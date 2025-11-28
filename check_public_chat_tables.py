import sqlite3

conn = sqlite3.connect('tenant_system.db')
cursor = conn.cursor()

# Check for public chat tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%public_chat%'")
tables = cursor.fetchall()

print("Public chat tables found:")
for table in tables:
    print(f"  - {table[0]}")

if not tables:
    print("  ❌ No public chat tables found!")
    print("\nYou need to run the migration:")
    print("  python migrations/apply_public_chat_migration.py")

conn.close()
