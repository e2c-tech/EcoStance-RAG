"""
Tenant management router for creating and managing tenants.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid
import re
import bcrypt
import os
import shutil

from ..db.database import get_db
from ..models.tenant import Tenant
from ..auth.dependencies import get_tenant_id
from ..schemas.tenant import TenantProfileUpdate, NotificationPreferences, TenantResponse

router = APIRouter()

# Logo upload configuration
LOGO_UPLOAD_DIR = "uploads/logos"
ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg"}
MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5MB

# Ensure logo directory exists
os.makedirs(LOGO_UPLOAD_DIR, exist_ok=True)


class TenantCreateRequest(BaseModel):
    """Tenant creation request model."""
    name: str
    email: str
    password: str
    phone: Optional[str] = None
    billing_tier: str = "free"


class TenantUpdateRequest(BaseModel):
    """Tenant update request model."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    billing_tier: Optional[str] = None
    settings: Optional[dict] = None


class TenantResponse(BaseModel):
    """Tenant response model."""
    id: str
    name: str
    slug: str
    email: Optional[str]
    phone: Optional[str]
    is_active: bool
    created_at: datetime
    billing_tier: str
    billing_status: str
    
    class Config:
        from_attributes = True


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from tenant name."""
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower())
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Add random suffix to ensure uniqueness
    slug = f"{slug}-{uuid.uuid4().hex[:6]}"
    return slug


@router.post("/tenants/register", response_model=TenantResponse, tags=["Tenant Management"])
async def register_tenant(
    request: TenantCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Self-service tenant registration endpoint.
    Creates a new tenant account with email and password.
    """
    # Check if email already exists
    existing_email = db.query(Tenant).filter(Tenant.email == request.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate unique slug
    slug = generate_slug(request.name)
    
    # Check if slug already exists (shouldn't happen with random suffix, but check anyway)
    existing = db.query(Tenant).filter(Tenant.slug == slug).first()
    if existing:
        # Regenerate with different suffix
        slug = generate_slug(request.name)
    
    # Hash password
    password_hash = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create tenant
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name=request.name,
        slug=slug,
        email=request.email,
        password_hash=password_hash,
        phone=request.phone,
        is_active=True,
        billing_tier=request.billing_tier,
        billing_status="active",
        settings={
            "max_storage_bytes": 10737418240,  # 10GB
            "max_queries_per_day": 1000,
            "max_queries_per_month": 30000,
            "max_documents": 10000,
            "max_db_connections": 5,
            "features": ["rag", "db_chat"],
            "region": "default"
        }
    )
    
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    
    return tenant


@router.get("/tenants/", response_model=List[TenantResponse], tags=["Tenant Management"])
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all tenants (admin only).
    In production, this should require admin authentication.
    """
    tenants = db.query(Tenant).filter(
        Tenant.deleted_at.is_(None)
    ).offset(skip).limit(limit).all()
    
    return tenants


@router.get("/tenants/me", response_model=TenantResponse, tags=["Tenant Management"])
async def get_current_tenant(
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Get current tenant information.
    Requires authentication.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return tenant


@router.get("/tenants/{tenant_id}", response_model=TenantResponse, tags=["Tenant Management"])
async def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    """
    Get tenant by ID (admin only).
    In production, this should require admin authentication.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return tenant


