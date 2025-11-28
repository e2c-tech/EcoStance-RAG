#!/usr/bin/env python3
"""
Automated test suite for ecostance-demo collection
Based on manual_test_questions_ecostance_demo_correct.md
"""

import requests
import json
import time
from typing import Dict, List, Tuple
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
COLLECTION_NAME = "ecostance-demo"
OUTPUT_FILE = "tests/test_results_ecostance_demo.json"
REPORT_FILE = "tests/test_results_ecostance_demo.md"

# Test questions organized by category
TEST_QUESTIONS = {
    "1. Company Information & Overview": {
        "Basic Company Details": [
            "What is CertifyDigital Inc?",
            "What services does CertifyDigital provide?",
            "What is the company's website?",
            "How can I contact CertifyDigital support?",
            "What type of certificates does CertifyDigital offer?",
            "Are the certificates blockchain-secured?",
            "What makes CertifyDigital certificates tamper-proof?",
        ],
        "Business Model": [
            "How does CertifyDigital verify qualifications?",
            "What format are the digital certificates in?",
            "Do certificates include QR codes?",
        ]
    },
    "2. Terms and Conditions": {
        "User Requirements": [
            "What are the terms and conditions?",
            "What is the minimum age to use CertifyDigital services?",
            "What information is required for account registration?",
            "Can I create multiple accounts?",
            "What happens if I provide false information during registration?",
        ],
        "Legal Framework": [
            "What law governs CertifyDigital's terms and conditions?",
            "Where are disputes resolved?",
            "When did the current terms become effective?",
            "How will I be notified of changes to the terms?",
            "What happens if I don't agree to updated terms?",
        ],
        "Account Management": [
            "Can CertifyDigital terminate my account?",
            "Under what conditions can my account be suspended?",
            "What are my responsibilities as a user?",
        ]
    },
    "3. Payments and Billing": {
        "Payment Processing": [
            "How are payments processed?",
            "What currency are prices listed in?",
            "Are fees refundable?",
            "Do prices include taxes?",
            "What payment methods are accepted?",
        ],
        "Billing Policies": [
            "How does automatic renewal work?",
            "Can I cancel my subscription?",
            "What happens if my payment fails?",
            "Are there any setup fees?",
            "How often am I billed?",
        ]
    },
    "4. Return and Refund Policy": {
        "Refund Eligibility": [
            "What is the return and refund policy?",
            "Can I get a refund for digital certificates?",
            "How long do I have to request a refund?",
            "What are valid reasons for a refund?",
            "Are there any non-refundable services?",
        ],
        "Refund Process": [
            "How do I request a refund?",
            "How long does it take to process a refund?",
            "Will I get a full refund or partial refund?",
            "What information do I need to provide for a refund request?",
            "Can I get a refund if I'm not satisfied with the service?",
        ]
    },
    "5. Frequently Asked Questions": {
        "Common Questions": [
            "What are the most frequently asked questions?",
            "How do I verify a certificate?",
            "Can certificates expire?",
            "How do I download my certificate?",
            "What if I lose my certificate?",
            "Can I share my certificate on social media?",
            "Are certificates internationally recognized?",
        ],
        "Technical Support": [
            "What should I do if I can't access my account?",
            "How do I update my profile information?",
            "What browsers are supported?",
            "Can I access certificates on mobile devices?",
        ]
    },
    "6. Sales Data Analysis": {
        "Monthly Performance": [
            "Show me the monthly sales data",
            "What was the revenue in July 2025?",
            "How many certificates were issued in August 2025?",
            "What is the trend in new customer acquisition?",
            "Which month had the highest revenue?",
            "What is the average churn rate?",
        ],
        "Business Metrics": [
            "Calculate the total revenue across all months",
            "What's the average number of certificates issued per month?",
            "Which month had the lowest churn rate?",
            "How many new customers were acquired in total?",
            "What's the relationship between certificates issued and revenue?",
            "Is there a correlation between new customers and churn rate?",
        ],
        "Growth Analysis": [
            "Is revenue growing or declining?",
            "What's the month-over-month growth rate?",
            "Which metrics show the best performance?",
            "What's the revenue per certificate?",
            "How does customer acquisition compare to churn?",
        ]
    },
    "7. Product Information": {
        "Product Catalog": [
            "What products are available?",
            "List all product categories",
            "What are the most expensive products?",
            "Show me products under $50",
            "What products are currently in stock?",
            "Which products are out of stock?",
        ],
        "Product Details": [
            "What information is stored for each product?",
            "How many products are in the database?",
            "What's the average product price?",
            "Which product has the highest price?",
            "Are there any free products or services?",
        ]
    },
    "8. Cross-Document Analysis": {
        "Policy Integration": [
            "How do the terms and conditions relate to the refund policy?",
            "What payment terms are mentioned across all documents?",
            "Are there any contradictions between policies?",
            "What contact information is consistent across documents?",
        ],
        "Business Intelligence": [
            "How do sales trends align with product offerings?",
            "What can the sales data tell us about customer satisfaction?",
            "Do the FAQs address common billing concerns?",
            "How comprehensive is the policy documentation?",
        ]
    },
    "9. Compliance and Legal": {
        "Regulatory Compliance": [
            "What legal disclaimers are included?",
            "How does CertifyDigital limit liability?",
            "What warranties are provided or disclaimed?",
            "Are there any age restrictions for services?",
            "What jurisdiction governs the services?",
        ],
        "Data Protection": [
            "How is user data protected?",
            "What happens to data when an account is terminated?",
            "Are there any privacy policies mentioned?",
        ]
    },
    "10. Customer Experience": {
        "User Journey": [
            "What is the typical customer onboarding process?",
            "How easy is it to get started with CertifyDigital?",
            "What support is available for new users?",
            "How can customers provide feedback?",
        ],
        "Service Quality": [
            "What guarantees does CertifyDigital provide?",
            "How does the company ensure certificate authenticity?",
            "What happens if there's a technical issue?",
            "Are there service level agreements mentioned?",
        ]
    }
}

