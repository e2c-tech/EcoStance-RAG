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
            
            if expected_context:
                print(f"\n✓ Expected context: {expected_context}")
                
        else:
            print(f"ERROR: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"REQUEST ERROR: {e}")
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")

def main():
    """Test RAG queries against Excel sales data"""
    
    print("Testing RAG queries against certifydigital Monthly Sales demo.xlsx")
    print("=" * 80)
    
    # Test 1: General sales data queries
    test_rag_query(
        "What sales data is available?",
        "Should find monthly sales information from Excel file"
    )
    
    test_rag_query(
        "Show me the sales figures",
        "Should display sales numbers from the spreadsheet"
    )
    
    # Test 2: Monthly/time-based queries
    test_rag_query(
        "What are the monthly sales totals?",
        "Should show sales broken down by month"
    )
    
    test_rag_query(
        "Which month had the highest sales?",
        "Should identify the peak sales month"
    )
    
    test_rag_query(
        "Show me sales trends over time",
        "Should analyze sales progression across months"
    )
    
    # Test 3: Product/category queries
    test_rag_query(
        "What products or services are being sold?",
        "Should list items from the sales data"
    )
    
    test_rag_query(
        "Which product category performs best?",
        "Should identify top-performing categories"
    )
    
    # Test 4: Financial analysis queries
    test_rag_query(
        "What is the total revenue?",
        "Should calculate total sales amount"
    )
    
    test_rag_query(
        "Calculate the average monthly sales",
        "Should compute average sales per month"
    )
    
    test_rag_query(
        "Show me sales growth percentage",
        "Should analyze month-over-month growth"
    )
    
    # Test 5: Specific data queries
    test_rag_query(
        "What are the sales figures for digital certification services?",
        "Should find certifydigital specific data"
    )
    
    test_rag_query(
        "Show me customer acquisition data",
        "Should find customer-related metrics"
    )
    
    test_rag_query(
        "What regions or markets are covered?",
        "Should identify geographical sales data"
    )
    
    # Test 6: Comparative queries
    test_rag_query(
        "Compare Q1 vs Q2 sales performance",
        "Should analyze quarterly comparisons"
    )
    
    test_rag_query(
        "Which sales channels are most effective?",
        "Should identify top-performing channels"
    )
    
    print(f"\n{'='*80}")
    print("EXCEL RAG TESTING COMPLETED!")
    print("=" * 80)
    
    print("\nWhat to verify:")
    print("1. ✅ Excel file data is properly extracted and indexed")
    print("2. ✅ Spreadsheet rows are converted to searchable text")
    print("3. ✅ Sales figures and metrics are accessible via RAG")
    print("4. ✅ Monthly/temporal data queries work correctly")
    print("5. ✅ Financial calculations and analysis are possible")
    
    print("\nExpected data types from Excel:")
    print("- Monthly sales figures")
    print("- Product/service categories")
    print("- Revenue amounts")
    print("- Customer metrics")
    print("- Time-series data")
    print("- Performance indicators")
    
    print(f"\n📊 File being tested: uploads/certifydigital Monthly Sales demo.xlsx")
    print(f"🎯 Knowledge base: {KB_NAME}")
    print(f"🔍 Check server logs for detailed context retrieval information")

if __name__ == "__main__":
    main()