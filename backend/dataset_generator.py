import json
from pathlib import Path

DATASET = [
    # 1. Financial & Business
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "The quarterly earnings call took place on October 14, 2025. Total revenue rose by 14.8% to $12.4M, whereas operating margins did not decline below 21%. Furthermore, Dr. Aris Thorne stated that product delivery would not commence before Q1 2026 unless client approvals are finalized."},
            {"role": "assistant", "content": "The quarterly earnings call took place on October 14, 2025. Total revenue grew 14.8% to reach $12.4M, and operating margins held firm, not dipping below 21%. Dr. Aris Thorne also noted that product delivery won't start until Q1 2026, unless client approvals are wrapped up sooner."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "It is important to note that the fiscal year 2024 generated $450,000 in recurring subscriptions. However, 12 customers did not renew their annual service agreements. CFO Marcus Vance emphasized that operational expenditure was reduced by 8.5% across all 4 regional subsidiaries."},
            {"role": "assistant", "content": "Fiscal year 2024 brought in $450,000 from recurring subscriptions, though 12 customers chose not to renew their annual service plans. CFO Marcus Vance highlighted that operational spending dropped 8.5% across all 4 regional subsidiaries."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "During the board summit on November 3, 2025, Helena Rostova announced an initial budget of €3.2M for European market penetration. She warned that profitability cannot be achieved within the first 18 months."},
            {"role": "assistant", "content": "At the board summit on November 3, 2025, Helena Rostova unveiled a €3.2M budget to expand into Europe. She cautioned that the initiative cannot turn a profit within its first 18 months."}
        ]
    },
    # 2. Medical, Scientific & Academic
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "In accordance with the study conducted by Larson et al. [3], 42 out of 50 patient subjects did not display adverse reactions to the 100mg dosage. However, patients with preexisting cardiovascular conditions were specifically excluded from the cohort."},
            {"role": "assistant", "content": "As shown in the study by Larson et al. [3], 42 of the 50 patients showed no adverse reactions to the 100mg dose. Crucially, individuals with preexisting cardiovascular conditions were not included in the cohort."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "The clinical trial commenced on January 15, 2026, administering 50mg of compound AZ-902 twice daily. Statistical significance was verified at p < 0.01, yet researchers could not conclude a causal link between treatment duration and long-term remission."},
            {"role": "assistant", "content": "The clinical trial began on January 15, 2026, testing a 50mg dose of compound AZ-902 twice a day. Even though statistical significance was confirmed at p < 0.01, researchers were unable to establish a causal connection between the length of treatment and long-term remission."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "The temperature of the reaction vessel was maintained at 78.5°C under 2.4 atmospheres of pressure. Despite multiple iterations, yield did not surpass 64.2%, and trace impurities were detected in 3 out of 10 samples."},
            {"role": "assistant", "content": "The reaction vessel was kept at 78.5°C under 2.4 atmospheres of pressure. Across multiple runs, the yield never rose above 64.2%, with minor impurities showing up in 3 of the 10 samples."}
        ]
    },
    # 3. Technical, Software & Systems
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "The distributed database cluster experienced 99.98% uptime in February 2026. Latency spikes exceeding 250ms were isolated to node cluster us-east-1b, affecting approximately 1,200 concurrent user sessions. No data loss occurred during the failover event."},
            {"role": "assistant", "content": "The distributed database cluster achieved 99.98% uptime throughout February 2026. Latency spikes above 250ms were confined to the us-east-1b node cluster, impacting around 1,200 active user sessions, though no data was lost during the failover."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "Engineers deployed patch v4.2.1 on August 19, 2025. Memory consumption was reduced by 35MB per container worker, but throughput did not increase beyond 14,000 queries per second under stress testing."},
            {"role": "assistant", "content": "The engineering team rolled out patch v4.2.1 on August 19, 2025. Each worker container consumed 35MB less memory, although throughput topped out at 14,000 queries per second during stress testing."}
        ]
    },
    # 4. Strict Negations & Causal Logic
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "The audit committee did not approve the transfer of $85,000 on March 4, 2026, because compliance documentation was neither signed by the division lead nor validated by internal legal counsel."},
            {"role": "assistant", "content": "The audit committee withheld approval for the $85,000 transfer on March 4, 2026, as compliance forms were neither signed by the division lead nor cleared by internal legal counsel."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "Preliminary benchmarks suggest that algorithm B is 2.3x faster than algorithm A. However, this does not imply that algorithm B is suitable for low-memory mobile hardware with under 4GB of RAM."},
            {"role": "assistant", "content": "Early benchmarks show algorithm B running 2.3x faster than algorithm A. That said, this doesn't mean algorithm B is ready for budget mobile devices equipped with less than 4GB of RAM."}
        ]
    },
    # 5. Professional & Conversational Communications
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "I am writing to formally communicate that your candidate interview with David Sterling has been rescheduled from Thursday, April 9 at 2:00 PM to Friday, April 10 at 10:30 AM EST. Please confirm your availability by Wednesday at 5:00 PM."},
            {"role": "assistant", "content": "I wanted to let you know that your interview with David Sterling has been moved from Thursday, April 9 at 2:00 PM to Friday, April 10 at 10:30 AM EST. Please let us know if that time works for you by Wednesday at 5:00 PM."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "Please be advised that all 3 deliverables outlined in project milestone 4 must be finalized prior to December 18, 2025. Failure to submit deliverables will result in a 5% contractual penalty per day."},
            {"role": "assistant", "content": "Just a reminder that all 3 deliverables for milestone 4 need to be finished before December 18, 2025. Late submissions incur a 5% contract penalty for each day delayed."}
        ]
    }
]

def save_dataset(filepath="expanded_training_data_14b.jsonl"):
    with open(filepath, "w", encoding="utf-8") as f:
        for item in DATASET:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Saved {len(DATASET)} high-quality samples to {filepath}")

if __name__ == "__main__":
    save_dataset()
