#!/usr/bin/env python3

from app.services.extraction_service import extract_data_from_file
import json

# Test the extraction
print("Testing COPY statement extraction...")
blocks, doc_type = extract_data_from_file('uploads/hotel.sql')
print(f'Extracted {len(blocks)} blocks of type: {doc_type}')

# Show some sample blocks
for i, block in enumerate(blocks[:5]):
    print(f'Block {i+1}:')
    print(f'  Table: {block["metadata"]["table_name"]}')
    print(f'  Method: {block["metadata"]["extraction_method"]}')
    print(f'  Data: {block["text"][:100]}...')
    print()

# Count blocks by table
table_counts = {}
for block in blocks:
    table = block["metadata"]["table_name"]
    table_counts[table] = table_counts.get(table, 0) + 1

print("Blocks per table:")
for table, count in table_counts.items():
    print(f"  {table}: {count} rows")