#!/usr/bin/env python3
"""Expand keywords.json from Google Search Console query data."""
import json
import os
import re
from datetime import datetime, timedelta

SITE_URL = "sc-domain:retireabroad-hub.com"
SIMILARITY_THRESHOLD = 0.70


def load_keywords():
    with open("keywords.json", "r") as f:
        return json.load(f)


def save_keywords(data):
    with open("keywords.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def classify_intent(query):
    q = query.lower()
    if any(w in q for w in ["rejected", "denied", "penalty", "trap", "problem", "mistake", "failed", "closed", "frozen", "shock"]):
        return "emotional"
    if any(w in q for w in ["how to", "step by step", "apply", "file", "open", "get", "enroll"]):
        return "transactional"
    if any(w in q for w in ["best", "vs", "comparison", "review", "cost", "price", "recommend"]):
        return "commercial"
    return "informational"


def infer_category(query):
    q = query.lower()
    if any(w in q for w in ["medicare", "insurance", "cobra", "cigna", "img", "safetywing"]):
        return "category_1_medicare_insurance"
    if any(w in q for w in ["fbar", "fatca", "tax", "irs", "nhr"]):
        return "category_2_tax_fbar"
    if any(w in q for w in ["visa", "d7", "residency", "aima", "immigration", "citizenship"]):
        return "category_3_visa_residency"
    if any(w in q for w in ["bank", "banking", "transfer", "wire", "wise", "schwab", "currency"]):
        return "category_4_banking_finance"
    if any(w in q for w in ["property", "real estate", "buy", "rent", "mortgage", "ejido", "fideicomiso"]):
        return "category_5_real_estate"
    if any(w in q for w in ["social security", "wep", "gpo", "ssa", "pension"]):
        return "category_6_social_security"
    if any(w in q for w in ["sns", "imss", "hospital", "dental", "healthcare", "prescription"]):
        return "category_7_healthcare_local"
    if any(w in q for w in ["cost of living", "budget", "rent", "utilities", "inflation"]):
        return "category_8_cost_of_living"
    return "category_1_medicare_insurance"


def word_similarity(a, b):
    words_a = set(re.sub(r"[^a-z0-9 ]", "", a.lower()).split())
    words_b = set(re.sub(r"[^a-z0-9 ]", "", b.lower()).split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def is_duplicate(new_kw, existing_keywords):
    for entry in existing_keywords:
        if word_similarity(new_kw, entry["keyword"]) >= SIMILARITY_THRESHOLD:
            return True
    return False


def fetch_gsc_queries():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        print("google-auth and google-api-python-client required. Install with: pip install google-auth google-api-python-client")
        return []

    creds_json = os.environ.get("GSC_CREDENTIALS_JSON")
    if not creds_json:
        print("GSC_CREDENTIALS_JSON secret not set. Skipping GSC expansion.")
        return []

    try:
        creds_data = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
        )
        service = build("searchconsole", "v1", credentials=creds)

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")

        response = service.searchanalytics().query(
            siteUrl=SITE_URL,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "rowLimit": 500,
                "dimensionFilterGroups": [{
                    "filters": [{"dimension": "country", "operator": "equals", "expression": "USA"}]
                }]
            }
        ).execute()

        rows = response.get("rows", [])
        return [
            {"query": row["keys"][0], "impressions": row.get("impressions", 0)}
            for row in rows
            if row.get("impressions", 0) > 0
        ]
    except Exception as e:
        print(f"GSC API error: {e}")
        return []


def main():
    keywords = load_keywords()
    today = datetime.now().strftime("%Y-%m-%d")

    rows = fetch_gsc_queries()
    if not rows:
        print("No GSC queries retrieved.")
        return

    added = 0
    for row in rows:
        query = row["query"].strip().lower()
        # Skip very short queries
        if len(query.split()) < 3:
            continue
        if is_duplicate(query, keywords):
            continue

        intent = classify_intent(query)
        category = infer_category(query)
        priority = "high" if intent == "emotional" else "normal"

        keywords.append({
            "keyword": query,
            "category": category,
            "intent": intent,
            "source": "gsc",
            "used": False,
            "added_at": today,
            "priority": priority
        })
        added += 1

    save_keywords(keywords)
    print(f"GSC expansion: added {added} new keywords (total: {len(keywords)})")


if __name__ == "__main__":
    main()
