import os, pickle, numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List

from azure_openai import create_client

load_dotenv()

CHAT_MODEL = os.environ.get("CHAT_MODEL", "phi-3-mini")  # deployment or global model name
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
TOP_K = int(os.environ.get("TOP_K", "4"))

with open("vector_store/embeddings.pkl", "rb") as f:
    KB = pickle.load(f)

client = create_client()

def embed(q: str):
    r = client.embeddings.create(model=EMBED_MODEL, input=q)
    return np.array(r.data[0].embedding, dtype="float32")

def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

def retrieve(query: str, k=TOP_K):
    qv = embed(query)
    scored = []
    for rec in KB:
        scored.append((cosine(qv, rec["embedding"]), rec))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:k]]

def _load_system_prompt():
    """Load the expanded system prompt from markdown; fallback to minimal prompt if unavailable.

    The markdown file contains a very detailed specification. For runtime efficiency we retain
    the full spec (helps steer deterministic behaviour) but append retrieval guard rules.
    """
    path = os.environ.get("SYSTEM_PROMPT_PATH", "docs/system_prompt.md")
    base_fallback = (
        "You are an expert Indian Chartered Accountant–style AI Tax Assistant. "
        "Use ONLY the provided context chunks. If context is insufficient, ask for clarification or say you cannot answer. "
        "Always finish with: 'Disclaimer: Not a substitute for a licensed Chartered Accountant.'"
    )
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Heuristic: extract the main system role paragraph starting at 'You are an expert' line
        # to avoid sending extraneous editorial sections if file format changes.
        lines = content.splitlines()
        extracted = []
        capture = False
        for ln in lines:
            if "You are an expert Indian Chartered Accountant" in ln:
                capture = True
            if capture:
                extracted.append(ln)
            # Stop if we reach a high-level section heading after initial block
            if capture and ln.strip().startswith("CORE OBJECTIVES"):
                break
        if extracted:
            core = "\n".join(extracted).strip()
        else:
            core = base_fallback
        retrieval_rules = (
            "\n\nRETRIEVAL & ANSWER RULES:\n"
            "1. Use ONLY the provided context chunks for factual numeric values unless user supplies direct figures.\n"
            "2. If critical data missing (year, amounts, holding period, age), ask concise follow-up before concluding.\n"
            "3. Cite sources as [Chunk i] for every factual block derived from context.\n"
            "4. If no relevant chunk provides the answer, state inability and request the needed data.\n"
            "5. Output concise markdown; tables for comparisons (e.g., Old vs New regime, capital gains classification).\n"
            "6. End with: 'Disclaimer: Not a substitute for a licensed Chartered Accountant.'"
        )
        return core + retrieval_rules
    except Exception:
        return base_fallback

SYSTEM_PROMPT = _load_system_prompt()

class ChatRequest(BaseModel):
    question: str
    history: List[dict] = []
    context_data: dict = {}  # For additional form/salary data

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    regime_comparison: dict = {}  # Old vs New regime analysis
    optimization_suggestions: List[dict] = []  # Tax saving opportunities
    next_steps: List[str] = []  # Recommended actions

app = FastAPI(title="Hackathon Tax Assistant")

def analyze_tax_scenario(question: str, context_text: str):
    """Analyze the question and context to extract tax optimization opportunities"""
    optimization_suggestions = []
    regime_comparison = {}
    next_steps = []
    
    # Check for common tax scenarios
    question_lower = question.lower()
    
    # Salary/income analysis scenario
    if any(keyword in question_lower for keyword in ['salary', 'income', 'form 16', 'tax liability']):
        optimization_suggestions.extend([
            {"strategy": "Maximize 80C deductions", "potential_saving": "Up to ₹46,500", "priority": "HIGH"},
            {"strategy": "Optimize health insurance", "potential_saving": "Up to ₹23,250", "priority": "HIGH"},
            {"strategy": "Consider NPS additional contribution", "potential_saving": "₹15,500", "priority": "MEDIUM"}
        ])
        next_steps.extend([
            "Review current 80C investments and maximize to ₹1.5L limit",
            "Ensure health insurance for self and parents",
            "Compare old vs new tax regime based on deduction profile"
        ])
    
    # Investment planning scenario
    if any(keyword in question_lower for keyword in ['investment', '80c', 'tax saving', 'deduction']):
        optimization_suggestions.extend([
            {"strategy": "ELSS mutual funds", "benefit": "Growth potential + 3-year lock-in", "priority": "HIGH"},
            {"strategy": "PPF contribution", "benefit": "EEE benefit + 15-year wealth building", "priority": "HIGH"},
            {"strategy": "Health insurance upgrade", "benefit": "Enhanced coverage + tax deduction", "priority": "MEDIUM"}
        ])
        next_steps.extend([
            "Start ELSS SIP for optimal growth and tax benefits",
            "Consider PPF for long-term stable returns",
            "Evaluate health insurance adequacy for family"
        ])
    
    # Form 16 analysis scenario
    if 'form 16' in question_lower:
        next_steps.extend([
            "Verify TDS details against Form 26AS",
            "Check HRA exemption optimization",
            "Ensure all eligible deductions are claimed",
            "Compare tax liability under both regimes"
        ])
    
    return optimization_suggestions, regime_comparison, next_steps

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    hits = retrieve(req.question)
    context_blocks = []
    for i, h in enumerate(hits):
        context_blocks.append(f"[Chunk {i}]\\n{h['text']}")
    context_text = "\n\n".join(context_blocks)
    
    # Enhanced user content with tax-specific prompting
    user_content = f"""Question: {req.question}

Context:
{context_text}

Instructions: 
1. Provide comprehensive analysis using structured tables
2. Always include tax optimization opportunities when applicable
3. Compare old vs new regime when income/tax calculations are involved
4. Suggest specific investment options and amounts
5. Provide actionable next steps
6. Use the provided context for accurate figures and calculations

Answer:"""
    
    messages = [{"role":"system","content":SYSTEM_PROMPT}]
    for h in req.history[-5:]:
        messages.append(h)
    messages.append({"role":"user","content":user_content})
    
    # Generate enhanced analysis
    optimization_suggestions, regime_comparison, next_steps = analyze_tax_scenario(req.question, context_text)
    
    # Get AI response
    answer = None
    try:
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0.1,
            messages=messages,
            max_tokens=1200  # Increased for comprehensive responses
        )
        answer = resp.choices[0].message.content
    except Exception as e:
        try:
            r2 = client.responses.create(
                model=CHAT_MODEL,
                input=messages,
                temperature=0.1,
                max_output_tokens=1200,
            )
            answer = r2.output_text
        except Exception as e2:
            raise e2
    
    return ChatResponse(
        answer=answer, 
        sources=[f"Chunk {i}" for i,_ in enumerate(hits)],
        regime_comparison=regime_comparison,
        optimization_suggestions=optimization_suggestions,
        next_steps=next_steps
    )

@app.get("/healthz")
def health():
    return {"status": "ok", "chunks": len(KB)}