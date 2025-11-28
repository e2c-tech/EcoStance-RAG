# Tenant Data Models

This directory contains all SQLAlchemy models for the multitenancy system.

## Models Overview

### Core Models

#### 1. **Tenant** (`tenant.py`)
The main tenant/organization model.

**Key Fields:**
- `id`: Unique tenant identifier (UUID)
- `name`: Organization name
- `slug`: URL-friendly identifier
- `is_active`: Status flag
- `settings`: JSON configuration (quotas, features, billing tier)
- `billing_tier`: free, starter, professional, enterprise
- `billing_status`: active, suspended, cancelled

**Relationships:**
- Has many: databases, knowledge_bases, users, api_keys

---

#### 2. **TenantDatabase** (`tenant_database.py`)
Represents database connections owned by a tenant.

**Key Fields:**
- `tenant_id`: Foreign key to Tenant
- `name`: Friendly name for the connection
- `db_type`: sqlite, postgresql, mysql, mongodb
- `db_uri_encrypted`: Encrypted connection string
- `is_active`: Connection status
- `last_connected_at`: Last successful connection timestamp

---

#### 3. **TenantKnowledgeBase** (`tenant_knowledge_base.py`)
Represents Qdrant collections (knowledge bases) owned by a tenant.

**Key Fields:**
- `tenant_id`: Foreign key to Tenant
- `kb_name`: User-friendly name
- `collection_name`: Actual Qdrant collection name (tenant_{id}_{name})
- `document_count`: Number of documents indexed
- `vector_count`: Number of vectors stored
- `storage_bytes`: Storage used
- `embedding_model`: Model used for embeddings
- `chunk_size`, `chunk_overlap`: Chunking configuration

---

#### 4. **TenantUser** (`tenant_user.py`)
Represents users and their roles within a tenant.

**Key Fields:**
- `tenant_id`: Foreign key to Tenant
- `user_id`: Reference to user in auth system
- `email`: User email
- `role`: owner, admin, manager, user, viewer
- `is_active`: User status
- `last_login_at`: Last login timestamp

**Unique Constraint:** (tenant_id, user_id) - a user can only have one role per tenant

---

#### 5. **TenantAPIKey** (`tenant_api_key.py`)
API keys for tenant authentication.

**Key Fields:**
- `tenant_id`: Foreign key to Tenant
- `name`: Friendly name for the key
- `key_hash`: Hashed API key (never store plain text!)
- `key_prefix`: First few characters for identification
- `permissions`: JSON array of permissions
- `expires_at`: Optional expiration date
- `usage_count`: Number of times used
- `last_used_at`: Last usage timestamp

---

### Supporting Models

#### 6. **TenantQuota** (`tenant_quota.py`)
Tracks resource usage and enforces quotas.

**Key Fields:**
- `storage_used` / `storage_limit`: Storage in bytes
- `queries_today` / `queries_limit_daily`: Daily query count
- `queries_this_month` / `queries_limit_monthly`: Monthly query count
- `documents_count` / `documents_limit`: Document limits
- `db_connections_count` / `db_connections_limit`: Connection limits
- `last_daily_reset`, `last_monthly_reset`: Reset timestamps

**Methods:**
- `is_storage_exceeded()`: Check if storage quota exceeded
- `is_daily_query_exceeded()`: Check if daily query quota exceeded
- `is_monthly_query_exceeded()`: Check if monthly query quota exceeded

---

#### 7. **AuditLog** (`audit_log.py`)
Tracks all tenant operations for security and compliance.

**Key Fields:**
- `tenant_id`: Foreign key to Tenant
- `user_id`, `user_email`: Who performed the action
- `action`: What was done (e.g., "tenant.created", "kb.uploaded")
- `resource_type`, `resource_id`: What was affected
- `status`: success, failure, error
- `metadata`: JSON with additional details
- `ip_address`, `user_agent`: Request context

---

## Database Setup

### 1. Initialize Database