def query_rag(question: str) -> Tuple[str, float, bool]:
    """
    Query the RAG system and return answer, response time, and success status.
    """
    start_time = time.time()
    
    try:
        data = {
            'collection_name': COLLECTION_NAME,
            'query': question
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/query/",
            data=data,
            timeout=30
        )
        
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', 'No answer provided')
            return answer, elapsed_time, True
        else:
            return f"Error: {response.status_code}", elapsed_time, False
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        return f"Exception: {str(e)}", elapsed_time, False

def evaluate_answer(answer: str) -> Dict:
    """
    Evaluate the quality of an answer.
    """
    answer_lower = answer.lower()
    
    # Check for "I don't know" responses
    if any(phrase in answer_lower for phrase in ["i don't know", "i do not know", "no information", "cannot find"]):
        quality = "no_answer"
    # Check for error responses
    elif answer.startswith("Error:") or answer.startswith("Exception:"):
        quality = "error"
    # Check for very short answers (likely incomplete)
    elif len(answer) < 20:
        quality = "poor"
    # Check for substantial answers
    elif len(answer) > 100:
        quality = "excellent"
    elif len(answer) > 50:
        quality = "good"
    else:
        quality = "partial"
    
    return {
        "quality": quality,
        "length": len(answer),
        "has_numbers": any(char.isdigit() for char in answer),
        "has_details": len(answer.split()) > 20
    }

def run_tests():
    """
    Run all test questions and collect results.
    """
    print("=" * 80)
    print("AUTOMATED TEST SUITE FOR ECOSTANCE-DEMO COLLECTION")
    print("=" * 80)
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    all_results = []
    category_stats = {}
    total_questions = 0
    
    for category, subcategories in TEST_QUESTIONS.items():
        print(f"\n{'='*80}")
        print(f"CATEGORY: {category}")
        print(f"{'='*80}")
        
        category_results = {
            "category": category,
            "subcategories": {},
            "stats": {
                "total": 0,
                "excellent": 0,
                "good": 0,
                "partial": 0,
                "poor": 0,
                "no_answer": 0,
                "error": 0,
                "avg_response_time": 0
            }
        }
        
        for subcategory, questions in subcategories.items():
            print(f"\n{subcategory}:")
            print("-" * 80)
            
            subcategory_results = []
            
            for i, question in enumerate(questions, 1):
                total_questions += 1
                print(f"\nQ{i}: {question}")
                
                # Query the RAG system
                answer, response_time, success = query_rag(question)
                
                # Evaluate the answer
                evaluation = evaluate_answer(answer)
                
                # Store results
                result = {
                    "question": question,
                    "answer": answer,
                    "response_time": round(response_time, 2),
                    "success": success,
                    "evaluation": evaluation
                }
                
                subcategory_results.append(result)
                all_results.append(result)
                
                # Update stats
                quality = evaluation["quality"]
                category_results["stats"]["total"] += 1
                category_results["stats"][quality] += 1
                category_results["stats"]["avg_response_time"] += response_time
                
                # Print result
                quality_symbol = {
                    "excellent": "[EXCELLENT]",
                    "good": "[GOOD]",
                    "partial": "[PARTIAL]",
                    "poor": "[POOR]",
                    "no_answer": "[NO ANSWER]",
                    "error": "[ERROR]"
                }
                
                print(f"   {quality_symbol.get(quality, '[?]')} Quality: {quality.upper()}")
                print(f"   Response Time: {response_time:.2f}s")
                print(f"   Answer: {answer[:150]}{'...' if len(answer) > 150 else ''}")
            
            category_results["subcategories"][subcategory] = subcategory_results
        
        # Calculate average response time
        if category_results["stats"]["total"] > 0:
            category_results["stats"]["avg_response_time"] = round(
                category_results["stats"]["avg_response_time"] / category_results["stats"]["total"], 2
            )
        
        category_stats[category] = category_results["stats"]
    
    return all_results, category_stats, total_questions

