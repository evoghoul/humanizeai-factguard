"""
HumanizeAI-FactGuard: Blended Training Dataset Builder
Combines:
1. Kaggle DAIGT / AI-vs-Human datasets (for high burstiness & natural tone)
2. Hugging Face PAWS / Paraphrase datasets (for deep syntactic restructuring & 0% plagiarism)
3. FactGuard Gold Seed Pairs (for 100% entity, metric, timeline, and intent lock)

Outputs: expanded_training_data_14b.jsonl ready for train_14b.py
"""

import os
import sys
import re
import json
import glob
from pathlib import Path
from typing import Any

# Optional libraries with type: ignore for clean local IDE inspection
try:
    import pandas as pd  # type: ignore
except ImportError:
    pd: Any = None  # type: ignore

try:
    from datasets import load_dataset  # type: ignore
except ImportError:
    load_dataset: Any = None  # type: ignore

# Paths (works whether run from repo root or backend/)
SCRIPT_DIR = Path(__file__).resolve().parent
CWD = Path.cwd()

# Find data dir and jsonl target
candidate_data_dirs = [SCRIPT_DIR / "data", CWD / "data", SCRIPT_DIR, CWD]
DATA_DIR = next((d for d in candidate_data_dirs if d.exists() and any(d.glob("*.csv"))), SCRIPT_DIR / "data")

OUTPUT_FILE = SCRIPT_DIR / "expanded_training_data_14b.jsonl"
if not OUTPUT_FILE.parent.exists():
    OUTPUT_FILE = CWD / "expanded_training_data_14b.jsonl"

SYSTEM_PROMPT = (
    "You are HumanizeAI, an expert human editor. Rewrite the input text into natural, fluent, human prose "
    "that passes all AI detectors (high perplexity and high burstiness), strictly obeying Wikipedia's "
    "'Signs of AI-generated text' negative constraints (no negative parallelisms, no rule of threes, no false ranges, "
    "zero AI cliché vocabulary, no compulsive summaries). You MUST strictly enforce 100% Named Entity Retention, "
    "100% Metric and Timeline Preservation, and zero hallucinations."
)

BANNED_CLICHES = [
    "delve", "delving", "tapestry", "multifaceted", "dynamic synergies",
    "testament", "paradigm shift", "crucial to note", "seamlessly",
    "beacon", "bustling", "vibrant", "revolutionize", "pivotal"
]

def extract_numbers_and_symbols(text: str) -> set:
    """Extracts all numbers, percentages, currencies, and year numbers."""
    return set(re.findall(r'[\$£€]?\b\d+(?:[\.,]\d+)?%?\b', text))

def get_content_words(text: str) -> set:
    """Extracts meaningful content words to verify topic alignment."""
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    stopwords = {"this", "that", "with", "from", "have", "were", "they", "their", "which", "about", "would", "there", "could", "other", "these", "should", "because"}
    return {w for w in words if w not in stopwords}

def is_factguard_compliant(source: str, target: str, check_semantic_overlap: bool = False) -> bool:
    """Verifies that the target rewrite passes all FactGuard invariant rules."""
    src = source.strip()
    tgt = target.strip()
    
    if len(src) < 20 or len(tgt) < 20:
        return False

    tgt_lower = tgt.lower()
    # 1. No banned AI clichés in target
    if any(cliche in tgt_lower for cliche in BANNED_CLICHES):
        return False

    # 2. Hard Entity & Number Lock: All numbers in source must exist in target
    src_nums = extract_numbers_and_symbols(src)
    tgt_nums = extract_numbers_and_symbols(tgt)
    if not src_nums.issubset(tgt_nums):
        return False

    # 3. Intent Lock: If source is an inquiry, target must stay an inquiry
    if src.endswith('?') and not tgt.endswith('?'):
        return False

    # 4. Length Preservation: Avoid extreme summarization or bloat (70% - 135%)
    src_len = len(src.split())
    tgt_len = len(tgt.split())
    if tgt_len < max(5, int(src_len * 0.70)) or tgt_len > int(src_len * 1.35):
        return False

    # 5. Semantic alignment check for external unpaired corpora
    if check_semantic_overlap:
        src_words = get_content_words(src)
        tgt_words = get_content_words(tgt)
        if src_words and tgt_words:
            overlap = len(src_words.intersection(tgt_words)) / max(len(src_words), 1)
            if overlap < 0.25:
                return False

    return True

def format_sample(source: str, target: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": source.strip()},
            {"role": "assistant", "content": target.strip()}
        ]
    }

