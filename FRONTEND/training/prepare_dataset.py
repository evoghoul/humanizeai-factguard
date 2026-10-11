#!/usr/bin/env python3
"""
HumanizeAI Dataset Preparation and Validation Script
Validates that fine-tuning training pairs do NOT drop facts, numbers, dates, or invert negations.
"""

import json
import re
import sys
from pathlib import Path

NUMBER_PATTERN = re.compile(r'(?:\$|€|£|¥)?\b\d+(?:[.,:/-]\d+)*(?:%|°[CF]|\s*(?:AM|PM|kg|lbs|mph|km/h|ms|px|GB|MB|KB|GHz|MHz|USD|EUR|GBP|INR)\b)?')
NEGATION_PATTERN = re.compile(r'\b(?:not|never|neither|nor|no|cannot|can\'t|won\'t|didn\'t|doesn\'t|isn\'t|aren\'t|wasn\'t|weren\'t)\b', re.IGNORECASE)

def validate_pair(source: str, target: str) -> tuple[bool, list[str]]:
    errors = []
    
    # 1. Number integrity check
    src_nums = set(NUMBER_PATTERN.findall(source))
    tgt_nums = set(NUMBER_PATTERN.findall(target))
    missing_nums = src_nums - tgt_nums
    if missing_nums:
        errors.append(f"Missing numbers/units in target: {missing_nums}")

    # 2. Negation polarity check
    src_neg = set(n.lower() for n in NEGATION_PATTERN.findall(source))
    tgt_neg = set(n.lower() for n in NEGATION_PATTERN.findall(target))
    if src_neg and not tgt_neg:
        errors.append(f"Source had negations {src_neg} but target contains none")

    # 3. Minimum length ratio (prevent arbitrary truncation)
    src_words = len(source.split())
    tgt_words = len(target.split())
    if src_words > 0 and (tgt_words / src_words) < 0.65:
        errors.append(f"Excessive length reduction: source={src_words}w, target={tgt_words}w")

    return len(errors) == 0, errors

def main():
    path = Path("training/dataset_template.jsonl")
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])

    if not path.exists():
        print(f"Error: Dataset file not found at {path}")
        sys.exit(1)

    valid_count = 0
    total_count = 0

    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            total_count += 1
            data = json.loads(line)
            messages = data.get("messages", [])
            user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
            asst_msg = next((m["content"] for m in messages if m["role"] == "assistant"), "")

            valid, errs = validate_pair(user_msg, asst_msg)
            if valid:
                valid_count += 1
            else:
                print(f"[Line {idx}] Validation issue: {', '.join(errs)}")

    print(f"\n--- Validation Summary ---")
    print(f"Total samples: {total_count}")
    print(f"Valid samples: {valid_count}")
    print(f"Integrity rate: {(valid_count / total_count * 100) if total_count else 0:.1f}%")

if __name__ == "__main__":
    main()
