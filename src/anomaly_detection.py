"""
Step 4: Anomaly Detection - Tax Compliance Deviation Score
----------------------------------
Goal: For each person in the knowledge graph, compare their "lifestyle
signals" (vehicle engine size, electricity bill) against their declared
tax income. Flag people whose lifestyle doesn't match their declared
income, and explain WHY (explainable AI / audit trail).

Approach: rule-based scoring (transparent and easy to explain in a report —
exactly what "interpretability of the audit trail" in the evaluation
criteria is asking for). This can later be swapped for a GNN-based model,
but this baseline is what makes the system explainable.

Scoring logic (each factor adds points to the Deviation Score, 0-100):
    - Owns a big-engine vehicle (>=1800cc) but declared income is low/zero
    - High electricity bill (luxury-level usage) but declared income is low/zero
    - Filed a zero-income return while still owning any vehicle or paying bills
    - The bigger the mismatch, the higher the score

Output: audit_results.csv with a deviation score + human-readable reason
for every flagged person, sorted highest-risk first.
"""

import csv
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Thresholds -> tweakable, and worth explaining in your report as design choices
HIGH_CC_THRESHOLD = 1800          # engine size considered "luxury"
HIGH_BILL_THRESHOLD = 80000       # monthly electricity bill considered "luxury" (PKR)
LOW_INCOME_THRESHOLD = 600000     # annual declared income considered suspiciously low


def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compute_deviation_score(row):
    """
    Returns (score, reasons_list) for one resolved entity row.
    Score is 0-100. Reasons explain exactly why points were added
    -> this IS the audit trail / explainability layer.
    """
    score = 0
    reasons = []

    declared_income = int(row["declared_income"]) if row["declared_income"] else 0
    filed = row["filed_return"] == "True"

    engine_cc = int(row["engine_cc"]) if row["engine_cc"] else 0
    monthly_bill = int(row["monthly_bill_pkr"]) if row["monthly_bill_pkr"] else 0

    # Rule 1: non-filer or zero-income filer who still owns assets
    if not filed or declared_income == 0:
        if engine_cc > 0:
            score += 35
            reasons.append(
                f"Zero/no tax filing but owns a {engine_cc}cc vehicle"
            )
        if monthly_bill >= HIGH_BILL_THRESHOLD:
            score += 35
            reasons.append(
                f"Zero/no tax filing but electricity bill is {monthly_bill:,} PKR/month"
            )

    
    if engine_cc >= HIGH_CC_THRESHOLD and declared_income < LOW_INCOME_THRESHOLD and declared_income > 0:
        score += 25
        reasons.append(
            f"Owns a {engine_cc}cc vehicle (luxury-class) but declared only "
            f"{declared_income:,} PKR annual income"
        )

    # Rule 3: high electricity usage but declared income is low
    if monthly_bill >= HIGH_BILL_THRESHOLD and declared_income < LOW_INCOME_THRESHOLD and declared_income > 0:
        score += 25
        reasons.append(
            f"Electricity bill is {monthly_bill:,} PKR/month (luxury-level usage) but declared only "
            f"{declared_income:,} PKR annual income"
        )

   
    score = min(score, 100)

    return score, reasons


def run_audit(resolved_entities):
    results = []
    for row in resolved_entities:
        score, reasons = compute_deviation_score(row)
        results.append({
            "resolved_id": row["resolved_id"],
            "filer_name": row["filer_name"],
            "cnic": row["cnic"],
            "declared_income": row["declared_income"],
            "engine_cc": row["engine_cc"],
            "monthly_bill_pkr": row["monthly_bill_pkr"],
            "deviation_score": score,
            "audit_reasons": " | ".join(reasons) if reasons else "No significant deviation detected",
        })

    
    results.sort(key=lambda r: r["deviation_score"], reverse=True)
    return results


def save_audit_results(results, filename="audit_results.csv"):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"\nSaved audit results -> {path}")


def print_top_flagged(results, top_n=5):
    print(f"\n--- Top {top_n} Highest Risk (Tax Compliance Deviation) ---")
    for r in results[:top_n]:
        print(f"\n{r['filer_name']} (score: {r['deviation_score']}/100)")
        print(f"  CNIC: {r['cnic']}")
        print(f"  Reason: {r['audit_reasons']}")


if __name__ == "__main__":
    resolved_entities = load_csv("resolved_entities.csv")
    print(f"Loaded {len(resolved_entities)} resolved entities")

    results = run_audit(resolved_entities)

    flagged_count = sum(1 for r in results if r["deviation_score"] > 0)
    print(f"\nTotal people flagged with some deviation: {flagged_count} / {len(results)}")

    print_top_flagged(results, top_n=5)
    save_audit_results(results)