def load_kaggle_samples(max_samples: int = 5000):
    """Loads Kaggle CSV files from data directories."""
    samples = []
    csv_candidates = list(glob.glob(str(DATA_DIR / "*.csv"))) + list(glob.glob(str(SCRIPT_DIR / "data" / "*.csv"))) + list(glob.glob(str(CWD / "data" / "*.csv")))
    # Deduplicate paths
    csv_candidates = list(dict.fromkeys(csv_candidates))

    if not csv_candidates:
        print(f"[*] No CSV files found yet in {DATA_DIR} or ./data.")
        return samples

    global pd
    if pd is None:
        try:
            import pandas as pd  # type: ignore
        except ImportError:
            print("[!] pandas is not installed. Run: pip install pandas")
            return samples

    for csv_path in csv_candidates:
        print(f"[*] Reading Kaggle CSV: {csv_path}")
        try:
            df = pd.read_csv(csv_path)
            print(f"    Total rows in file: {len(df)}")
            print(f"    Columns found: {list(df.columns)}")
            
            if "text" in df.columns and "label" in df.columns:
                # Group by prompt if available to get topic-matched pairs
                col = "prompt_name" if "prompt_name" in df.columns else ("prompt_id" if "prompt_id" in df.columns else None)
                if col:
                    print(f"    Grouping by topic '{col}' for precise topic matching...")
                    for pid, group in df.groupby(col):
                        grp_h = group[group["label"] == 0]["text"].dropna().tolist()
                        grp_a = group[group["label"] == 1]["text"].dropna().tolist()
                        for a_text, h_text in zip(grp_a, grp_h):
                            # Compare first paragraphs to ensure manageable training length
                            a_para = a_text.split("\n\n")[0].strip()
                            h_para = h_text.split("\n\n")[0].strip()
                            if is_factguard_compliant(a_para, h_para, check_semantic_overlap=True):
                                samples.append((a_para, h_para))
                                if len(samples) >= max_samples:
                                    break
                        if len(samples) >= max_samples:
                            break
                else:
                    humans = df[df["label"] == 0]["text"].dropna().tolist()
                    ais = df[df["label"] == 1]["text"].dropna().tolist()
                    for a_text, h_text in zip(ais, humans):
                        a_para = a_text.split("\n\n")[0].strip()
                        h_para = h_text.split("\n\n")[0].strip()
                        if is_factguard_compliant(a_para, h_para, check_semantic_overlap=True):
                            samples.append((a_para, h_para))
                            if len(samples) >= max_samples:
                                break
        except Exception as e:
            print(f"[!] Warning reading {csv_path}: {e}")

    print(f"[+] Successfully extracted {len(samples)} FactGuard-compliant Kaggle samples.")
    return samples

def load_huggingface_paws(max_samples: int = 3000):
    """Loads Google PAWS dataset from Hugging Face for deep syntactic rewrites."""
    samples = []
    print("[*] Fetching Hugging Face PAWS dataset (google-research-datasets/paws)...")
    global load_dataset
    if load_dataset is None:
        try:
            from datasets import load_dataset  # type: ignore
        except ImportError:
            print("[*] Note: 'datasets' package not installed locally. Skipping PAWS download.")
            return samples

    try:
        ds = load_dataset("google-research-datasets/paws", "labeled_final", split="train")
        for item in ds:
            if item.get("label") == 1:
                s1 = str(item.get("sentence1", "")).strip()
                s2 = str(item.get("sentence2", "")).strip()
                if is_factguard_compliant(s1, s2):
                    samples.append((s1, s2))
                    if len(samples) >= max_samples:
                        break
        print(f"[+] Loaded {len(samples)} valid PAWS paraphrase pairs.")
    except Exception as e:
        print(f"[*] Note: Could not load PAWS from Hugging Face ({e}). Continuing with available data.")
    return samples

def load_existing_samples():
    """Loads existing validated samples from expanded_training_data_14b.jsonl."""
    samples = []
    search_paths = [OUTPUT_FILE, SCRIPT_DIR / "expanded_training_data_14b.jsonl", CWD / "expanded_training_data_14b.jsonl"]
    target_path = next((p for p in search_paths if p.exists()), None)
    
    if not target_path:
        return samples
        
    print(f"[*] Reading existing FactGuard samples from {target_path}...")
    with open(target_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    obj = json.loads(line)
                    samples.append(obj)
                except Exception:
                    pass
    print(f"[+] Loaded {len(samples)} existing FactGuard samples.")
    return samples

def main():
    print("=" * 65)
    print(" HumanizeAI-FactGuard: Blended Training Builder")
    print(" Kaggle DAIGT + Hugging Face PAWS + FactGuard Seed Anchors")
    print("=" * 65)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Existing verified dataset
    all_formatted = load_existing_samples()
    
    # 2. Kaggle Samples
    kaggle_pairs = load_kaggle_samples(max_samples=4000)
    for src, tgt in kaggle_pairs:
        all_formatted.append(format_sample(src, tgt))
        
    # 3. Hugging Face PAWS
    hf_pairs = load_huggingface_paws(max_samples=2500)
    for src, tgt in hf_pairs:
        all_formatted.append(format_sample(src, tgt))

    # 4. Save to final expanded_training_data_14b.jsonl
    print(f"\n[*] Total compiled dataset size: {len(all_formatted)} training samples.")
    print(f"[*] Writing to {OUTPUT_FILE}...")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for entry in all_formatted:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"\n[SUCCESS] Saved {len(all_formatted)} samples to: {OUTPUT_FILE}")
    print("Ready to fine-tune! Run: python train_14b.py")
    print("=" * 65)

if __name__ == "__main__":
    main()
