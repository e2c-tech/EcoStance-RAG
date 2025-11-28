# Phase 2.2 Quick Reference

## 🔐 Credential Encryption

```python
from app.services.credential_service import get_credential_service

service = get_credential_service()

# Encrypt
encrypted = service.encrypt_credential("postgresql://user:pass@host/db")

# Decrypt
decrypted = service.decrypt_credential(encrypted)

# Test
assert service.test_encryption() == True
```

## 🔌 Connection Management

```python
from app.services.connection_manager_service import get_connection_manager_service

manager = get_connection_manager_service()

# Get connection (creates or reuses)
connector = manager.get_connection(
    tenant_id="acme-corp",
    db_id="main-db",
    connection_config={'type': 'postgresql', ...}
)

# Get stats
stats = manager.get_connection_stats("acme-corp")

# Close connection
manager.close_connection("acme-corp", "main-db")
```

## 🌐 API Endpoints

### Connect
```bash
POST /db/connect
Authorization: Bearer {token}
{
  "db_uri": "postgresql://user:pass@localhost/db",
  "db_id": "main-db"
}
```

### Generate Query
```bash
POST /db/generate-query
Authorization: Bearer {token}
{
  "question": "Show all users",
  "db_id": "main-db"
}
```

### Execute Query
```bash
POST /db/execute-query
Authorization: Bearer {token}
{
  "query": "SELECT * FROM users",
  "db_id": "main-db"
}
```

### Get Stats
```bash
GET /db/connections/stats
Authorization: Bearer {token}
```

### Health Check
```bash
GET /db/connections/{db_id}/health
Authorization: Bearer {token}
```

### Close Connection
```bash
POST /db/connections/{db_id}/close
Authorization: Bearer {token}
```

## ⚙️ Configuration

### Environment Variables
```bash
ENCRYPTION_KEY=PnhFEx2BLbYwlRDXylajuKdLyGyk_6FP2aQUFBAR2Qc=
MAX_CONNECTIONS_PER_TENANT=5
CONNECTION_TIMEOUT_MINUTES=30
```

### Generate Encryption Key
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 📊 Connection Pooling

```
Format: {tenant_id}:{db_id}
Example: acme-corp:main-db

Limits:
- Max 5 connections per tenant
- 30 minute idle timeout
- Automatic cleanup every 5 minutes
```

## 🔍 Monitoring

```python
# Tenant stats
stats = manager.get_connection_stats("acme-corp")
# {
#   "active_connections": 3,
#   "max_connections": 5,
#   "connections": [...]
# }

# System stats
stats = manager.get_connection_stats()
# {
#   "total_connections": 15,
#   "total_tenants": 5
# }
```

## 🧪 Testing

```python
# Test encryption
from app.services.credential_service import get_credential_service
service = get_credential_service()
assert service.test_encryption() == True

# Test connection pooling
from app.services.connection_manager_service import get_connection_manager_service
manager = get_connection_manager_service()

config = {'type': 'sqlite', 'database': 'test.db'}
conn = manager.get_connection("test-tenant", "db1", config)
assert conn is not None
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `app/services/credential_service.py` | Credential encryption |
| `app/services/connection_manager_service.py` | Connection pooling |
| `app/routers/db_router_v2.py` | Tenant-aware DB router |

## 🎯 Status

✅ **Phase 2.2 Complete** - Database Connection Management

**Next:** Phase 2.3 - File Storage Isolation
