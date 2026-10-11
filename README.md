# 🛡️ HumanizeAI + FactGuard

> **Google Student Club — Welcome Hackathon 2026**  
> **Problem Statement 02**: *AI Humanization & Natural Language Refinement (Human-Like Communication Layer)*  
> **Team**: THE COMPILERs | **Repository**: [evoghoul/humanizeai-factguard](https://github.com/evoghoul/humanizeai-factguard)

---

## 🌐 Live System Deployments

| Component | Status | Technology | Live URL |
| :--- | :--- | :--- | :--- |
| **Frontend Workspace** | 🟢 Live | React 19 + Vite + TypeScript (Nocturne Glassmorphism) | [Deployed on Vercel](https://humanizeai-factguard.vercel.app) |
| **FactGuard Backend** | 🟢 Live | FastAPI + Heuristic Fact Audit Engine | [https://humanizeai-backend-tfzm.onrender.com](https://humanizeai-backend-tfzm.onrender.com) |
| **API Interactive Docs** | 🟢 Live | Swagger / OpenAPI 3.0 | [Interactive Swagger Docs](https://humanizeai-backend-tfzm.onrender.com/docs) |
| **Dedicated AI Inference** | 🟢 Live | Qwen2.5-14B-Instruct (4-bit NF4) + Custom LoRA Adapter | Cloudflare Secure Tunnel |

---

## 💡 Executive Summary

AI models naturally generate repetitive, robotic phrasing with uniform sentence cadence. Existing humanizer tools degrade factual accuracy by indiscriminately swapping synonyms, dropping dates, or inverting sensitive clauses.

**HumanizeAI + FactGuard** solves this dual problem:
1. **Context-Aware Humanization Layer**: Powered by a custom fine-tuned **14-Billion parameter large language model (`Qwen/Qwen2.5-14B-Instruct`)**, producing fluid, human-cadence prose across recruiter feedback, interview questions, and executive reports.
2. **FactGuard Mathematical Audit**: A deterministic, rule-based verification ledger ensuring **zero hallucinations**—strictly verifying that critical figures ($12.4M, 14.8%), calendar dates (October 14, 2025), proper names (Dr. Aris Thorne), and negation conditions ("won't commence until...") survive intact.
3. **Safety Fallback Principle**: *"Knowing when not to change something."* If any rewritten clause violates factual integrity, FactGuard flags the exact discrepancy, attempts a feedback retry, and falls back to preserving ground-truth content.

---

## 🔄 The 6-Stage Pipeline

```
  [ Input Text ]
        │
        ▼
┌───────────────────────────────┐
│ 1. Intent & Fact Ledger       │  Deterministic extraction of numbers, dates,
│    Extraction                 │  currencies, entities, and negation polarity
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ 2. Robotic Language Analysis  │  Detection of formulaic AI tokens, uniform sentence
│                               │  lengths, and cliché academic connectors
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ 3. Style & Tone Modulation    │  Application of selected persona (Professional,
│                               │  Conversational, Polished) & burstiness dynamics
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ 4. 14B Contextual Rewrite     │  Fine-tuned Qwen2.5-14B-Instruct (LoRA rank=16)
│                               │  generates natural human phrasing
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ 5. FactGuard Integrity Check  │  Heuristic cross-referencing between source & target
│                               │  ledger; checks for omission or semantic drift
└───────────────┬───────────────┘
                │
                ▼
  [ Verified Human Output ]  + Interactive Verification Ledger & Diff
```

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────┐
│  Vercel Cloud (Frontend Layer)                         │
│  • React 19 + Vite + TypeScript                        │
│  • Nocturne Glassmorphism Writing Workspace            │
│  • Live Diff Highlighting & Visual Fact Badges         │
└───────────────────────────┬────────────────────────────┘
                            │ HTTPS Proxy
                            ▼
┌────────────────────────────────────────────────────────┐
│  Render Cloud (API & Guardrail Layer)                  │
│  • FastAPI High-Performance Asynchronous Backend       │
│  • FactGuard Deterministic Audit Engine                │
│  • Robotic Language Detection Heuristics               │
└───────────────────────────┬────────────────────────────┘
                            │ Secure Tunnel
                            ▼
┌────────────────────────────────────────────────────────┐
│  Lightning AI Cloud (Dedicated GPU Inference)          │
│  • L4 Tensor Core GPU (24 GB VRAM)                     │
│  • Qwen2.5-14B-Instruct in 4-bit NF4 Quantization      │
│  • Custom Fine-Tuned `humanizeai_14b_lora` Adapter     │
└────────────────────────────────────────────────────────┘
```

---

## 🔬 Model & Training Details

* **Base Model**: `Qwen/Qwen2.5-14B-Instruct` (14.8 Billion Parameters)
* **Quantization**: 4-bit NormalFloat (NF4) with double quantization and bfloat16 computation
* **Fine-Tuning Method**: Parameter-Efficient Fine-Tuning (PEFT / QLoRA)
  * Trainable Parameters: `68,812,800` (0.4637% of base)
  * Target Modules: `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`
  * LoRA Rank $r=16$, Alpha $\alpha=32$, Dropout $0.05$
  * Optimizer: `paged_adamw_8bit` with gradient checkpointing
* **Training Objective**: Instruction-tuned specifically to remove AI stylistic signatures while strictly obeying numerical and factual invariances.

---

## 🧪 Verification & Test Suite

The project includes automated test coverage across both frontend and backend:

* **Backend Test Suite (PyTest)**:
  * 15/15 tests passing across API contracts, FactGuard extraction, and negation preservation.
* **Frontend Test Suite (Vitest)**:
  * 32/32 unit & workflow tests passing across data normalization, error handling, and diff rendering.

---

## 💻 Local Development Setup

### 1. Backend (FastAPI)
```bash
cd backend
python -m venv venv
venv\Scripts\activate       # On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (React + Vite)
```bash
cd FRONTEND
npm install
npm run dev
```
Open [http://localhost:8443](http://localhost:8443) in your browser.

---

## 👥 Hackathon Team

* **Team**: THE COMPILERs
* **Track**: Problem Statement 02 — AI Humanization & Natural Language Refinement
* **Hackathon**: Google Student Club — Welcome Hackathon 2026
