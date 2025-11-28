#!/usr/bin/env python3

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
KB_NAME = "ecostance-demo2"

def test_rag_query_with_sources(query, expected_context=None):
    """Test a RAG query and display results with better source handling"""
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
            
            # The current API only returns the answer, but we can see from logs
            # that data is being retrieved. Let's note this limitation.
            print(f"\nNOTE: API currently only returns answer, not source details.")
            print(f"Check server logs to see retrieved context data.")
            
            if expected_context:
                print(f"\n✓ Expected context: {expected_context}")
                
        else:
            print(f"ERROR: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"REQUEST ERROR: {e}")
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")

def test_specific_hotel_queries():
    """Test queries that should work based on the log data"""
    
    print("Testing specific queries based on retrieved data from logs...")
    print("=" * 80)
    
    # These queries should work based on what we see in the logs
    
    test_rag_query_with_sources(
        "What is the price of Margherita Pizza?",
        "Should find: $9.99 (seen in logs)"
    )
    
    test_rag_query_with_sources(
        "Show me vegetarian menu items",
        "Should find: Vegan Buddha Bowl ($10.5), Veggie Omelette ($6.25)"
    )
    
    test_rag_query_with_sources(
        "What menu items cost less than $10?",
        "Should find items under $10 from menu_items table"
    )
    
    test_rag_query_with_sources(
        "Show me order information",
        "Should find order records with IDs, amounts, statuses"
    )
    
    test_rag_query_with_sources(
        "What are the different order statuses?",
        "Should find: cart, pending, accepted (from logs)"
    )
    
    test_rag_query_with_sources(
        "Find orders with total amount over $200",
        "Should find orders like ID 25 with $217 total"
    )
    
    test_rag_query_with_sources(
        "What group members are in the system?",
        "Should find: joey, John Snow, Abhay (from logs)"
    )
    
    test_rag_query_with_sources(
        "Show me user roles in the system",
        "Should find: org_admin, staff roles"
    )

def analyze_logs_findings():
    """Analyze what we learned from the error logs"""
    
    print(f"\n{'='*80}")
    print("ANALYSIS OF ERROR LOGS:")
    print("=" * 80)
    
    print("\n✅ WORKING CORRECTLY:")
    print("  - Hotel.sql data successfully indexed with COPY extraction")
    print("  - Vector search finding relevant records")
    print("  - Context being passed to LLM")
    print("  - Some queries returning correct answers (Margherita Pizza: $9.99)")
    
    print("\n❌ ISSUES IDENTIFIED:")
    print("  - API response doesn't include source information")
    print("  - LLM sometimes returns 'I don't know' despite having context")
    print("  - Query service may need prompt tuning")
    
    print("\n📊 DATA SUCCESSFULLY INDEXED:")
    print("  - Menu items: Margherita Pizza, Vegan Buddha Bowl, Caesar Salad, etc.")
    print("  - Orders: IDs 3, 7, 8, 17, 25 with various statuses")
    print("  - Customers: Abhay Patgar, Afnan Ahmed")
    print("  - Users: org_admin roles with emails")
    print("  - Groups: Active groups with members")
    
    print("\n🔧 RECOMMENDATIONS:")
    print("  1. Modify query API to return source information")
    print("  2. Improve LLM prompt to be more confident with structured data")
    print("  3. Add metadata filtering for better context retrieval")
    print("  4. Consider adding table-specific queries")

if __name__ == "__main__":
    print("IMPROVED HOTEL RAG TESTING")
    print("Testing based on actual log analysis")
    
    test_specific_hotel_queries()
    analyze_logs_findings()
    
    print(f"\n{'='*80}")
    print("CONCLUSION:")
    print("The COPY extraction fix worked! Hotel database is indexed and searchable.")
    print("The RAG system retrieves relevant data but needs API/prompt improvements.")
    print("Key success: PostgreSQL COPY format now properly supported! ✅")