"""
Create a demo QuickShip database with sample shipment data
"""
import sqlite3
from datetime import datetime, timedelta

# Create database
conn = sqlite3.connect('QuickShip.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    address TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS delivery_boys (
    boy_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    vehicle_number TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS shipments (
    shipment_id TEXT PRIMARY KEY,
    tracking_number TEXT NOT NULL,
    customer_id INTEGER NOT NULL,
    delivery_boy_id INTEGER,
    status TEXT NOT NULL,
    delivery_address TEXT NOT NULL,
    pincode TEXT NOT NULL,
    expected_delivery_date TEXT,
    actual_delivery_date TEXT,
    charges REAL NOT NULL,
    cod_amount REAL,
    remarks TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (delivery_boy_id) REFERENCES delivery_boys(boy_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS complaints (
    complaint_id INTEGER PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    complaint_type TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    resolution TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
)
''')

# Insert sample customers
customers = [
    (1, 'Rajesh Kumar', '9224217802', 'rajesh@example.com', 'Mumbai, Maharashtra'),
    (2, 'Priya Sharma', '9876543210', 'priya@example.com', 'Delhi, Delhi'),
    (3, 'Amit Patel', '9123456789', 'amit@example.com', 'Ahmedabad, Gujarat'),
]

cursor.executemany('INSERT OR REPLACE INTO customers VALUES (?, ?, ?, ?, ?)', customers)

# Insert sample delivery boys
delivery_boys = [
    (1, 'Suresh', '9988776655', 'MH-01-AB-1234'),
    (2, 'Ramesh', '9876543211', 'DL-02-CD-5678'),
]

cursor.executemany('INSERT OR REPLACE INTO delivery_boys VALUES (?, ?, ?, ?)', delivery_boys)

# Insert sample shipments
today = datetime.now()
shipments = [
    ('QS250001', 'TRK123456789', 1, 1, 'In Transit', '123 Main St, Mumbai, Maharashtra', '400001', 
     (today + timedelta(days=2)).strftime('%Y-%m-%d'), None, 150.00, 500.00, 'COD order'),
    
    ('QS250002', 'TRK123456790', 2, 2, 'Delivered', '456 Park Ave, Delhi, Delhi', '110001', 
     (today - timedelta(days=1)).strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), 200.00, None, 'Prepaid'),
    
    ('QS250003', 'TRK123456791', 3, 1, 'Out for Delivery', '789 Gandhi Rd, Ahmedabad, Gujarat', '380001', 
     today.strftime('%Y-%m-%d'), None, 180.00, 800.00, 'COD order - fragile'),
    
    ('QS250004', 'TRK123456792', 1, None, 'Booked', '123 Main St, Mumbai, Maharashtra', '400001', 
     (today + timedelta(days=3)).strftime('%Y-%m-%d'), None, 120.00, None, 'Prepaid - express'),
    
    ('QS250020', 'TRK123456820', 2, 2, 'At Hub', '456 Park Ave, Delhi, Delhi', '110001', 
     (today + timedelta(days=1)).strftime('%Y-%m-%d'), None, 175.00, 600.00, 'COD order'),
]

cursor.executemany('''
    INSERT OR REPLACE INTO shipments 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', shipments)

# Insert sample complaints
complaints = [
    (1, 'QS250001', 'Delay', 'Package delayed by 2 days', 'Resolved', 
     'Compensated with discount', today.strftime('%Y-%m-%d %H:%M:%S'), 
     (today + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')),
]

cursor.executemany('''
    INSERT OR REPLACE INTO complaints 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', complaints)

conn.commit()
conn.close()

print("✅ QuickShip demo database created successfully!")
print("📦 Created 5 sample shipments (QS250001-QS250004, QS250020)")
print("👥 Created 3 sample customers")
print("🚚 Created 2 delivery boys")
print("📝 Created 1 sample complaint")
print("\nDatabase: QuickShip.db")
print("\nUpdate your .env file:")
print("QUICKSHIP_DB_PATH=QuickShip.db")
