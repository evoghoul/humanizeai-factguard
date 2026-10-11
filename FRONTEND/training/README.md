# HumanizeAI — Model Training & External Fine-Tuning Strategy

This directory contains the tools, schemas, and execution recipes for evaluating, fine-tuning, and deploying dedicated open-weight writing refinement models.

---

## 1. Candidate Models & Selection Criteria

| Candidate Model | Parameter Size | Minimum VRAM (4-bit QLoRA) | Strengths | Ideal Deployment |
|---|---|---|---|---|
| **Llama 3.3 70B Instruct** | 70B | ~48 GB (A100 / H100) | State-of-the-art prose nuance, high reasoning, complex syntax preservation. | Enterprise vLLM or RunPod serverless |
| **Qwen 2.5 32B / 72B Instruct** | 32B / 72B | ~24 GB / ~48 GB | Exceptional multi-lingual capability, technical terminology handling, precise adherence to formatting. | Cloud vLLM instance |
| **Llama 3.1 8B Instruct** | 8B | ~6 GB (Tesla T4 / RTX 3060) | Extremely fast inference, low cost, trainable on Google Colab free tier. | Local Ollama or low-cost cloud GPU |
| **Mistral Small 24B Instruct** | 24B | ~16 GB (RTX 4090 / A10G) | High token throughput, strong stylistic flexibility. | Mid-tier GPU instance |

---

## 2. Dataset Preparation & Quality Filters

### Dataset Requirements:
- **Sample Count:** 1,500 – 5,000 verified paired samples (Source Text $\rightarrow$ Refined Humanized Text).
- **Format:** OpenAI chat JSONL format (`{"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}`).
- **Integrity Validation:** Run `python training/prepare_dataset.py [path/to/dataset.jsonl]`.

### Automated Quality Rules:
1. **Zero Dropped Numbers/Dates:** Every percentage, currency value, metric, and date from the input must exist in the output.
2. **Polarity Consistency:** Negation words (`not`, `never`, `cannot`, `neither...nor`) must never be dropped or flipped.
3. **Length Preservation Ratio:** Output word count must be between 80% and 120% of input word count (except for explicitly requested Concise or Expanded modes).
4. **Attribution & Citations:** Bracketed `[1]` and academic references `(Author et al., Year)` must remain intact.

---

## 3. Split Strategy
- **Train Set (80%):** ~1,600 examples.
- **Validation Set (10%):** ~200 examples (used for early stopping, loss tracking).
- **Test / Benchmark Set (10%):** ~200 examples (never seen during training, evaluated with automated deterministic and semantic verification scripts).

---

## 4. Fine-Tuning Execution (Unsloth QLoRA)

Run on Google Colab or cloud GPU:
```bash
pip install unsloth trl datasets transformers
python training/train_lora_unsloth.py
```

---

## 5. Deployment Options & Connecting to Humanize AI

Once the model is fine-tuned and merged:

### Option A: Serve with vLLM (Recommended for Production)
```bash
vllm serve ./humanize-ai-model --port 8000 --max-model-len 4096
```

### Option B: Serve with Ollama (Local)
Create a `Modelfile`:
```dockerfile
FROM ./humanize-ai-model
PARAMETER temperature 0.2
```
And run:
```bash
ollama create humanize-ai -f Modelfile
ollama run humanize-ai
```

### Option C: Connect to Humanize AI
In your `.env.local` file:
```env
AI_PROVIDER=openai_compatible
OPENAI_BASE_URL=http://localhost:8000/v1
OPENAI_MODEL=humanize-ai-model
OPENAI_API_KEY=dummy-token
```
The Humanize AI backend automatically uses `OpenAiCompatibleProvider` to send requests to your custom trained model.

---

## 6. Evaluation Benchmark & Rollback Strategy

Before switching production traffic:
1. Run the test evaluation benchmark on the 200 hold-out test cases.
2. Calculate:
   - **Entity Preservation Rate:** $\ge 99.5\%$
   - **Negation Integrity:** $100\%$
   - **Semantic Pass Rate:** $\ge 95\%$
3. **Rollback Strategy:** If the fine-tuned model drops entities or underperforms, simply remove `AI_PROVIDER` from `.env.local`. Humanize AI will immediately fall back to Google Gemini with zero downtime.
