"""
Enhanced Tax Data Processing Script
Processes comprehensive tax scenarios and creates enriched training data
"""
import json
import os
from pathlib import Path

def process_comprehensive_tax_data():
    """Process and combine all tax training data files"""
    
    # Define all training data files
    data_files = [
        "training_data/form16_finetune.jsonl",
        "training_data/comprehensive_tax_finetune.jsonl", 
        "training_data/form16_detailed_analysis.jsonl"
    ]
    
    combined_data = []
    
    for file_path in data_files:
        if os.path.exists(file_path):
            print(f"Processing {file_path}...")
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        combined_data.append(data)
                    except json.JSONDecodeError as e:
                        print(f"Error processing line in {file_path}: {e}")
                        continue
    
    # Save combined training data
    output_file = "training_data/combined_comprehensive_finetune.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for data in combined_data:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    
    print(f"Combined {len(combined_data)} training examples into {output_file}")
    return len(combined_data)

def create_tax_scenario_templates():
    """Create templates for common tax scenarios"""
    
    scenarios = {
        "salary_analysis": {
            "keywords": ["salary", "form 16", "breakdown", "components"],
            "response_structure": {
                "summary": "Brief overview of salary structure and tax implications",
                "salary_breakdown": "Table showing each component and tax treatment", 
                "exemptions": "Available exemptions and optimization opportunities",
                "recommendations": "Specific actions to reduce tax liability"
            }
        },
        "regime_comparison": {
            "keywords": ["old regime", "new regime", "compare", "which is better"],
            "response_structure": {
                "comparison_table": "Side-by-side regime comparison",
                "breakeven_analysis": "Income level where regimes are equal",
                "recommendation": "Clear guidance on optimal choice",
                "switching_strategy": "When and how to switch"
            }
        },
        "investment_planning": {
            "keywords": ["investment", "80c", "tax saving", "deduction", "planning"],
            "response_structure": {
                "priority_matrix": "Investment options ranked by priority",
                "allocation_strategy": "Recommended investment distribution", 
                "implementation_plan": "Monthly/annual investment schedule",
                "tax_savings": "Expected tax benefits from each option"
            }
        },
        "form16_analysis": {
            "keywords": ["form 16", "analyze", "understand", "explain"],
            "response_structure": {
                "part_a_analysis": "TDS and employer details verification",
                "part_b_breakdown": "Complete salary and deduction analysis",
                "verification_checklist": "Points to cross-check",
                "optimization_opportunities": "Areas for tax improvement"
            }
        }
    }
    
    # Save scenario templates
    with open("data/tax_scenario_templates.json", 'w', encoding='utf-8') as f:
        json.dump(scenarios, f, indent=2, ensure_ascii=False)
    
    print("Created tax scenario templates")
    return scenarios

def validate_training_data():
    """Validate the training data for completeness and accuracy"""
    
    validation_results = {
        "total_examples": 0,
        "scenario_coverage": {},
        "missing_elements": []
    }
    
    required_elements = [
        "Summary:",
        "table format",
        "⚠️ **Disclaimer:**"
    ]
    
    files_to_validate = [
        "training_data/comprehensive_tax_finetune.jsonl",
        "training_data/form16_detailed_analysis.jsonl",
        "training_data/comprehensive_validation.jsonl"
    ]
    
    for file_path in files_to_validate:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())
                        validation_results["total_examples"] += 1
                        
                        # Check for assistant response completeness
                        messages = data.get("messages", [])
                        assistant_msg = next((msg for msg in messages if msg["role"] == "assistant"), None)
                        
                        if assistant_msg:
                            content = assistant_msg["content"]
                            
                            # Check for required elements
                            for element in required_elements:
                                if element not in content:
                                    validation_results["missing_elements"].append({
                                        "file": file_path,
                                        "line": line_num,
                                        "missing": element
                                    })
                            
                            # Categorize by scenario
                            user_msg = next((msg for msg in messages if msg["role"] == "user"), None)
                            if user_msg:
                                user_question = user_msg["content"].lower()
                                if "salary" in user_question or "form 16" in user_question:
                                    validation_results["scenario_coverage"]["salary_analysis"] = validation_results["scenario_coverage"].get("salary_analysis", 0) + 1
                                elif "regime" in user_question:
                                    validation_results["scenario_coverage"]["regime_comparison"] = validation_results["scenario_coverage"].get("regime_comparison", 0) + 1
                                elif "investment" in user_question or "80c" in user_question:
                                    validation_results["scenario_coverage"]["investment_planning"] = validation_results["scenario_coverage"].get("investment_planning", 0) + 1
                                
                    except json.JSONDecodeError as e:
                        validation_results["missing_elements"].append({
                            "file": file_path,
                            "line": line_num,
                            "error": f"JSON decode error: {e}"
                        })
    
    # Save validation results
    with open("training_data/validation_results.json", 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, indent=2, ensure_ascii=False)
    
    print(f"Validation complete: {validation_results['total_examples']} examples processed")
    print(f"Scenario coverage: {validation_results['scenario_coverage']}")
    print(f"Issues found: {len(validation_results['missing_elements'])}")
    
    return validation_results

def main():
    """Main processing function"""
    print("Starting comprehensive tax data processing...")
    
    # Create directories if they don't exist
    os.makedirs("training_data", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Process training data
    total_examples = process_comprehensive_tax_data()
    
    # Create scenario templates
    scenarios = create_tax_scenario_templates()
    
    # Validate training data
    validation_results = validate_training_data()
    
    print(f"""
    Processing Summary:
    ==================
    Total training examples: {total_examples}
    Scenario templates created: {len(scenarios)}
    Validation issues: {len(validation_results['missing_elements'])}
    
    Files created:
    - training_data/combined_comprehensive_finetune.jsonl
    - data/tax_scenario_templates.json
    - training_data/validation_results.json
    """)

if __name__ == "__main__":
    main()