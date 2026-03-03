#!/usr/bin/env python3
"""
Integration tests for the Enhanced Tax Assistant using direct LLM calls.

These tests call the OpenAI / Azure OpenAI model through ``create_client()``
and ``get_deployment_name()``.  They are skipped automatically when valid
API credentials or a deployment name are not configured.

Run:
    pytest test_comprehensive_tax_system.py -v
"""
import os
import unittest
import pytest
from azure_openai import create_client, get_deployment_name


# ---------------------------------------------------------------------------
# Skip condition — client and model must be available
# ---------------------------------------------------------------------------
def _client_available() -> bool:
    """Return True if create_client() + get_deployment_name() succeed."""
    try:
        client = create_client()
        model = get_deployment_name()
        return client is not None and model is not None
    except Exception:
        return False


skip_no_client = pytest.mark.skipif(
    not _client_available(),
    reason="OpenAI / Azure client not configured (missing env vars or model)",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_system_prompt() -> str:
    """Load the comprehensive system prompt."""
    path = "docs/system_prompt.md"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "Default system prompt"


def _query_model(query: str) -> str:
    """Send *query* to the LLM and return the response text.

    Returns the raw content string, or an ``"Error: ..."`` string on
    failure so individual tests can assert accordingly.
    """
    client = create_client()
    model = get_deployment_name()
    system_prompt = _load_system_prompt()
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            max_tokens=1500,
        )
        return response.choices[0].message.content
    except Exception as exc:
        return f"Error: {exc}"


# Minimum number of tax-related keywords that must appear in a valid answer.
TAX_KEYWORDS = ["tax", "deduction", "income", "₹", "section", "calculation", "recommendation"]
MIN_KEYWORD_MATCHES = 4


# ---------------------------------------------------------------------------
# 1. Form 16 Analysis
# ---------------------------------------------------------------------------
@skip_no_client
class TestForm16PartAB(unittest.TestCase):
    """Form 16 Part A & B Analysis."""

    QUERY = (
        "I have a Form 16 with basic salary of ₹800,000, HRA of ₹240,000, "
        "and TDS of ₹45,000. Analyze Part A and Part B components in detail "
        "including salary breakdown, deductions claimed, and tax calculations."
    )

    def setUp(self):
        self.response = _query_model(self.QUERY)

    def test_no_error(self):
        self.assertFalse(self.response.startswith("Error:"), self.response)

    def test_contains_tax_keywords(self):
        lower = self.response.lower()
        found = sum(1 for kw in TAX_KEYWORDS if kw in lower)
        self.assertGreaterEqual(found, MIN_KEYWORD_MATCHES)


@skip_no_client
class TestSalaryComponentBreakdown(unittest.TestCase):
    """Salary Component Breakdown."""

    QUERY = (
        "My CTC is ₹1,200,000 with basic ₹600,000, HRA ₹180,000, "
        "special allowance ₹300,000, and EPF contribution ₹21,600. "
        "Break down all components and their tax implications."
    )

    def setUp(self):
        self.response = _query_model(self.QUERY)

    def test_no_error(self):
        self.assertFalse(self.response.startswith("Error:"), self.response)

    def test_contains_tax_keywords(self):
        lower = self.response.lower()
        found = sum(1 for kw in TAX_KEYWORDS if kw in lower)
        self.assertGreaterEqual(found, MIN_KEYWORD_MATCHES)


# ---------------------------------------------------------------------------
# 2. Tax Regime Comparison
# ---------------------------------------------------------------------------
@skip_no_client
class TestOldVsNewRegime(unittest.TestCase):
    """Old vs New Regime Analysis."""

    QUERY = (
        "Compare old vs new tax regime for salary ₹1,500,000, "
        "with 80C investments ₹150,000, health insurance ₹25,000, "
        "and home loan interest ₹200,000. Which regime is better?"
    )

    def setUp(self):
        self.response = _query_model(self.QUERY)

    def test_no_error(self):
        self.assertFalse(self.response.startswith("Error:"), self.response)

    def test_contains_tax_keywords(self):
        lower = self.response.lower()
        found = sum(1 for kw in TAX_KEYWORDS if kw in lower)
        self.assertGreaterEqual(found, MIN_KEYWORD_MATCHES)

    def test_mentions_regime(self):
        self.assertIn("regime", self.response.lower())