```bash
# Create all tables
python -m app.db.init_db

# Drop all tables (WARNING: deletes all data!)
python -m app.db.init_db --drop
```

### 2. Seed Initial Data

```bash
# Create default tenant
python -m app.db.seed_data
```

### 3. Configure Database URL

Set the `DATABASE_URL` environment variable:

```bash
# SQLite (default)
DATABASE_URL=sqlite:///./tenant_system.db

# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/tenant_db

# MySQL
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/tenant_db
```

---

## Usage Examples

### Creating a Tenant

```python
from app.models import Tenant, TenantQuota
from app.db.database import SessionLocal

db = SessionLocal()

# Create tenant
tenant = Tenant(
    name="Acme Corporation",
    slug="acme-corp",
    email="admin@acme.com",
    billing_tier="professional",
    settings={
        "max_storage_bytes": 53687091200,  # 50GB
        "max_queries_per_day": 5000,
        "features": ["rag", "db_chat"]
    }
)

db.add(tenant)
db.commit()

# Create quota
quota = TenantQuota(
    tenant_id=tenant.id,
    storage_limit=53687091200,
    queries_limit_daily=5000,
    queries_limit_monthly=150000
)

db.add(quota)
db.commit()
```

### Adding a Knowledge Base

```python
from app.models import TenantKnowledgeBase

kb = TenantKnowledgeBase(
    tenant_id=tenant.id,
    kb_name="Product Documentation",
    collection_name=f"tenant_{tenant.id}_product_docs",
    description="All product documentation and guides",
    embedding_model="all-MiniLM-L6-v2"
)

db.add(kb)
db.commit()
```

### Adding a User to Tenant

```python
from app.models import TenantUser

user = TenantUser(
    tenant_id=tenant.id,
    user_id="user-uuid-here",
    email="john@acme.com",
    full_name="John Doe",
    role="admin"
)

db.add(user)
db.commit()
```

### Creating an API Key

```python
from app.models import TenantAPIKey
import hashlib
import secrets

# Generate API key
api_key = f"sk_live_{secrets.token_urlsafe(32)}"
key_hash = hashlib.sha256(api_key.encode()).hexdigest()

api_key_record = TenantAPIKey(
    tenant_id=tenant.id,
    name="Production API Key",
    key_hash=key_hash,
    key_prefix=api_key[:15],
    permissions=["upload:files", "query:kb"]
)

db.add(api_key_record)
db.commit()

# Give the plain API key to the user (only shown once!)
print(f"API Key: {api_key}")
```

### Logging an Audit Event

```python
from app.models import AuditLog

log = AuditLog(
    tenant_id=tenant.id,
    user_id="user-uuid",
    user_email="john@acme.com",
    action="kb.document_uploaded",
    resource_type="knowledge_base",
    resource_id=kb.id,
    description="Uploaded document: product_guide.pdf",
    metadata={"file_name": "product_guide.pdf", "file_size": 1024000},
    status="success",
    ip_address="192.168.1.1"
)

db.add(log)
db.commit()
```

---

## Relationships Diagram

```
Tenant
  ├── TenantDatabase (1:N)
  ├── TenantKnowledgeBase (1:N)
  ├── TenantUser (1:N)
  ├── TenantAPIKey (1:N)
  └── TenantQuota (1:1)

AuditLog → Tenant (N:1, optional)
```

---

## Best Practices

1. **Always use transactions** when creating related records
2. **Hash API keys** before storing (never store plain text)
3. **Soft delete** tenants by setting `is_active=False` and `deleted_at`
4. **Log all operations** using AuditLog for compliance
5. **Check quotas** before allowing resource-intensive operations
6. **Use indexes** on frequently queried fields (tenant_id, slug, etc.)
7. **Encrypt sensitive data** like database URIs before storage

---

## Migration Notes

When migrating existing data to multitenancy:

1. Create a "default" tenant
2. Assign all existing data to the default tenant
3. Update all queries to include tenant_id filters
4. Test thoroughly before enabling authentication

See `seed_data.py` for creating the default tenant.
