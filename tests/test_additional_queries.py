#!/usr/bin/env python3
"""
Test script to verify the query service works with various questions about the meeting.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.query_service import execute_query

def test_queries():
    """Test various queries about the meeting"""
    collection_name = "ecostance-demo2"
    
    queries = [
        "What application are they building?",
        "Who are the participants in this meeting?",
        "What technology stack are they using?",
        "What is the role of FastAPI in their architecture?",
        "What is Splunk mentioned in the context of?"
    ]
    
    for query in queries:
        try:
            print(f"\n🔍 Query: '{query}'")
            print("-" * 60)
            
            result = execute_query(collection_name, query)
            print(f"Answer: {result}")
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_queries()