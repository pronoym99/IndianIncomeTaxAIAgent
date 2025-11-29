# IndianIncomeTaxAIAgent
An AI-powered assistant to help salaried professionals in India analyse their income sources and Form 16, suggest effective tax planning strategies, optimise savings and investments, and streamline ITR filing. 

# Hackathon Tax Assistant (Form 16 Focus)

## Quick Start
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Set up environment variables
Copy the example file and edit values:
```
cp .env.example .env   # (On Windows PowerShell: Copy-Item .env.example .env)
```

# Ingest ALL supported files under /data (json, txt, md)
python ingest.py --force

# Run API
uvicorn app:app --reload --port 8000
```
Test:
```powershell
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"question\":\"Explain Form 16 parts\"}"
```

## Modern UI with File Upload
```powershell
streamlit run ui.py
```

**New Features:**
- 💬 **Modern Chat Interface**: Real-time conversation with the AI tax assistant
- 📎 **File Upload Support**: Upload Form 16, salary slips, PDFs, CSVs, images
- 🔄 **Interactive Session**: Maintains conversation context across messages
- 🚀 **Quick Actions**: Pre-built buttons for common tax queries
- 📊 **File Preview**: View uploaded document contents in the sidebar

**Supported File Types:**
- Text files: `.txt`, `.csv`, `.md`
- PDFs: `.pdf` (with text extraction via PyPDF2)
- Images: `.png`, `.jpg`, `.jpeg` (base64 encoded for multimodal models)

## CLI Chat Tool
For command-line usage with file analysis:
```powershell
# Interactive chat with file attachment
python ca_convo.py -f data/samples/form16_simple.txt

# Single question with multiple files  
python ca_convo.py -q "Compare these documents" -f file1.pdf -f file2.txt

# Interactive mode (default)
python ca_convo.py --interactive
```

## New: System Prompt (Expert CA)
A detailed expert Chartered Accountant style system prompt is stored at `docs/system_prompt.md`. Use the entire content as the `system` role message when initializing chat sessions requiring deterministic tax advisory with clarifying question workflow.

## New: Fine-Tuning Training Data
Sample chat fine-tune dataset (JSONL) at `training_data/form16_finetune.jsonl`.
Each line uses the Azure OpenAI compatible chat format:
```
{"messages":[{"role":"system","content":"..."},{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
```
You can expand this file with more scenarios (HRA edge cases, capital gains classification, donation deductions, regime comparison) ensuring: deterministic tone, disclaimer appended, no hallucinated figures.

### Validating JSONL
Use a quick Python check:
```powershell
python - <<'PY'
import json, pathlib
for i,l in enumerate(open('training_data/form16_finetune.jsonl','r',encoding='utf-8')):
    try: json.loads(l)
    except Exception as e: print('Line', i+1, 'Invalid', e)
PY
```

### Fine-Tuning (Azure OpenAI Foundry Outline)
1. Upload `training_data/form16_finetune.jsonl` in the Azure AI Studio / Foundry fine-tune UI (Chat Completion model that supports fine-tuning, e.g., a small instruct model if available).
2. Select base model (e.g. `gpt-4o-mini` compatible if fine-tune offering exists; else use available fine-tunable smaller model).
3. Configure epochs (start low: 1–3), temperature 0 for eval.
4. Provide a validation file (optional) with withheld scenarios (copy file & remove last N lines for training subset).
5. Start job and monitor metrics (loss, token usage). Avoid overfitting—stop if validation loss diverges.
6. Store resulting deployment name in `CHAT_MODEL` env var for inference.

> Note: Not all Azure models permit fine-tuning; if unsupported, keep using the system prompt + RAG instead.

## Sample Synthetic Form 16 Files
Two synthetic examples for parsing / validation & prompt generation:
- `data/samples/form16_simple.txt` – basic single-employer scenario
- `data/samples/form16_complex.txt` – multi-employer, detailed allowances, HRA, deductions

## Validation Script
`scripts/validate_form16.py` performs:
1. Heuristic parse of text file (key: value + section markers)
2. Aggregation of salary components & deductions
3. Structural checks (missing mandatory identifiers, gross salary consistency)
4. Optional LLM validation prompt emission (`--emit-llm-prompt`)

Run example:
```powershell
python scripts/validate_form16.py --path data/samples/form16_simple.txt --emit-llm-prompt
```
This prints a JSON summary and a suggested secondary prompt for the model to cross-check internal consistency.

## Suggested LLM Validation Chain
1. Parse file with script (structured JSON output)
2. Feed JSON + original extracted text to model with an instruction: "Validate inconsistencies & list issues[] / warnings[] / confirmations[]"
3. Reject documents with critical issues (PAN/TAN missing, salary mismatch, negative tax).

## Ingestion Details
`ingest.py` scans `data/` recursively for: `.json`, `.txt`, `.md`.
Flattening & chunking rules unchanged (≈1200 char window / 120 char overlap).

### CLI Flags
```
python ingest.py [--data-dir DATA] [--out OUTFILE] [--max-chars N] [--overlap N] [--force]
```
(See earlier section for descriptions.)

### Environment Variables
Key vars: `DATA_DIR`, `STORE_DIR`, `CHUNK_MAX_CHARS`, `CHUNK_OVERLAP`, `EMBED_MODEL`, `CHAT_MODEL`, `TOP_K`.

### Stored Record Structure
```
{
  id: <sha1>,
  text: <chunk text>,
  embedding: np.float32 vector,
  source: relative source file path,
  chunk_index: index within that file
}
```

## Azure OpenAI / Global Endpoint Configuration
(Existing section retained; supports both Azure resource endpoint & global models.)

### Chat API Fallback Strategy
`app.py` attempts `chat.completions` then falls back to `responses` API.

## Extending the Dataset
Ideas to add lines to `form16_finetune.jsonl`:
- Edge HRA: zero rent, partial-year rent, metro vs non-metro switch
- 80C saturation vs under-utilization optimization suggestions
- Capital gains reinvestment scenarios (Sections 54 / 54F / 54EC)
- Donation categorization under 80G with limit math
- Regime switch breakeven comparison prompt & answer pattern

Maintain deterministic wording, include disclaimer each answer line, and avoid speculative values.

## Disclaimer
The assistant responses append: "Disclaimer: Not a substitute for a licensed Chartered Accountant." – adjust or harmonize with system prompt if you change phrasing.


