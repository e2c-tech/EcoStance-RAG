#!/usr/bin/env python3

import requests
import json

BASE_URL = "http://localhost:8000"

def check_collections():
    """Check what collections exist in the system"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/manage/knowledge-bases/")
        if response.status_code == 200:
            collections = response.json()
            print("Available knowledge bases:")
            for collection in collections:
                print(f"  - {collection}")
            return collections
        else:
            print(f"Error getting knowledge bases: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Error: {e}")
        return []

def check_collection_info(collection_name):
    """Get information about a specific collection"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/manage/knowledge-bases/{collection_name}/details")
        if response.status_code == 200:
            info = response.json()
            print(f"\nKnowledge base '{collection_name}' details:")
            print(f"  Document count: {info.get('count', 'Unknown')}")
            print(f"  Files: {info.get('files', [])}")
        else:
            print(f"Error getting knowledge base details: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_simple_query(collection_name):
    """Test a simple query to see what data is actually indexed"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/query/",
            data={
                "query": "show me any data",
                "collection_name": collection_name,
                "top_k": 3
            }
        )
        if response.status_code == 200:
            result = response.json()
            print(f"\nSample data from '{collection_name}':")
            print(f"Answer: {result.get('answer', 'No answer')}")
            
            sources = result.get('sources', [])
            print(f"Sources found: {len(sources)}")
            
            for i, source in enumerate(sources[:3], 1):
                metadata = source.get('metadata', {})
                print(f"\n  Source {i}:")
                print(f"    Table: {metadata.get('table_name', 'Unknown')}")
                print(f"    Method: {metadata.get('extraction_method', 'Unknown')}")
                print(f"    File: {metadata.get('source_filename', 'Unknown')}")
                print(f"    Content: {source.get('content', '')[:150]}...")
        else:
            print(f"Error querying collection: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Checking RAG system collections and data...")
    print("=" * 60)
    
    collections = check_collections()
    
    if "ecostance-demo2" in collections:
        check_collection_info("ecostance-demo2")
        test_simple_query("ecostance-demo2")
    else:
        print("\n'ecostance-demo2' collection not found!")
        if collections:
            print("Testing first available collection...")
            test_simple_query(collections[0])