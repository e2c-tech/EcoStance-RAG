"""
Test script to verify Excel file upload and processing
"""
import pandas as pd
import requests
import os

def create_test_excel():
    """Create a simple test Excel file"""
    data = {
        'Product': ['Certificate A', 'Certificate B', 'Certificate C'],
        'Price': [29, 49, 99],
        'Description': [
            'Basic digital certificate with QR code verification',
            'Premium certificate with blockchain embedding',
            'Enterprise certificate with advanced features'
        ],
        'Category': ['Basic', 'Premium', 'Enterprise']
    }
    
    df = pd.DataFrame(data)
    
    # Create test file
    test_file = 'test_products.xlsx'
    df.to_excel(test_file, index=False, sheet_name='Products')
    
    print(f"✅ Created test Excel file: {test_file}")
    return test_file

def test_excel_processing():
    """Test Excel file upload and processing"""
    
    print("🧪 Testing Excel File Processing")
    print("=" * 40)
    
    # Create test Excel file
    excel_file = create_test_excel()
    
    try:
        # Test 1: Upload the Excel file
        print("\n📝 Test 1: Upload Excel File")
        with open(excel_file, 'rb') as f:
            files = {'file': (excel_file, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            response = requests.post("http://127.0.0.1:8000/api/v1/upload/", files=files)
        
        if response.status_code == 200:
            result = response.json()
            file_path = result.get('file_path')
            print(f"✅ Upload successful: {file_path}")
            
            # Test 2: Process the Excel file
            print("\n📝 Test 2: Process Excel File")
            data = {
                'file_path': file_path,
                'collection_name': 'test-excel-kb'
            }
            response = requests.post("http://127.0.0.1:8000/api/v1/upload-to-qdrant/", data=data)
            
            if response.status_code == 200:
                print("✅ Processing successful!")
                
                # Test 3: Query the processed data
                print("\n📝 Test 3: Query Processed Excel Data")
                query_data = {
                    'collection_name': 'test-excel-kb',
                    'query': 'What is the price of premium certificate?'
                }
                response = requests.post("http://127.0.0.1:8000/api/v1/query/", data=query_data)
                
                if response.status_code == 200:
                    answer = response.json().get('answer')
                    print(f"✅ Query successful!")
                    print(f"Question: What is the price of premium certificate?")
                    print(f"Answer: {answer}")
                else:
                    print(f"❌ Query failed: {response.status_code} - {response.text}")
            else:
                print(f"❌ Processing failed: {response.status_code} - {response.text}")
        else:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start with: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Clean up test file
        if os.path.exists(excel_file):
            os.remove(excel_file)
            print(f"\n🧹 Cleaned up test file: {excel_file}")

def show_supported_formats():
    """Show all supported file formats"""
    print("\n📋 Supported File Formats:")
    print("-" * 30)
    formats = [
        ("PDF", "pdf", "Portable Document Format"),
        ("Word", "docx", "Microsoft Word documents"),
        ("Excel", "xlsx", "Microsoft Excel spreadsheets"),
        ("CSV", "csv", "Comma-separated values"),
        ("Text", "txt", "Plain text files"),
        ("Markdown", "md", "Markdown documents"),
        ("HTML", "html, htm", "Web pages"),
        ("SQL", "sql", "SQL scripts"),
        ("JSONL", "jsonl", "JSON Lines format")
    ]
    
    for name, ext, desc in formats:
        print(f"{name:10} (.{ext:4}) - {desc}")

if __name__ == "__main__":
    show_supported_formats()
    test_excel_processing()