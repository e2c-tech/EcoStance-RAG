"""
Tenant schemas for request/response models.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class TenantProfileUpdate(BaseModel):
    """Schema for updating tenant profile."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class NotificationPreferences(BaseModel):
    """Schema for notification preferences."""
    email_alerts: bool = True
    quota_warnings: bool = True
    error_alerts: bool = True
    weekly_reports: bool = False
    webhook_url: Optional[str] = None


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
    logo_url: Optional[str] = None
    logo_filename: Optional[str] = None
    
    class Config:
        from_attributes = True


class TenantWithPreferences(TenantResponse):
    """Tenant response with preferences."""
    preferences: Optional[NotificationPreferences] = None
