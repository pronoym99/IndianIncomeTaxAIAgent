"""
Comprehensive Tax Assistant Testing Script
Tests all tax scenarios and capabilities requested by user
"""
import asyncio
import json
import requests
import time
from typing import Dict, List, Any

class TaxAssistantTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        
    def test_form16_analysis(self) -> Dict[str, Any]:
        """Test comprehensive Form 16 analysis capabilities"""
        
        test_cases = [
            {
                "name": "Basic Form 16 Analysis",
                "query": """I have received my Form 16 for FY 2023-24. Here are the details:
                
                Part A:
                - Employer: ABC Company Ltd
                - PAN: AAACL1234A
                - TAN: DELC12345B
                - Employee PAN: ABCDE1234F
                - Total TDS deducted: ₹85,000
                
                Part B:
                - Gross Salary: ₹12,00,000
                - Basic Salary: ₹6,00,000
                - HRA: ₹3,00,000
                - Special Allowance: ₹3,00,000
                - Provident Fund: ₹72,000
                - Standard Deduction: ₹50,000
                - 80C Investments: ₹1,50,000
                - 80D Health Insurance: ₹25,000
                
                Can you provide a comprehensive analysis of my Form 16 and suggest optimizations?""",
                "expected_elements": [
                    "Part A Analysis",
                    "Part B Breakdown", 
                    "salary components",
                    "tax computation",
                    "optimization suggestions",
                    "table format",
                    "regime comparison"
                ]
            }
        ]
        
        results = []
        for test_case in test_cases:
            response = self._make_request(test_case["query"])
            results.append(self._validate_response(test_case, response))
            
        return {
            "category": "Form 16 Analysis",
            "tests": results,
            "passed": sum(1 for r in results if r["passed"]),
            "total": len(results)
        }
    
    def test_regime_comparison(self) -> Dict[str, Any]:
        """Test old vs new tax regime comparison"""
        
        test_cases = [
            {
                "name": "Regime Comparison for Salaried Employee",
                "query": """I'm a software engineer with ₹15 lakh annual salary. I have the following:
                - 80C investments: ₹1.5 lakh
                - 80D health insurance: ₹50,000
                - Home loan interest: ₹2 lakh
                - HRA: ₹6 lakh (living in metro city)
                
                Should I choose old or new tax regime? Please provide detailed comparison.""",
                "expected_elements": [
                    "regime comparison",
                    "table",
                    "tax calculation",
                    "recommendation",
                    "breakeven analysis",
                    "optimization"
                ]
            }
        ]
        
        results = []
        for test_case in test_cases:
            response = self._make_request(test_case["query"])
            results.append(self._validate_response(test_case, response))
            
        return {
            "category": "Regime Comparison", 
            "tests": results,
            "passed": sum(1 for r in results if r["passed"]),
            "total": len(results)
        }
    
    def test_deduction_optimization(self) -> Dict[str, Any]:
        """Test comprehensive deduction analysis and optimization"""
        
        test_cases = [
            {
                "name": "80C Deduction Optimization",
                "query": """I want to maximize my 80C deductions. My details:
                - Annual salary: ₹10 lakh
                - Current EPF: ₹60,000
                - Current investments: ₹50,000 in ELSS
                
                What are all available 80C options and how should I optimize?""",
                "expected_elements": [
                    "80C options",
                    "priority ranking",
                    "investment strategy", 
                    "tax savings",
                    "allocation table",
                    "specific recommendations"
                ]
            },
            {
                "name": "Health Insurance Deduction (80D)",
                "query": """Guide me on 80D health insurance deductions. I'm 35 years old, my parents are 65. 
                What's the maximum deduction I can claim and best strategy?""",
                "expected_elements": [
                    "80D limits",
                    "age-based benefits",
                    "maximum deduction",
                    "strategy",
                    "preventive health checkup"
                ]
            }
        ]
        
        results = []
        for test_case in test_cases:
            response = self._make_request(test_case["query"])
            results.append(self._validate_response(test_case, response))
            
        return {
            "category": "Deduction Optimization",
            "tests": results, 
            "passed": sum(1 for r in results if r["passed"]),
            "total": len(results)
        }
    
    def test_investment_planning(self) -> Dict[str, Any]:
        """Test comprehensive investment planning and tax optimization"""
        
        test_cases = [
            {
                "name": "Tax-Saving Investment Planning",
                "query": """I'm 28 years old, earning ₹8 lakh annually. I want to:
                1. Save maximum tax
                2. Build wealth for retirement
                3. Create emergency fund
                
                Please suggest a comprehensive investment plan with tax optimization.""",
                "expected_elements": [
                    "investment priority",
                    "tax-saving options",
                    "asset allocation",
                    "monthly planning",
                    "expected returns",
                    "tax benefits"
                ]
            }
        ]
        
        results = []
        for test_case in test_cases:
            response = self._make_request(test_case["query"])
            results.append(self._validate_response(test_case, response))
            
        return {
            "category": "Investment Planning",
            "tests": results,
            "passed": sum(1 for r in results if r["passed"]),
            "total": len(results)
        }
    
    def test_salary_analysis(self) -> Dict[str, Any]:
        """Test detailed salary breakdown and tax implications"""
        
        test_cases = [
            {
                "name": "Salary Structure Analysis",
                "query": """My company is restructuring salary. Current: ₹12 lakh CTC
                Proposed structure:
                - Basic: ₹6 lakh
                - HRA: ₹3 lakh  
                - Conveyance: ₹2.4 lakh
                - Medical: ₹15,000
                - LTA: ₹60,000
                - Special allowance: Balance
                
                Analyze the tax impact and suggest optimizations.""",
                "expected_elements": [
                    "salary breakdown",
                    "tax treatment",
                    "exemptions available",
                    "optimization suggestions",
                    "comparison table"
                ]
            }
        ]
        
        results = []
        for test_case in test_cases:
            response = self._make_request(test_case["query"])
            results.append(self._validate_response(test_case, response))
            
        return {
            "category": "Salary Analysis",
            "tests": results,
            "passed": sum(1 for r in results if r["passed"]),
            "total": len(results)
        }
    
    def _make_request(self, query: str) -> Dict[str, Any]:
        """Make request to the tax assistant API"""
        try:
            payload = {
                "message": query,
                "context_data": {
                    "user_profile": "salaried_employee",
                    "analysis_type": "comprehensive"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"HTTP {response.status_code}",
                    "message": response.text
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "error": "Request failed",
                "message": str(e)
            }
    
    def _validate_response(self, test_case: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate API response against expected elements"""
        
        result = {
            "test_name": test_case["name"],
            "passed": False,
            "found_elements": [],
            "missing_elements": [],
            "response_quality": {
                "has_summary": False,
                "has_tables": False,
                "has_recommendations": False,
                "has_disclaimer": False,
                "response_length": 0
            }
        }
        
        if "error" in response:
            result["error"] = response["error"]
            return result
        
        # Extract response content
        response_text = ""
        if "response" in response:
            response_text = response["response"]
        elif "message" in response:
            response_text = response["message"]
        
        result["response_quality"]["response_length"] = len(response_text)
        
        # Check for expected elements
        response_lower = response_text.lower()
        
        for element in test_case["expected_elements"]:
            if element.lower() in response_lower:
                result["found_elements"].append(element)
            else:
                result["missing_elements"].append(element)
        
        # Check response quality indicators
        result["response_quality"]["has_summary"] = "summary" in response_lower
        result["response_quality"]["has_tables"] = "|" in response_text or "table" in response_lower
        result["response_quality"]["has_recommendations"] = "recommend" in response_lower or "suggest" in response_lower
        result["response_quality"]["has_disclaimer"] = "disclaimer" in response_lower
        
        # Determine if test passed (found at least 70% of expected elements)
        found_percentage = len(result["found_elements"]) / len(test_case["expected_elements"])
        result["passed"] = found_percentage >= 0.7 and result["response_quality"]["response_length"] > 500
        
        return result
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all test categories"""
        
        print("🧪 Starting Comprehensive Tax Assistant Testing...\n")
        
        test_categories = [
            ("Form 16 Analysis", self.test_form16_analysis),
            ("Regime Comparison", self.test_regime_comparison), 
            ("Deduction Optimization", self.test_deduction_optimization),
            ("Investment Planning", self.test_investment_planning),
            ("Salary Analysis", self.test_salary_analysis)
        ]
        
        all_results = {
            "test_summary": {
                "total_categories": len(test_categories),
                "total_tests": 0,
                "total_passed": 0,
                "start_time": time.time()
            },
            "category_results": []
        }
        
        for category_name, test_func in test_categories:
            print(f"🔍 Testing {category_name}...")
            category_result = test_func()
            all_results["category_results"].append(category_result)
            
            all_results["test_summary"]["total_tests"] += category_result["total"]
            all_results["test_summary"]["total_passed"] += category_result["passed"]
            
            print(f"   ✅ {category_result['passed']}/{category_result['total']} tests passed\n")
        
        all_results["test_summary"]["end_time"] = time.time()
        all_results["test_summary"]["duration"] = all_results["test_summary"]["end_time"] - all_results["test_summary"]["start_time"]
        all_results["test_summary"]["success_rate"] = all_results["test_summary"]["total_passed"] / all_results["test_summary"]["total_tests"] if all_results["test_summary"]["total_tests"] > 0 else 0
        
        return all_results
    
    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive test report"""
        
        report = f"""
# 📊 Tax Assistant Comprehensive Test Report

## 📈 Overall Results
- **Total Tests**: {results['test_summary']['total_tests']}
- **Tests Passed**: {results['test_summary']['total_passed']}
- **Success Rate**: {results['test_summary']['success_rate']:.1%}
- **Duration**: {results['test_summary']['duration']:.2f} seconds

## 📋 Category Breakdown
"""
        
        for category in results["category_results"]:
            status_emoji = "✅" if category["passed"] == category["total"] else "⚠️" if category["passed"] > 0 else "❌"
            report += f"""
### {status_emoji} {category['category']}
- **Tests**: {category['passed']}/{category['total']} passed
"""
            
            for test in category["tests"]:
                test_status = "✅" if test["passed"] else "❌"
                report += f"  - {test_status} {test['test_name']}\n"
                
                if not test["passed"]:
                    report += f"    - **Missing**: {', '.join(test['missing_elements'])}\n"
                    if "error" in test:
                        report += f"    - **Error**: {test['error']}\n"

        report += f"""
## 🎯 Capabilities Verified

### ✅ Successfully Tested:
"""
        
        successful_categories = [cat for cat in results["category_results"] if cat["passed"] > 0]
        for category in successful_categories:
            report += f"- {category['category']}\n"

        if len(successful_categories) < len(results["category_results"]):
            failed_categories = [cat for cat in results["category_results"] if cat["passed"] == 0]
            report += f"""
### ❌ Need Attention:
"""
            for category in failed_categories:
                report += f"- {category['category']}\n"

        return report

def main():
    """Main testing function"""
    
    print("🚀 Tax Assistant Comprehensive Testing Suite")
    print("=" * 50)
    
    # Initialize tester
    tester = TaxAssistantTester()
    
    # Run comprehensive tests
    results = tester.run_comprehensive_test()
    
    # Generate and save report
    report = tester.generate_test_report(results)
    
    # Save results
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    with open("test_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("📄 Test Report Generated:")
    print(report)
    
    return results

if __name__ == "__main__":
    main()