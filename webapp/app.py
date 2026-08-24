"""
Step 5: Multi-Page GUI Web App (Flask)
----------------------------------
A real, functional multi-page web application for the Tax Compliance
Deviation system. Pages:

    /               -> Dashboard (summary stats + chart)
    /people         -> Searchable/sortable list of all people
    /person/<id>    -> Full detail page for one person (all linked records
                       + graph connections + audit trail)
    /api/search      -> JSON search endpoint used by the live search box

Run with:  python app.py
Then open: http://127.0.0.1:5000
"""

import csv
import os
from flask import Flask, render_template, request, jsonify, abort

app = Flask(__name__)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")


def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_all_data():
    """Load and index all data once per request (simple, fine for this scale)."""
    audit = load_csv("audit_results.csv")
    resolved = {r["resolved_id"]: r for r in load_csv("resolved_entities.csv")}
    return audit, resolved


def score_class(score):
    score = int(score)
    if score >= 70:
        return "high"
    if score >= 30:
        return "mid"
    return "low"



TAX_SLABS = [
    {
        "range": "Up to Rs. 600,000",
        "rate": "0%",
        "formula": "No tax",
        "calc": lambda i: 0,
    },
    {
        "range": "Rs. 600,001 - Rs. 1,200,000",
        "rate": "1%",
        "formula": "1% of amount exceeding Rs. 600,000",
        "calc": lambda i: (i - 600000) * 0.01,
    },
    {
        "range": "Rs. 1,200,001 - Rs. 2,200,000",
        "rate": "11%",
        "formula": "Rs. 6,000 + 11% of amount exceeding Rs. 1,200,000",
        "calc": lambda i: 6000 + (i - 1200000) * 0.11,
    },
    {
        "range": "Rs. 2,200,001 - Rs. 3,200,000",
        "rate": "23%",
        "formula": "Rs. 116,000 + 23% of amount exceeding Rs. 2,200,000",
        "calc": lambda i: 116000 + (i - 2200000) * 0.23,
    },
    {
        "range": "Rs. 3,200,001 - Rs. 4,100,000",
        "rate": "30%",
        "formula": "Rs. 346,000 + 30% of amount exceeding Rs. 3,200,000",
        "calc": lambda i: 346000 + (i - 3200000) * 0.30,
    },
    {
        "range": "Above Rs. 4,100,000",
        "rate": "35%",
        "formula": "Rs. 616,000 + 35% of amount exceeding Rs. 4,100,000",
        "calc": lambda i: 616000 + (i - 4100000) * 0.35,
    },
]

SLAB_BOUNDS = [600000, 1200000, 2200000, 3200000, 4100000]


def slab_index_for_income(income):
    for idx, bound in enumerate(SLAB_BOUNDS):
        if income <= bound:
            return idx
    return len(SLAB_BOUNDS)


def estimated_tax(income):
    """Rough estimated annual tax for a given declared income, using the
    FY 2025-26 FBR salary slabs. For reference/education only -> not a
    substitute for an actual tax computation (credits, surcharge, etc.
    are not applied here, except the 9% surcharge note below)."""
    if income <= 0:
        return 0
    idx = slab_index_for_income(income)
    tax = TAX_SLABS[idx]["calc"](income)
    return round(tax)

SCORING_RULES = [
    {
        "points": 35,
        "title": "Non-filer / zero declared income + owns a vehicle",
        "detail": "Person did not file a return (or declared 0 income) but a "
                   "vehicle of any engine size is registered to them.",
    },
    {
        "points": 35,
        "title": "Non-filer / zero declared income + high electricity bill",
        "detail": "Person did not file a return (or declared 0 income) but their "
                   "monthly electricity bill is Rs. 80,000 or more (luxury-level usage).",
    },
    {
        "points": 25,
        "title": "Owns a luxury vehicle but declared low income",
        "detail": "Vehicle engine size is 1800cc or larger, while declared annual "
                   "income is above 0 but below Rs. 600,000.",
    },
    {
        "points": 25,
        "title": "High electricity bill but declared low income",
        "detail": "Monthly electricity bill is Rs. 80,000 or more, while declared "
                   "annual income is above 0 but below Rs. 600,000.",
    },
]

SCORE_BANDS = [
    {"range": "0", "label": "No Deviation", "class": "low", "meaning": "No mismatch found between lifestyle signals and declared income."},
    {"range": "1 - 29", "label": "Low Risk", "class": "low", "meaning": "Minor or single-factor mismatch; usually low priority."},
    {"range": "30 - 69", "label": "Medium Risk", "class": "mid", "meaning": "Two or more mismatch factors, or one large mismatch; worth a closer look."},
    {"range": "70 - 100", "label": "High Risk", "class": "high", "meaning": "Multiple strong mismatches (e.g. non-filer with both a vehicle and a high bill); top audit priority."},
]


@app.template_filter("comma")
def comma_filter(value):
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value



@app.route("/")
def dashboard():
    audit, _ = load_all_data()
    total = len(audit)
    flagged = sum(1 for r in audit if int(r["deviation_score"]) > 0)
    high_risk = sum(1 for r in audit if int(r["deviation_score"]) >= 70)
    avg_score = round(sum(int(r["deviation_score"]) for r in audit) / total, 1) if total else 0

    return render_template(
        "dashboard.html",
        total=total, flagged=flagged, high_risk=high_risk, avg_score=avg_score,
    )


@app.route("/people")
def people():
    audit, _ = load_all_data()
    for r in audit:
        r["score_class"] = score_class(r["deviation_score"])
    audit.sort(key=lambda r: int(r["deviation_score"]), reverse=True)
    return render_template("people.html", people=audit)


@app.route("/person/<resolved_id>")
def person_detail(resolved_id):
    audit, resolved = load_all_data()
    audit_row = next((r for r in audit if r["resolved_id"] == resolved_id), None)
    detail_row = resolved.get(resolved_id)

    if not audit_row or not detail_row:
        abort(404)

    audit_row["score_class"] = score_class(audit_row["deviation_score"])
    reasons = [r.strip() for r in audit_row["audit_reasons"].split("|")] if audit_row["audit_reasons"] else []

    return render_template(
        "person_detail.html",
        person=audit_row,
        detail=detail_row,
        reasons=reasons,
    )


@app.route("/guide")
def guide():
    return render_template(
        "guide.html",
        scoring_rules=SCORING_RULES,
        score_bands=SCORE_BANDS,
        tax_slabs=TAX_SLABS,
    )


@app.route("/api/tax-estimate")
def api_tax_estimate():
    """Given ?income=<annual PKR>, returns which slab it falls in + estimated tax."""
    try:
        income = int(request.args.get("income", "0"))
    except ValueError:
        income = 0
    idx = slab_index_for_income(income) if income > 0 else 0
    tax = estimated_tax(income)
    slab = TAX_SLABS[idx]
    return jsonify({
        "income": income,
        "slab_range": slab["range"],
        "slab_rate": slab["rate"],
        "formula": slab["formula"],
        "estimated_annual_tax": tax,
        "estimated_monthly_tax": round(tax / 12) if tax else 0,
    })


@app.route("/api/search")
def api_search():
    """Live search endpoint: matches by name or CNIC, returns JSON."""
    q = request.args.get("q", "").strip().lower()
    audit, _ = load_all_data()

    if not q:
        results = audit
    else:
        results = [
            r for r in audit
            if q in r["filer_name"].lower() or q in r["cnic"].lower()
        ]

    results = sorted(results, key=lambda r: int(r["deviation_score"]), reverse=True)[:20]
    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