@skip_no_client
class TestMultiYearRegimeProjection(unittest.TestCase):
    """Multi-year Regime Projection."""

    QUERY = (
        "I'm 28 years old, earning ₹800,000 annually with expected 15% "
        "yearly growth. Compare both regimes for next 5 years and "
        "recommend optimal strategy."
    )

    def setUp(self):
        self.response = _query_model(self.QUERY)

    def test_no_error(self):
        self.assertFalse(self.response.startswith("Error:"), self.response)

    def test_contains_tax_keywords(self):
        lower = self.response.lower()
        found = sum(1 for kw in TAX_KEYWORDS if kw in lower)
        self.assertGreaterEqual(found, MIN_KEYWORD_MATCHES)


# ---------------------------------------------------------------------------
# 3. Investment & Deduction Analysis
# ---------------------------------------------------------------------------
@skip_no_client
class TestCompleteDeductionAnalysis(unittest.TestCase):
    """Complete Deduction Analysis (80C / 80D / 80E / 80G / 80TTA)."""

    QUERY = (
        "Analyze all possible deductions for my situation: Section 80C, "
        "80D, 80E, 80G, 80TTA. My salary is ₹1,000,000, I have health "
        "insurance premiums ₹30,000, education loan interest ₹45,000."
    )

    def setUp(self):
        self.response = _query_model(self.QUERY)

    def test_no_error(self):
        self.assertFalse(self.response.startswith("Error:"), self.response)

    def test_contains_tax_keywords(self):
        lower = self.response.lower()
        found = sum(1 for kw in TAX_KEYWORDS if kw in lower)
        self.assertGreaterEqual(found, MIN_KEYWORD_MATCHES)

    def test_mentions_sections(self):
        lower = self.response.lower()
        self.assertTrue("80c" in lower or "80d" in lower)


@skip_no_client
class TestInvestmentRecommendations(unittest.TestCase):
    """Investment Recommendations."""

    QUERY = (
        "I'm 30 years old, risk-moderate investor, salary ₹1,200,000. "
        "Recommend optimal tax-saving investments and long-term wealth "
        "creation strategy."
    )

    def setUp(self):
        self.response = _query_model(self.QUERY)

    def test_no_error(self):
        self.assertFalse(self.response.startswith("Error:"), self.response)

    def test_contains_tax_keywords(self):
        lower = self.response.lower()
        found = sum(1 for kw in TAX_KEYWORDS if kw in lower)
        self.assertGreaterEqual(found, MIN_KEYWORD_MATCHES)

    def test_mentions_investment(self):
        self.assertIn("invest", self.response.lower())


# ---------------------------------------------------------------------------
# 4. HRA & Housing Analysis
# ---------------------------------------------------------------------------
@skip_no_client
class TestHRAOptimization(unittest.TestCase):
    """HRA Optimization."""

    QUERY = (
        "I live in Mumbai (metro), pay rent ₹25,000/month, HRA component "
        "₹300,000, basic salary ₹600,000. Calculate optimal HRA exemption "
        "and benefits."
    )

    def setUp(self):
        self.response = _query_model(self.QUERY)

    def test_no_error(self):
        self.assertFalse(self.response.startswith("Error:"), self.response)

    def test_contains_tax_keywords(self):
        lower = self.response.lower()
        found = sum(1 for kw in TAX_KEYWORDS if kw in lower)
        self.assertGreaterEqual(found, MIN_KEYWORD_MATCHES)

    def test_mentions_hra(self):
        self.assertIn("hra", self.response.lower())


