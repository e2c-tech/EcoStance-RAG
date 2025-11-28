#!/usr/bin/env python3
"""
Test script to verify the query service is working correctly with the meeting transcript.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.query_service import execute_query

def test_meeting_objectives():
    """Test querying for meeting objectives"""
    collection_name = "ecostance-demo2"
    query = "what are the objectives of this meeting"
    
    try:
        print(f"Testing query: '{query}'")
        print(f"Collection: {collection_name}")
        print("-" * 50)
        
        result = execute_query(collection_name, query)
        print(f"Result: {result}")
        
        if result.strip().lower() == "i don't know":
            print("\n❌ Still getting 'I don't know' response")
            return False
        else:
            print("\n✅ Got a meaningful response!")
            return True
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

if __name__ == "__main__":
    test_meeting_objectives()