"""
Integration tests for the Tax Assistant /chat API endpoint.

These tests send real HTTP requests to localhost:8000.
They are skipped automatically when the server is not running.

Run the server first:
    uvicorn app:app --reload

Then run:
    pytest test_comprehensive_system.py -v
"""
import unittest
import pytest
import requests


BASE_URL = "http://localhost:8000"
MIN_RESPONSE_LENGTH = 500
MIN_ELEMENT_MATCH_RATIO = 0.7


def _server_reachable() -> bool:
    """Return True if the local API server responds."""
    try:
        requests.get(BASE_URL, timeout=3)
        return True
    except requests.exceptions.ConnectionError:
        return False


skip_no_server = pytest.mark.skipif(
    not _server_reachable(),
    reason="API server not running on localhost:8000",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _post_chat(query: str) -> dict:
    """POST a query to /chat and return the JSON response."""
    payload = {
        "message": query,
        "context_data": {
            "user_profile": "salaried_employee",
            "analysis_type": "comprehensive",
        },
    }
    resp = requests.post(
        f"{BASE_URL}/chat",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _extract_text(response: dict) -> str:
    """Extract the textual content from the API JSON response."""
    return response.get("response", "") or response.get("message", "")


# ---------------------------------------------------------------------------
# 1. Form 16 Analysis
# ---------------------------------------------------------------------------
@skip_no_server
class TestForm16Analysis(unittest.TestCase):
    """Test comprehensive Form 16 analysis via /chat."""

    QUERY = (
        "I have received my Form 16 for FY 2023-24. Here are the details:\n"
        "Part A:\n"
        "- Employer: ABC Company Ltd\n"
        "- PAN: AAACL1234A\n"
        "- TAN: DELC12345B\n"
        "- Employee PAN: ABCDE1234F\n"
        "- Total TDS deducted: ₹85,000\n\n"
        "Part B:\n"
        "- Gross Salary: ₹12,00,000\n"
        "- Basic Salary: ₹6,00,000\n"
        "- HRA: ₹3,00,000\n"
        "- Special Allowance: ₹3,00,000\n"
        "- Provident Fund: ₹72,000\n"
        "- Standard Deduction: ₹50,000\n"
        "- 80C Investments: ₹1,50,000\n"
        "- 80D Health Insurance: ₹25,000\n\n"
        "Can you provide a comprehensive analysis of my Form 16 and suggest optimizations?"
    )
    EXPECTED_ELEMENTS = [
        "Part A Analysis",
        "Part B Breakdown",
        "salary components",
        "tax computation",
        "optimization suggestions",
        "table format",
        "regime comparison",
    ]

    def setUp(self):
        self.response = _post_chat(self.QUERY)
        self.text = _extract_text(self.response)

    def test_response_not_empty(self):
        self.assertGreater(len(self.text), 0, "Response body is empty")

    def test_response_long_enough(self):
        self.assertGreaterEqual(
            len(self.text), MIN_RESPONSE_LENGTH,
            f"Response too short ({len(self.text)} chars)",
        )

    def test_expected_elements_present(self):
        lower = self.text.lower()
        found = [e for e in self.EXPECTED_ELEMENTS if e.lower() in lower]
        ratio = len(found) / len(self.EXPECTED_ELEMENTS)
        self.assertGreaterEqual(
            ratio, MIN_ELEMENT_MATCH_RATIO,
            f"Only {len(found)}/{len(self.EXPECTED_ELEMENTS)} elements found: {found}",
        )


# ---------------------------------------------------------------------------
# 2. Regime Comparison
# ---------------------------------------------------------------------------
@skip_no_server
class TestRegimeComparison(unittest.TestCase):
    """Test old vs new tax regime comparison via /chat."""

    QUERY = (
        "I'm a software engineer with ₹15 lakh annual salary. I have the following:\n"
        "- 80C investments: ₹1.5 lakh\n"
        "- 80D health insurance: ₹50,000\n"
        "- Home loan interest: ₹2 lakh\n"
        "- HRA: ₹6 lakh (living in metro city)\n\n"
        "Should I choose old or new tax regime? Please provide detailed comparison."
    )
    EXPECTED_ELEMENTS = [
        "regime comparison",
        "table",
        "tax calculation",
        "recommendation",
        "breakeven analysis",
        "optimization",
    ]

    def setUp(self):
        self.response = _post_chat(self.QUERY)
        self.text = _extract_text(self.response)

    def test_response_long_enough(self):
        self.assertGreaterEqual(len(self.text), MIN_RESPONSE_LENGTH)

    def test_expected_elements_present(self):
        lower = self.text.lower()
        found = [e for e in self.EXPECTED_ELEMENTS if e.lower() in lower]
        ratio = len(found) / len(self.EXPECTED_ELEMENTS)
        self.assertGreaterEqual(ratio, MIN_ELEMENT_MATCH_RATIO)

    def test_contains_recommendations(self):
        lower = self.text.lower()
        self.assertTrue(
            "recommend" in lower or "suggest" in lower,
            "Response lacks recommendations or suggestions",
        )


# ---------------------------------------------------------------------------
# 3. Deduction Optimization — 80C
# ---------------------------------------------------------------------------
@skip_no_server
class TestDeduction80C(unittest.TestCase):
    """Test 80C deduction optimisation via /chat."""

    QUERY = (
        "I want to maximize my 80C deductions. My details:\n"
        "- Annual salary: ₹10 lakh\n"
        "- Current EPF: ₹60,000\n"
        "- Current investments: ₹50,000 in ELSS\n\n"
        "What are all available 80C options and how should I optimize?"
    )
    EXPECTED_ELEMENTS = [
        "80C options",
        "priority ranking",
        "investment strategy",
        "tax savings",
        "allocation table",
        "specific recommendations",
    ]

    def setUp(self):
        self.response = _post_chat(self.QUERY)
        self.text = _extract_text(self.response)

    def test_response_long_enough(self):
        self.assertGreaterEqual(len(self.text), MIN_RESPONSE_LENGTH)

    def test_expected_elements_present(self):
        lower = self.text.lower()
        found = [e for e in self.EXPECTED_ELEMENTS if e.lower() in lower]
        ratio = len(found) / len(self.EXPECTED_ELEMENTS)
        self.assertGreaterEqual(ratio, MIN_ELEMENT_MATCH_RATIO)


# ---------------------------------------------------------------------------
# 4. Deduction Optimization — 80D (Health Insurance)
# ---------------------------------------------------------------------------
@skip_no_server
class TestDeduction80D(unittest.TestCase):
    """Test 80D health insurance deduction analysis via /chat."""

    QUERY = (
        "Guide me on 80D health insurance deductions. "
        "I'm 35 years old, my parents are 65. "
        "What's the maximum deduction I can claim and best strategy?"
    )
    EXPECTED_ELEMENTS = [
        "80D limits",
        "age-based benefits",
        "maximum deduction",
        "strategy",
        "preventive health checkup",
    ]

    def setUp(self):
        self.response = _post_chat(self.QUERY)
        self.text = _extract_text(self.response)

    def test_response_long_enough(self):
        self.assertGreaterEqual(len(self.text), MIN_RESPONSE_LENGTH)

    def test_expected_elements_present(self):
        lower = self.text.lower()
        found = [e for e in self.EXPECTED_ELEMENTS if e.lower() in lower]
        ratio = len(found) / len(self.EXPECTED_ELEMENTS)
        self.assertGreaterEqual(ratio, MIN_ELEMENT_MATCH_RATIO)


# ---------------------------------------------------------------------------
# 5. Investment Planning
# ---------------------------------------------------------------------------
@skip_no_server
class TestInvestmentPlanning(unittest.TestCase):
    """Test tax-saving investment planning via /chat."""

    QUERY = (
        "I'm 28 years old, earning ₹8 lakh annually. I want to:\n"
        "1. Save maximum tax\n"
        "2. Build wealth for retirement\n"
        "3. Create emergency fund\n\n"
        "Please suggest a comprehensive investment plan with tax optimization."
    )
    EXPECTED_ELEMENTS = [
        "investment priority",
        "tax-saving options",
        "asset allocation",
        "monthly planning",
        "expected returns",
        "tax benefits",
    ]

    def setUp(self):
        self.response = _post_chat(self.QUERY)
        self.text = _extract_text(self.response)

    def test_response_long_enough(self):
        self.assertGreaterEqual(len(self.text), MIN_RESPONSE_LENGTH)

    def test_expected_elements_present(self):
        lower = self.text.lower()
        found = [e for e in self.EXPECTED_ELEMENTS if e.lower() in lower]
        ratio = len(found) / len(self.EXPECTED_ELEMENTS)
        self.assertGreaterEqual(ratio, MIN_ELEMENT_MATCH_RATIO)


# ---------------------------------------------------------------------------
# 6. Salary Structure Analysis
# ---------------------------------------------------------------------------
@skip_no_server
class TestSalaryAnalysis(unittest.TestCase):
    """Test salary breakdown and tax impact analysis via /chat."""

    QUERY = (
        "My company is restructuring salary. Current: ₹12 lakh CTC\n"
        "Proposed structure:\n"
        "- Basic: ₹6 lakh\n"
        "- HRA: ₹3 lakh\n"
        "- Conveyance: ₹2.4 lakh\n"
        "- Medical: ₹15,000\n"
        "- LTA: ₹60,000\n"
        "- Special allowance: Balance\n\n"
        "Analyze the tax impact and suggest optimizations."
    )
    EXPECTED_ELEMENTS = [
        "salary breakdown",
        "tax treatment",
        "exemptions available",
        "optimization suggestions",
        "comparison table",
    ]

    def setUp(self):
        self.response = _post_chat(self.QUERY)
        self.text = _extract_text(self.response)

    def test_response_long_enough(self):
        self.assertGreaterEqual(len(self.text), MIN_RESPONSE_LENGTH)

    def test_expected_elements_present(self):
        lower = self.text.lower()
        found = [e for e in self.EXPECTED_ELEMENTS if e.lower() in lower]
        ratio = len(found) / len(self.EXPECTED_ELEMENTS)
        self.assertGreaterEqual(ratio, MIN_ELEMENT_MATCH_RATIO)