@skip_no_client
class TestRentVsBuy(unittest.TestCase):
    """Rent vs Buy Analysis."""

    QUERY = (
        "Should I buy a house with home loan EMI ₹40,000/month or continue "
        "renting at ₹25,000/month? My salary is ₹1,500,000. Show tax "
        "implications."
    )

    def setUp(self):
        self.response = _query_model(self.QUERY)

    def test_no_error(self):
        self.assertFalse(self.response.startswith("Error:"), self.response)

    def test_contains_tax_keywords(self):
        lower = self.response.lower()
        found = sum(1 for kw in TAX_KEYWORDS if kw in lower)
        self.assertGreaterEqual(found, MIN_KEYWORD_MATCHES)


# ---------------------------------------------------------------------------
# 5. Health Insurance Analysis
# ---------------------------------------------------------------------------
@skip_no_client
class TestSection80DOptimization(unittest.TestCase):
    """Section 80D Optimization."""

    QUERY = (
        "I pay health insurance: ₹15,000 for self, ₹25,000 for parents "
        "(age 58), ₹30,000 for parents-in-law (age 65). Calculate Section "
        "80D benefits and optimization."
    )

    def setUp(self):
        self.response = _query_model(self.QUERY)

    def test_no_error(self):
        self.assertFalse(self.response.startswith("Error:"), self.response)

    def test_contains_tax_keywords(self):
        lower = self.response.lower()
        found = sum(1 for kw in TAX_KEYWORDS if kw in lower)
        self.assertGreaterEqual(found, MIN_KEYWORD_MATCHES)


# ---------------------------------------------------------------------------
# 6. Tax Assessment
# ---------------------------------------------------------------------------
@skip_no_client
class TestCompleteTaxLiability(unittest.TestCase):
    """Complete Tax Liability Assessment."""

    QUERY = (
        "Calculate my tax assessment: Gross salary ₹1,800,000, HRA exempt "
        "₹180,000, 80C deductions ₹150,000, TDS ₹165,000. Am I due for "
        "refund or additional payment?"
    )

    def setUp(self):
        self.response = _query_model(self.QUERY)

    def test_no_error(self):
        self.assertFalse(self.response.startswith("Error:"), self.response)

    def test_contains_tax_keywords(self):
        lower = self.response.lower()
        found = sum(1 for kw in TAX_KEYWORDS if kw in lower)
        self.assertGreaterEqual(found, MIN_KEYWORD_MATCHES)


@skip_no_client
class TestNextYearPlanning(unittest.TestCase):
    """Next Year Planning."""

    QUERY = (
        "Based on current year tax liability of ₹200,000, plan investments "
        "and strategies for next financial year to minimize tax burden."
    )

    def setUp(self):
        self.response = _query_model(self.QUERY)

    def test_no_error(self):
        self.assertFalse(self.response.startswith("Error:"), self.response)

    def test_contains_tax_keywords(self):
        lower = self.response.lower()
        found = sum(1 for kw in TAX_KEYWORDS if kw in lower)
        self.assertGreaterEqual(found, MIN_KEYWORD_MATCHES)


# ---------------------------------------------------------------------------
# 7. ITR & Compliance
# ---------------------------------------------------------------------------
@skip_no_client
class TestITRFilingGuidance(unittest.TestCase):
    """ITR Filing Guidance."""

    QUERY = (
        "I'm a salaried employee with salary income, bank interest ₹15,000, "
        "and capital gains from mutual funds ₹25,000. Which ITR form should "
        "I use?"
    )

    def setUp(self):
        self.response = _query_model(self.QUERY)

    def test_no_error(self):
        self.assertFalse(self.response.startswith("Error:"), self.response)

    def test_contains_tax_keywords(self):
        lower = self.response.lower()
        found = sum(1 for kw in TAX_KEYWORDS if kw in lower)
        self.assertGreaterEqual(found, MIN_KEYWORD_MATCHES)

    def test_mentions_itr(self):
        self.assertIn("itr", self.response.lower())