@router.put("/tenants/{tenant_id}", response_model=TenantResponse, tags=["Tenant Management"])
async def update_tenant(
    tenant_id: str,
    request: TenantUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update tenant information (admin only).
    In production, this should require admin authentication.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Update fields if provided
    if request.name is not None:
        tenant.name = request.name
    if request.email is not None:
        tenant.email = request.email
    if request.phone is not None:
        tenant.phone = request.phone
    if request.is_active is not None:
        tenant.is_active = request.is_active
    if request.billing_tier is not None:
        tenant.billing_tier = request.billing_tier
    if request.settings is not None:
        tenant.settings = request.settings
    
    tenant.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(tenant)
    
    return tenant


@router.delete("/tenants/{tenant_id}", tags=["Tenant Management"])
async def delete_tenant(
    tenant_id: str,
    hard_delete: bool = False,
    db: Session = Depends(get_db)
):
    """
    Delete tenant (admin only).
    By default performs soft delete. Use hard_delete=true for permanent deletion.
    In production, this should require admin authentication.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if hard_delete:
        # Permanent deletion
        db.delete(tenant)
        message = "Tenant permanently deleted"
    else:
        # Soft delete
        tenant.deleted_at = datetime.utcnow()
        tenant.is_active = False
        message = "Tenant soft deleted"
    
    db.commit()
    
    return {"message": message, "tenant_id": tenant_id}


@router.post("/tenants/{tenant_id}/activate", response_model=TenantResponse, tags=["Tenant Management"])
async def activate_tenant(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    """
    Activate a tenant account (admin only).
    In production, this should require admin authentication.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    tenant.is_active = True
    tenant.billing_status = "active"
    tenant.deleted_at = None
    tenant.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(tenant)
    
    return tenant


@router.post("/tenants/{tenant_id}/deactivate", response_model=TenantResponse, tags=["Tenant Management"])
async def deactivate_tenant(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    """
    Deactivate a tenant account (admin only).
    In production, this should require admin authentication.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    tenant.is_active = False
    tenant.billing_status = "suspended"
    tenant.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(tenant)
    
    return tenant


# ============================================================================
# PHASE 5: Tenant Profile Management
# ============================================================================

@router.patch("/tenants/me/profile", response_model=TenantResponse, tags=["Tenant Profile"])
async def update_tenant_profile(
    profile: TenantProfileUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Update current tenant's profile (name, email, phone).
    Requires authentication.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Update fields if provided
    if profile.name is not None:
        tenant.name = profile.name
    
    if profile.email is not None:
        # Check if email is already taken by another tenant
        existing = db.query(Tenant).filter(
            Tenant.email == profile.email,
            Tenant.id != tenant_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        tenant.email = profile.email
    
    if profile.phone is not None:
        tenant.phone = profile.phone
    
    tenant.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(tenant)
    
    return tenant


@router.post("/tenants/me/logo", tags=["Tenant Profile"])
async def upload_tenant_logo(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Upload tenant logo.
    Requires authentication.
    Accepts: PNG, JPG, JPEG, GIF, SVG (max 5MB)
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_LOGO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_LOGO_EXTENSIONS)}"
        )
    
    # Read file content to check size
    content = await file.read()
    if len(content) > MAX_LOGO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_LOGO_SIZE / 1024 / 1024}MB"
        )
    
    # Delete old logo if exists
    if tenant.logo_filename:
        old_logo_path = os.path.join(LOGO_UPLOAD_DIR, tenant.logo_filename)
        if os.path.exists(old_logo_path):
            os.remove(old_logo_path)
    
    # Generate unique filename
    unique_filename = f"{tenant_id}_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = os.path.join(LOGO_UPLOAD_DIR, unique_filename)
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Update tenant record
    tenant.logo_filename = unique_filename
    tenant.logo_url = f"/api/v1/tenants/me/logo"
    tenant.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Logo uploaded successfully",
        "logo_url": tenant.logo_url,
        "filename": unique_filename
    }


@router.get("/tenants/me/logo", tags=["Tenant Profile"])
async def get_tenant_logo(
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Get current tenant's logo.
    Requires authentication.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if not tenant.logo_filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No logo uploaded"
        )
    
    file_path = os.path.join(LOGO_UPLOAD_DIR, tenant.logo_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Logo file not found"
        )
    
    return FileResponse(file_path)


@router.delete("/tenants/me/logo", tags=["Tenant Profile"])
async def delete_tenant_logo(
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Delete current tenant's logo.
    Requires authentication.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if not tenant.logo_filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No logo to delete"
        )
    
    # Delete file from disk
    file_path = os.path.join(LOGO_UPLOAD_DIR, tenant.logo_filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Update tenant record
    tenant.logo_filename = None
    tenant.logo_url = None
    tenant.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Logo deleted successfully"}


# ============================================================================
# PHASE 5: Notification Preferences
# ============================================================================

@router.get("/tenants/me/preferences", tags=["Tenant Preferences"])
async def get_preferences(
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Get notification preferences for current tenant.
    Requires authentication.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Get preferences from settings JSON field
    settings = tenant.settings or {}
    preferences = settings.get("preferences", {})
    
    # Return with defaults
    return {
        "email_alerts": preferences.get("email_alerts", True),
        "quota_warnings": preferences.get("quota_warnings", True),
        "error_alerts": preferences.get("error_alerts", True),
        "weekly_reports": preferences.get("weekly_reports", False),
        "webhook_url": preferences.get("webhook_url")
    }


@router.put("/tenants/me/preferences", tags=["Tenant Preferences"])
async def update_preferences(
    preferences: NotificationPreferences,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Update notification preferences for current tenant.
    Requires authentication.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Update settings JSON field
    settings = tenant.settings or {}
    settings["preferences"] = {
        "email_alerts": preferences.email_alerts,
        "quota_warnings": preferences.quota_warnings,
        "error_alerts": preferences.error_alerts,
        "weekly_reports": preferences.weekly_reports,
        "webhook_url": preferences.webhook_url
    }
    
    tenant.settings = settings
    tenant.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Preferences updated successfully",
        "preferences": settings["preferences"]
    }
