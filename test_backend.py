"""
Quick test to verify backend routes are available
"""

import sys
sys.path.append('.')

from app.main import app
from app.config import ENABLE_REACT_AGENT

print("=" * 60)
print("Backend Route Check")
print("=" * 60)

print(f"\n✓ ENABLE_REACT_AGENT: {ENABLE_REACT_AGENT}")

print("\n📋 Available Routes:")
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        methods = ', '.join(route.methods) if route.methods else 'N/A'
        print(f"  {methods:10} {route.path}")

print("\n" + "=" * 60)

# Check if beta routes are included
beta_routes = [route for route in app.routes if '/beta/' in route.path]
if beta_routes:
    print("✅ Beta agent routes are registered!")
    for route in beta_routes:
        methods = ', '.join(route.methods) if route.methods else 'N/A'
        print(f"  {methods:10} {route.path}")
else:
    print("❌ Beta agent routes NOT found!")
    print("\nTroubleshooting:")
    print("1. Check ENABLE_REACT_AGENT=true in .env")
    print("2. Restart the backend server")
    print("3. Check for import errors")

print("=" * 60)
