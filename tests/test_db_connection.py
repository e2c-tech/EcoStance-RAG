"""
Simple test script to verify database connection functionality
"""
import requests
import json

BACKEND_URL = "http://127.0.0.1:8000/api/v1"

def test_db_connection():
    """Test database connection with SQLite"""
    print("Testing database connection...")
    
    # Test with SQLite (simplest option)
    db_uri = "sqlite:///test.db"
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/db/connect",
            json={"db_uri": db_uri}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Database connection successful!")
            return True
        else:
            print("❌ Database connection failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_query_generation():
    """Test SQL query generation"""
    print("\nTesting SQL query generation...")
    
    question = "Show me all tables"
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/db/generate-query",
            json={"question": question}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Query generation successful!")
            return True
        else:
            print("❌ Query generation failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Database Connection Test")
    print("=" * 60)
    print("\nMake sure the backend is running on http://127.0.0.1:8000")
    print("Run: python run_app.py\n")
    
    # Test connection
    connection_ok = test_db_connection()
    
    # Test query generation if connection succeeded
    if connection_ok:
        test_query_generation()
    
    print("\n" + "=" * 60)