def generate_report(all_results: List[Dict], category_stats: Dict, total_questions: int):
    """
    Generate a comprehensive test report.
    """
    # Calculate overall stats
    overall_stats = {
        "total": total_questions,
        "excellent": 0,
        "good": 0,
        "partial": 0,
        "poor": 0,
        "no_answer": 0,
        "error": 0,
        "avg_response_time": 0
    }
    
    for result in all_results:
        quality = result["evaluation"]["quality"]
        overall_stats[quality] += 1
        overall_stats["avg_response_time"] += result["response_time"]
    
    overall_stats["avg_response_time"] = round(
        overall_stats["avg_response_time"] / total_questions, 2
    )
    
    # Generate markdown report
    report = f"""# Test Results for ecostance-demo Collection

**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Collection:** {COLLECTION_NAME}  
**Total Questions:** {total_questions}

---

## 📊 Overall Performance Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| ✅ Excellent Responses | {overall_stats['excellent']} | {overall_stats['excellent']/total_questions*100:.1f}% |
| 👍 Good Responses | {overall_stats['good']} | {overall_stats['good']/total_questions*100:.1f}% |
| ⚠️ Partial Responses | {overall_stats['partial']} | {overall_stats['partial']/total_questions*100:.1f}% |
| ❌ Poor Responses | {overall_stats['poor']} | {overall_stats['poor']/total_questions*100:.1f}% |
| ❓ No Answer | {overall_stats['no_answer']} | {overall_stats['no_answer']/total_questions*100:.1f}% |
| 🔥 Errors | {overall_stats['error']} | {overall_stats['error']/total_questions*100:.1f}% |

**Average Response Time:** {overall_stats['avg_response_time']}s

---

## 📈 Performance by Category

"""
    
    for category, stats in category_stats.items():
        success_rate = ((stats['excellent'] + stats['good']) / stats['total'] * 100) if stats['total'] > 0 else 0
        
        report += f"""
### {category}

- **Total Questions:** {stats['total']}
- **Success Rate:** {success_rate:.1f}% (Excellent + Good)
- **Average Response Time:** {stats['avg_response_time']}s

| Quality | Count |
|---------|-------|
| ✅ Excellent | {stats['excellent']} |
| 👍 Good | {stats['good']} |
| ⚠️ Partial | {stats['partial']} |
| ❌ Poor | {stats['poor']} |
| ❓ No Answer | {stats['no_answer']} |
| 🔥 Error | {stats['error']} |

"""
    
    # Add detailed results section
    report += """
---

## 📝 Detailed Question Results

"""
    
    for i, result in enumerate(all_results, 1):
        quality = result["evaluation"]["quality"]
        quality_emoji = {
            "excellent": "✅",
            "good": "👍",
            "partial": "⚠️",
            "poor": "❌",
            "no_answer": "❓",
            "error": "🔥"
        }
        
        report += f"""
### Q{i}: {result['question']}

**Quality:** {quality_emoji.get(quality, '?')} {quality.upper()}  
**Response Time:** {result['response_time']}s  
**Answer Length:** {result['evaluation']['length']} characters

**Answer:**
```
{result['answer'][:500]}{'...' if len(result['answer']) > 500 else ''}
```

---
"""
    
    # Add recommendations
    report += """
## 💡 Recommendations

"""
    
    if overall_stats['no_answer'] > total_questions * 0.2:
        report += "- ⚠️ **High 'No Answer' Rate:** Consider improving context retrieval or chunking strategy.\n"
    
    if overall_stats['avg_response_time'] > 5:
        report += "- ⚠️ **Slow Response Times:** Consider optimizing embedding model loading or query processing.\n"
    
    if overall_stats['excellent'] + overall_stats['good'] > total_questions * 0.7:
        report += "- ✅ **Strong Performance:** System is performing well on this collection.\n"
    
    if overall_stats['error'] > 0:
        report += f"- 🔥 **Errors Detected:** {overall_stats['error']} queries resulted in errors. Check logs for details.\n"
    
    return report

def main():
    """
    Main test execution function.
    """
    print("\nStarting automated test suite...\n")
    
    # Run all tests
    all_results, category_stats, total_questions = run_tests()
    
    # Save raw results to JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            "test_date": datetime.now().isoformat(),
            "collection": COLLECTION_NAME,
            "total_questions": total_questions,
            "results": all_results,
            "category_stats": category_stats
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Raw results saved to: {OUTPUT_FILE}")
    
    # Generate and save report
    report = generate_report(all_results, category_stats, total_questions)
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"[OK] Test report saved to: {REPORT_FILE}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETED")
    print("=" * 80)
    print(f"Total Questions: {total_questions}")
    print(f"Results saved to: {OUTPUT_FILE}")
    print(f"Report saved to: {REPORT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()