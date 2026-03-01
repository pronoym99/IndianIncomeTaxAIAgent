"""Form 16 text validator & LLM prompt generator.

Purpose:
 1. Parse synthetic / extracted Form 16 plain text files (simple heuristic parsing).
 2. Validate required structural fields.
 3. Produce a JSON summary.
 4. Optionally craft an LLM validation prompt asking the model to cross-check consistency.

Usage:
  python scripts/validate_form16.py --path data/samples/form16_simple.txt --emit-llm-prompt

Outputs:
  - Prints JSON summary to stdout.
  - If --emit-llm-prompt supplied, prints a delimiter + suggested prompt.

This is intentionally lightweight; real-world PDFs should be OCR'd & normalized upstream.
"""
from __future__ import annotations
import re, json, argparse, sys
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict

RE_FIELD = re.compile(r"^(?P<k>[A-Za-z0-9 /()%-]+):\s*(?P<v>.+)$")

MANDATORY_TOP = [
    "Financial Year",
    "Employer Name",
    "Employer TAN",
    "Employer PAN",
    "Employee Name",
    "Employee PAN",
]

@dataclass
class SalaryComponent:
    name: str
    amount: float
    exempt: bool = False
    notes: Optional[str] = None

@dataclass
class Form16Summary:
    financial_year: Optional[str] = None
    employer_name: Optional[str] = None
    employer_tan: Optional[str] = None
    employer_pan: Optional[str] = None
    employee_name: Optional[str] = None
    employee_pan: Optional[str] = None
    period_of_employment: Optional[str] = None
    previous_employer: Optional[str] = None
    consolidated_tds: Optional[float] = None
    gross_salary_total: Optional[float] = None
    salary_components: List[SalaryComponent] = field(default_factory=list)
    exemptions: Dict[str, float] = field(default_factory=dict)
    chapter_via_deductions: Dict[str, float] = field(default_factory=dict)
    standard_deduction: Optional[float] = None
    hra_exempt: Optional[float] = None
    taxable_income: Optional[float] = None
    tds_deducted: Optional[float] = None
    refund_or_payable: Optional[float] = None
    issues: List[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

SECTION_HEADERS = {
    "part a": "part_a",
    "part b": "part_b",
    "gross salary components": "gross_salary",
    "exempt allowances": "exempt_allowances",
    "chapter vi-a deductions": "chapter_via",
    "taxable income computation": "taxable_computation",
    "taxable income derivation": "taxable_computation",
}

MONEY_RE = re.compile(r"(?<![A-Za-z0-9])([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)(?![A-Za-z0-9])")

FLOAT_CLEAN = lambda s: float(s.replace(",", ""))


def parse_money(s: str) -> Optional[float]:
    s = s.strip()
    try:
        if s.lower() in {"na", "n/a", "nil"}:
            return 0.0
        return FLOAT_CLEAN(s)
    except Exception:
        m = MONEY_RE.search(s)
        if m:
            try:
                return FLOAT_CLEAN(m.group(1))
            except Exception:
                return None
        return None


def parse_file(text: str) -> Form16Summary:
    lines = [l.rstrip() for l in text.splitlines() if l.strip()]
    summary = Form16Summary()
    current_section = None
    in_salary_block = False

    for raw in lines:
        low = raw.lower()
        # Detect section header
        if low.strip() in SECTION_HEADERS:
            current_section = SECTION_HEADERS[low.strip()]
            if current_section == "gross_salary":
                in_salary_block = True
            else:
                in_salary_block = False
            continue

        # Salary components heuristics
        if in_salary_block:
            if ":" in raw:
                parts = raw.split(":", 1)
                name = parts[0].strip()
                amt = parse_money(parts[1])
                if amt is not None:
                    summary.salary_components.append(SalaryComponent(name=name, amount=amt))
                continue

        # Generic key: value parse
        m = RE_FIELD.match(raw)
        if m:
            k = m.group("k").strip()
            v = m.group("v").strip()
            kl = k.lower()
            if kl == "financial year": summary.financial_year = v
            elif kl == "employer name": summary.employer_name = v
            elif kl == "employer tan": summary.employer_tan = v
            elif kl == "employer pan": summary.employer_pan = v
            elif kl == "employee name": summary.employee_name = v
            elif kl == "employee pan": summary.employee_pan = v
            elif kl.startswith("period of employment"): summary.period_of_employment = v
            elif kl.startswith("previous employer"): summary.previous_employer = v
            elif kl.startswith("gross salary total"): summary.gross_salary_total = parse_money(v)
            elif kl.startswith("standard deduction"): summary.standard_deduction = parse_money(v)
            elif kl.startswith("hra exempt"): summary.hra_exempt = parse_money(v)
            elif kl.startswith("total chapter vi-a") or kl.startswith("total chapter vi-a (allowed)"):
                summary.chapter_via_deductions["TOTAL"] = parse_money(v)
            elif kl.startswith("tds deducted") or kl.startswith("total tds (current employer)"):
                val = parse_money(v)
                if summary.tds_deducted is None:
                    summary.tds_deducted = val
                else:
                    if val: summary.tds_deducted += val
            elif kl.startswith("consolidated tds"):
                summary.consolidated_tds = parse_money(v)
            elif kl.startswith("taxable income") and "approx" not in kl:
                maybe = parse_money(v)
                if maybe: summary.taxable_income = maybe
            elif kl.startswith("refund due") or kl.startswith("estimated additional tax payable"):
                summary.refund_or_payable = parse_money(v)
            continue

        # Exempt allowances & deductions simple capture
        if current_section == "exempt_allowances" and ":" in raw:
            name, val = raw.split(":", 1)
            pv = parse_money(val)
            if pv is not None:
                summary.exemptions[name.strip()] = pv
            continue
        if current_section == "chapter_via" and ":" in raw:
            name, val = raw.split(":", 1)
            pv = parse_money(val)
            if pv is not None:
                summary.chapter_via_deductions[name.strip()] = pv
            continue

    # Post-processing checks
    for field_name in MANDATORY_TOP:
        if getattr(summary, field_name.lower().replace(" ", "_"), None) is None:
            summary.issues.append(f"Missing top-level field: {field_name}")

    if summary.gross_salary_total is None and summary.salary_components:
        comp_sum = sum(c.amount for c in summary.salary_components)
        summary.gross_salary_total = comp_sum
    if summary.gross_salary_total and summary.salary_components:
        comp_sum = sum(c.amount for c in summary.salary_components)
        if abs(comp_sum - summary.gross_salary_total) > 1:
            summary.issues.append(f"Gross salary total mismatch: components={comp_sum} vs stated={summary.gross_salary_total}")

    return summary


def build_llm_validation_prompt(summary: Form16Summary) -> str:
    return (
        "You are to validate a parsed Form 16 summary. Check for: "
        "(1) Mandatory IDs, (2) HRA vs salary consistency, (3) Chapter VI-A totals, "
        "(4) Gross salary reconstruction vs components, (5) Any impossible values. "
        "Respond in JSON with keys: issues[], warnings[], confirmations[].\n\nParsed Summary:\n" + summary.to_json()
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True, help="Path to Form 16 text file")
    ap.add_argument("--emit-llm-prompt", action="store_true", help="Also output an LLM validation prompt")
    args = ap.parse_args()

    try:
        with open(args.path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"File not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    summary = parse_file(text)
    print(summary.to_json())

    if args.emit_llm_prompt:
        print("\n==== LLM_VALIDATION_PROMPT ====")
        print(build_llm_validation_prompt(summary))

if __name__ == "__main__":
    main()
