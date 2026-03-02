# Azure OpenAI Fine-Tuning Guide (Form 16 Tax Assistant)

Reference Microsoft doc: https://learn.microsoft.com/azure/ai-foundry/openai/how-to/fine-tuning (see section: *Prepare your training and validation data*).

This guide adapts those requirements specifically for the Form 16 / Indian Tax Assistant use case in this repository.

---
## 1. Objectives
Fine-tune a base chat-capable model (if supported) to:
- Maintain deterministic professional CA tone
- Ask clarifying questions before calculations
- Output standard tables / disclaimers
- Provide accurate regime comparison scaffolding

If fine-tuning is unavailable for your chosen base model, continue using: `docs/system_prompt.md` + RAG retrieval.

---
## 2. Data Format Requirements
Azure AI Foundry accepts JSONL where each line is an object containing a `messages` array with role/content pairs (chat schema):
```json
{"messages":[{"role":"system","content":"..."},{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
```
Rules:
- Roles allowed: `system`, `user`, `assistant`.
- At least one `user` and one `assistant` message per sample.
- Keep answers concise but complete; avoid extraneous punctuation or stylistic noise.
- Ensure consistent disclaimer text *exactly* for training stability.
- No personally identifiable real data (use synthetic salary values).

### Token Considerations
- Keep each conversation short (1–3 turns). Multi-turn can be added but increases token size + potential overfitting.
- Aggregate 50–300 high-quality lines to start; expand iteratively.

---
## 3. Training vs Validation Split
- Training: majority (e.g. 80%). File: `training_data/form16_finetune.jsonl`.
- Validation: representative hold-out (20%). File: `training_data/form16_finetune_validation.jsonl`.
- Validation examples should cover: refusal for insufficient data, optimization suggestions, conceptual explanation.

Do NOT duplicate exact user prompts across both sets.

---
## 4. Content Design Checklist
Each assistant answer should:
- Start with a concise summary when explanation-based.
- Include stepwise numeric breakdown for calculations (HRA, deductions, capital gains). 
- End with unified disclaimer:
  `Disclaimer: This guidance is informational, not a substitute for a qualified Chartered Accountant.`
- Avoid making assumptions—explicitly request missing fields.

Include negative / boundary cases:
- Missing FY => ask for it
- Attempt to claim both HRA & 80GG => reject
- Request for assumption-filled estimate => respond with pending info list

Include optimization prompts:
- Suggest maximizing 80C remainder
- Show HRA computation logic
- Highlight when new regime disallows certain deductions

---
## 5. Quality Control Before Upload
Run JSONL validation:
```powershell
python - <<'PY'
import json, pathlib
for path in ["training_data/form16_finetune.jsonl", "training_data/form16_finetune_validation.jsonl"]:
  print('Checking', path)
  for i,l in enumerate(open(path,'r',encoding='utf-8')):
    try: json.loads(l)
    except Exception as e: print('  Line', i+1, 'invalid:', e)
PY
```
Check for stylistic consistency (optional regex):
```powershell
Select-String -Path training_data/form16_finetune*.jsonl -Pattern 'Disclaimer:' | Measure-Object
```
Expect equal counts to number of conversation lines.

---
## 6. Upload & Job Creation (Portal Workflow)
1. Open Azure AI Foundry / AI Studio > **Fine-tuning**.
2. Select compatible base model (e.g. phi-3-mini or supported GPT variant) – verify fine-tuning availability.
3. Upload `form16_finetune.jsonl` as Training file.
4. Upload `form16_finetune_validation.jsonl` as Validation file (optional but recommended).
5. Configure Hyperparameters:
   - Epochs: start 1–2 (increase if underfitting)
   - Batch size: auto
   - Learning rate multiplier: default (adjust only after first evaluation)
   - Seed: specify for reproducibility (e.g. 42)
6. Launch job and monitor metrics (training loss vs validation loss). Avoid divergence.
7. On completion, deploy resulting model version -> note deployment name -> set `CHAT_MODEL` env var.

---
## 7. CLI / REST (If Needed)
If programmatic support added in future, outline would be:
- Upload files to fine-tune asset container
- Submit fine-tune job referencing file IDs and base model
- Poll job status
(Currently, portal is the simplest & documented path; adapt when SDK endpoints become generally available.)

---
## 8. Post-Deployment Acceptance Tests
Create a lightweight script (pseudo):
```python
TESTS = [
  ("Explain Form 16 parts", "Part A"),
  ("Can I claim both HRA and 80GG?", "mutually exclusive"),
  ("I have basic 9L, HRA 3L, rent 2.4L non-metro. HRA?", "Taxable HRA")
]
```
Assert responses contain required keywords & disclaimer.

Compare base vs fine-tuned latency & token usage to ensure performance not degraded materially.

---
## 9. RAG + Fine-Tune Integration
Even after fine-tuning, keep retrieval for dynamic law updates:
- System prompt trimmed (model already aligned)
- Prepend top-k chunks to user message
- Guardrails: If chunk coverage insufficient → instruct user rather than hallucinate

---
## 10. Expansion Roadmap
Future dataset additions:
- Capital gains with reinvestment exemptions (54F partial usage)
- Multi-employer Form 16 reconciliation
- Edge donation categories (80G limits vs without limits)
- NPS employer contributions (80CCD(2)) nuance under regimes

Maintain versioning: store new dataset variants as `form16_finetune_v2.jsonl` etc. with a CHANGELOG.

---
## 11. Troubleshooting
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Validation loss >> Training loss | Overfitting | Reduce epochs or dataset redundancy |
| Model ignores disclaimer | Inconsistent training examples | Ensure 100% inclusion |
| Hallucinated figures | Missing clarifying Q examples | Add more refusal/clarification samples |
| HRA math errors | Insufficient arithmetic examples | Add diverse HRA scenarios |

---
## 12. Compliance & Safety Notes
- Use only synthetic or publicly known allowance limits.
- Do not include PII or real PAN/TANs (samples here are fictitious formats).
- Re-run ingestion after any dataset change to refresh context store if you add docs—fine-tune does not auto-update retrieval base.

---
## 13. Quick Checklist Before Launch
- [ ] JSONL validates
- [ ] All assistant replies end with disclaimer
- [ ] At least 1 refusal / clarifying example present
- [ ] At least 2 HRA calculations
- [ ] Old vs New regime comparison example present
- [ ] Optimization suggestion example present
- [ ] No duplicate user prompts across train/validation

---
**Done.** Refer back to Microsoft docs for platform-level nuances.
