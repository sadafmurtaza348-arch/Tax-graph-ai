# 🔍 Tax Graph AI — Broadening the National Tax Net

A rule-based, explainable AI system that flags potential tax compliance
deviations by comparing people's **declared income** against their
**lifestyle signals** — vehicle ownership and electricity usage — using
entity resolution and a knowledge graph.

**🌐 Live demo:** [sadaf348.pythonanywhere.com](https://sadaf348.pythonanywhere.com)

---

## What it does

Many people under-report income on their tax returns. This project cross-references
three separate data sources for the same individual — **tax filings**, **vehicle
registration**, and **utility bills** — resolves them into a single identity even when
names are recorded slightly differently across sources, then flags anyone whose
lifestyle doesn't match their declared income.

Every flag comes with a **plain-English reason**, not just a black-box score —
that's the whole point: an auditor should be able to see *why* a person was flagged.

### Pipeline

tax_filings.csv, vehicles.csv, and utility_bills.csv all feed into an
Entity Resolution step (fuzzy name matching across the three sources),
which builds a Knowledge Graph (build_graph.py) linking each person to
their vehicle(s) and bill(s). That graph feeds Anomaly Detection, which
computes a deviation score and audit reasons per person, which the Web
Dashboard then displays.

1. **`entity_resolution.py`** — matches records across the three datasets that likely
   belong to the same person (fuzzy name matching), even with typos/formatting differences.
2. **`build_graph.py`** — builds a knowledge graph linking each person to their vehicle(s)
   and utility bill(s).
3. **`anomaly_detection.py`** — computes a 0–100 **Deviation Score** per person using
   transparent rules (e.g. "owns a 2500cc vehicle but declared only 300,000 PKR income"),
   and generates a human-readable audit trail.
4. **`webapp/`** — a Flask app that presents everything: a dashboard, a searchable/sortable
   list of all people, individual profile pages, and a **Guide** page explaining exactly
   how scores are calculated, plus a Pakistan income tax slab reference table.

## Features

- 📊 **Dashboard** — summary stats (total people, flagged, high risk, average score)
- 👥 **All People** — live-searchable, sortable table of every person, ranked by risk
- 🧾 **Person Detail** — full profile per person: declared income, vehicle, utility bill,
  matched audit reasons, and graph connections
- 📖 **Guide** — the scoring rules explained (why points are given), score-band meanings,
  and Pakistan's official FBR salary tax slabs with a quick tax estimator
- 🔎 Live nav-bar search by name or CNIC (JSON API-backed)

## Tech stack

- **Backend:** Python, Flask
- **Data processing:** entity resolution (fuzzy matching), knowledge graph construction
- **Frontend:** Jinja2 templates, vanilla JS, Chart.js
- **Data:** CSV (tax filings, vehicles, utility bills) → resolved entities → audit results

## Running it locally

Clone the repo, install dependencies from requirements.txt, then (optionally)
regenerate the audit results by running entity_resolution.py, build_graph.py,
and anomaly_detection.py in order from the src folder. Finally, cd into the
webapp folder and run app.py, then open http://127.0.0.1:5000 in your browser.

## Project structure

The repo has three main folders: data (CSV files plus the generated knowledge
graph), src (the three Python pipeline scripts), and webapp (app.py plus the
templates folder containing dashboard, people, person detail, and guide pages).
There's also a requirements.txt and Procfile at the root.

## Disclaimer

This is a demonstration / academic project. The Pakistan income tax slabs shown in
the Guide page are for reference/education only (FBR FY 2025–26 salary rates) —
always confirm current rates directly with FBR before relying on them for a real filing.
