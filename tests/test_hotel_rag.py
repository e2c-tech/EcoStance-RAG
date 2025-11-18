#!/usr/bin/env python3

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
KB_NAME = "ecostance-demo2"

def test_rag_query(query, expected_context=None):
    """Test a RAG query and display results"""
    print(f"\n{'='*60}")
    print(f"QUERY: {query}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/query/",
            data={
                "query": query,
                "collection_name": KB_NAME,
                "top_k": 5
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"ANSWER: {result.get('answer', 'No answer provided')}")
            print(f"\nSOURCES ({len(result.get('sources', []))} found):")
            
            for i, source in enumerate(result.get('sources', []), 1):
                print(f"\n  Source {i}:")
                print(f"    Table: {source.get('metadata', {}).get('table_name', 'Unknown')}")
                print(f"    Method: {source.get('metadata', {}).get('extraction_method', 'Unknown')}")
                print(f"    Score: {source.get('score', 'N/A'):.4f}")
                print(f"    Content: {source.get('content', '')[:200]}...")
            
            if expected_context:
                print(f"\n  ✓ Expected context: {expected_context}")
                
        else:
            print(f"ERROR: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"REQUEST ERROR: {e}")
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")

def main():
    """Run comprehensive RAG tests on hotel database"""
    
    print("Testing RAG queries against hotel.sql data in ecostance-demo2 KB")
    print("=" * 80)
    
    # Test 1: Customer queries
    test_rag_query(
        "Who are the customers in the database?",
        "Should find customer records from public.customers table"
    )
    
    test_rag_query(
        "Find customer with phone number +918296635241",
        "Should find AFNAN AHMED customer record"
    )
    
    # Test 2: Menu and restaurant queries
    test_rag_query(
        "What menu items are available?",
        "Should find items from public.menu_items table"
    )
    
    test_rag_query(
        "Show me vegetarian menu items",
        "Should filter vegetarian items from menu"
    )
    
    test_rag_query(
        "What is the price of Margherita Pizza?",
        "Should find pizza price from menu_items"
    )
    
    # Test 3: Orders and business queries
    test_rag_query(
        "How many orders are there?",
        "Should count orders from public.orders table"
    )
    
    test_rag_query(
        "What tables are available in the restaurant?",
        "Should find table information from public.tables"
    )
    
    test_rag_query(
        "Which organizations are in the system?",
        "Should find organization data"
    )
    
    # Test 4: Complex analytical queries
    test_rag_query(
        "What is the total revenue from completed orders?",
        "Should analyze order amounts and statuses"
    )
    
    test_rag_query(
        "Which customer has the most recent login?",
        "Should find customer with latest last_login timestamp"
    )
    
    # Test 5: Specific data queries
    test_rag_query(
        "Show me group information for groups that are active",
        "Should find active groups from public.groups table"
    )
    
    test_rag_query(
        "What kitchen stations are configured?",
        "Should find kitchen station data"
    )
    
    print(f"\n{'='*80}")
    print("RAG testing completed!")
    print("Check the results above to verify that:")
    print("1. Queries return relevant data from the hotel database")
    print("2. Sources point to correct tables (customers, menu_items, orders, etc.)")
    print("3. Extraction method shows 'psql_copy' for COPY statement data")
    print("4. Answers are contextually appropriate")

if __name__ == "__main__":
    main()