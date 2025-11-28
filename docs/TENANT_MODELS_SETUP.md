# Tenant Data Models Setup Guide

## Overview

The tenant data models have been created to support multitenancy in your RAG system. This guide will help you set up and use these models.

## What Was Created

### Database Models (7 models)

1. **Tenant** - Main organization/tenant entity
2. **TenantDatabase** - Database connections per tenant
3. **TenantKnowledgeBase** - Qdrant collections per tenant
4. **TenantUser** - Users and roles within tenants
5. **TenantAPIKey** - API keys for authentication
6. **TenantQuota** - Resource usage tracking and limits
7. **AuditLog** - Security and compliance logging

### Supporting Files

- `app/db/database.py` - Database configuration and session management
- `app/db/init_db.py` - Database initialization script
- `app/db/seed_data.py` - Seed script for default tenant
- `app/models/README.md` - Detailed model documentation

## Quick Start

### Step 1: Install Dependencies

Make sure you have SQLAlchemy installed:

```bash
pip install sqlalchemy
```

For PostgreSQL:
```bash
pip install psycopg2-binary
```

For MySQL:
```bash
pip install mysql-connector-python
```

### Step 2: Configure Database

Add to your `.env` file:

```env
# SQLite (default - good for development)
DATABASE_URL=sqlite:///./tenant_system.db

# Or PostgreSQL (recommended for production)
# DATABASE_URL=postgresql://user:password@localhost:5432/tenant_db

# Or MySQL
# DATABASE_URL=mysql+pymysql://user:password@localhost:3306/tenant_db
```

### Step 3: Initialize Database

Create all tables:

```bash
python -m app.db.init_db
```

Expected output:
```
Creating database tables...
✓ Database tables created successfully!

Created tables:
  - tenants
  - tenant_databases
  - tenant_knowledge_bases
  - tenant_users
  - tenant_api_keys
  - tenant_quotas
  - audit_logs
```

### Step 4: Seed Default Tenant

Create a default tenant for backward compatibility:

```bash
python -m app.db.seed_data
```

Expected output:
```
Seeding database...
✓ Created default tenant with ID: <uuid>

✓ Database seeded successfully!

Default Tenant Details:
  ID: <uuid>
  Name: Default Organization
  Slug: default
  Tier: enterprise
```

## Database Schema

### Entity Relationships

```
┌─────────────┐
│   Tenant    │
└──────┬──────┘
       │
       ├──────► TenantDatabase (1:N)
       ├──────► TenantKnowledgeBase (1:N)
       ├──────► TenantUser (1:N)
       ├──────► TenantAPIKey (1:N)
       └──────► TenantQuota (1:1)

AuditLog ──────► Tenant (N:1)
```

### Key Features

**Tenant Model:**
- Unique slug for URL-friendly identification
- JSON settings for flexible configuration
- Billing tier and status tracking
- Soft delete support (deleted_at)

**TenantDatabase:**
- Encrypted database URI storage
- Multiple database types supported
- Connection status tracking

**TenantKnowledgeBase:**
- Maps to Qdrant collections
- Tracks document and vector counts
- Configurable embedding models and chunking

**TenantUser:**
- Role-based access control
- Unique constraint on (tenant_id, user_id)
- Login tracking

**TenantAPIKey:**
- Hashed key storage (never plain text)
- Permission-based access
- Expiration support
- Usage tracking

**TenantQuota:**
- Storage, query, and document limits
- Daily and monthly tracking
- Automatic reset tracking

**AuditLog:**
- Complete operation history
- IP and user agent tracking
- Indexed for fast queries

## Usage in FastAPI

### 1. Add Database Dependency

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.database import get_db

@app.get("/tenants")
def list_tenants(db: Session = Depends(get_db)):
    from app.models import Tenant
    tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
    return [t.to_dict() for t in tenants]
```

### 2. Initialize on Startup

Update `app/main.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()  # Create tables if they don't exist
    yield
    # Shutdown
    pass

app = FastAPI(lifespan=lifespan)
```

## Common Operations

### Create a New Tenant

```python
from app.models import Tenant, TenantQuota
from app.db.database import SessionLocal

db = SessionLocal()

tenant = Tenant(
    name="Acme Corp",
    slug="acme-corp",
    email="admin@acme.com",
    billing_tier="professional"
)
db.add(tenant)
db.commit()

# Create quota
quota = TenantQuota(tenant_id=tenant.id)
db.add(quota)
db.commit()
```

### Query Tenant Data

```python
# Get tenant by slug
tenant = db.query(Tenant).filter(Tenant.slug == "acme-corp").first()

# Get all knowledge bases for a tenant
kbs = db.query(TenantKnowledgeBase).filter(
    TenantKnowledgeBase.tenant_id == tenant.id
).all()

# Check quota
quota = db.query(TenantQuota).filter(
    TenantQuota.tenant_id == tenant.id
).first()

if quota.is_storage_exceeded():
    raise Exception("Storage quota exceeded")
```

### Log an Audit Event

```python
from app.models import AuditLog

log = AuditLog(
    tenant_id=tenant.id,
    user_id="user-123",
    action="document.uploaded",
    resource_type="knowledge_base",
    resource_id=kb.id,
    status="success",
    metadata={"file_name": "doc.pdf"}
)
db.add(log)
db.commit()
```

## Next Steps

Now that the data models are created, you can proceed with:

1. ✅ **Phase 1.1 Complete** - Tenant Data Model
2. **Phase 1.2** - Authentication & Context (JWT, dependencies)
3. **Phase 1.3** - Database Schema Migration (add tenant_id to existing tables)

See `docs/MULTITENANCY_IMPLEMENTATION_PLAN.md` for the complete roadmap.

## Troubleshooting

### Issue: "No module named 'sqlalchemy'"

```bash
pip install sqlalchemy
```

### Issue: "Table already exists"

The `init_db()` function is safe to run multiple times - it only creates tables that don't exist.

To recreate tables:
```bash
python -m app.db.init_db --drop
python -m app.db.init_db
```

### Issue: Database locked (SQLite)

SQLite doesn't handle concurrent writes well. For production, use PostgreSQL:

```bash
pip install psycopg2-binary
export DATABASE_URL=postgresql://user:pass@localhost/dbname
```

## Additional Resources

- Model documentation: `app/models/README.md`
- Implementation plan: `docs/MULTITENANCY_IMPLEMENTATION_PLAN.md`
- SQLAlchemy docs: https://docs.sqlalchemy.org/
