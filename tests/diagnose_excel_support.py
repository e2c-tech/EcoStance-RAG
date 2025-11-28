"""
Diagnostic script to check Excel processing capabilities
"""

def check_dependencies():
    """Check if all required dependencies for Excel processing are available"""
    
    print("🔍 Checking Excel Processing Dependencies")
    print("=" * 45)
    
    dependencies = [
        ('pandas', 'Excel/CSV data processing'),
        ('openpyxl', 'Excel file reading (.xlsx)'),
        ('xlrd', 'Excel file reading (.xls) - optional'),
    ]
    
    missing_deps = []
    
    for dep_name, description in dependencies:
        try:
            __import__(dep_name)
            print(f"✅ {dep_name:15} - {description}")
        except ImportError as e:
            print(f"❌ {dep_name:15} - {description} (MISSING: {e})")
            missing_deps.append(dep_name)
    
    return missing_deps

def test_excel_extraction():
    """Test the Excel extraction function directly"""
    
    print("\n🧪 Testing Excel Extraction Function")
    print("=" * 35)
    
    try:
        # Try to import the extraction service
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
        
        from app.services.extraction_service import _extract_spreadsheet
        print("✅ Successfully imported extraction service")
        
        # Check if we can create a simple test
        try:
            import pandas as pd
            
            # Create a simple test DataFrame and save it
            test_data = {
                'Name': ['Product A', 'Product B'],
                'Price': [29, 49],
                'Description': ['Basic product', 'Premium product']
            }
            df = pd.DataFrame(test_data)
            test_file = 'temp_test.xlsx'
            df.to_excel(test_file, index=False)
            
            print(f"✅ Created test Excel file: {test_file}")
            
            # Test extraction
            blocks, doc_type = _extract_spreadsheet(test_file, 'xlsx')
            print(f"✅ Extraction successful: {len(blocks)} blocks, type: {doc_type}")
            
            # Show extracted content
            if blocks:
                print("\n📄 Extracted Content Sample:")
                for i, block in enumerate(blocks[:2]):  # Show first 2 blocks
                    print(f"   Block {i+1}: {block['text'][:100]}...")
            
            # Clean up
            os.remove(test_file)
            print(f"✅ Cleaned up test file")
            
        except Exception as e:
            print(f"❌ Excel extraction test failed: {e}")
    
    except ImportError as e:
        print(f"❌ Could not import extraction service: {e}")

def check_file_type_mapping():
    """Check if Excel file types are properly mapped"""
    
    print("\n🗺️  Checking File Type Mapping")
    print("=" * 30)
    
    try:
        from app.services.extraction_service import FILE_EXTRACTORS
        
        excel_types = ['xlsx', 'xls', 'csv']
        
        for file_type in excel_types:
            if file_type in FILE_EXTRACTORS:
                print(f"✅ {file_type:4} - Mapped to extraction function")
            else:
                print(f"❌ {file_type:4} - NOT MAPPED")
        
        print(f"\n📋 All supported types: {list(FILE_EXTRACTORS.keys())}")
        
    except ImportError as e:
        print(f"❌ Could not check file mapping: {e}")

def main():
    """Run all diagnostic checks"""
    
    print("🏥 Excel Support Diagnostic Tool")
    print("=" * 50)
    
    # Check dependencies
    missing = check_dependencies()
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("💡 Install with: pip install " + " ".join(missing))
    else:
        print("\n✅ All dependencies available")
    
    # Test extraction if dependencies are available
    if not missing:
        test_excel_extraction()
        check_file_type_mapping()
    
    print("\n🎯 Summary:")
    if missing:
        print("❌ Excel support is NOT working - missing dependencies")
        print("🔧 Fix: Install missing packages and restart server")
    else:
        print("✅ Excel support should be working")
        print("🔧 If still having issues, check server logs for errors")

if __name__ == "__main__":
    main()