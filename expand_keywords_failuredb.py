#!/usr/bin/env python3
"""Expand keywords.json from failure-db.json entries."""
import json
import os
import re
from datetime import datetime

SIMILARITY_THRESHOLD = 0.70
FAILURE_DB_PATH = "failure-db.json"


def load_keywords():
    with open("keywords.json", "r") as f:
        return json.load(f)


def save_keywords(data):
    with open("keywords.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_failure_db():
    if os.path.exists(FAILURE_DB_PATH):
        with open(FAILURE_DB_PATH, "r") as f:
            return json.load(f)
    alt_path = os.path.join("data", "failure-db.json")
    if os.path.exists(alt_path):
        with open(alt_path, "r") as f:
            return json.load(f)
    return {"failures": []}


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


def map_category(failure_category):
    mapping = {
        "medicare_insurance": "category_1_medicare_insurance",
        "tax_fbar": "category_2_tax_fbar",
        "visa_residency": "category_3_visa_residency",
        "banking_finance": "category_4_banking_finance",
        "real_estate": "category_5_real_estate",
        "social_security": "category_6_social_security",
        "healthcare_local": "category_7_healthcare_local",
        "cost_of_living": "category_8_cost_of_living",
    }
    for key, val in mapping.items():
        if key in failure_category:
            return val
    return "category_1_medicare_insurance"


def generate_keywords_from_failure(failure):
    """Generate 2-4 search keywords from a failure case."""
    situation = failure.get("situation", "").lower()
    outcome = failure.get("outcome", "").lower()
    category = failure.get("category", "")
    failure_id = failure.get("id", "")

    keywords = []

    # Determine country context
    country = "portugal"
    if "mexico" in situation or "mexican" in situation:
        country = "mexico"

    # Build keywords based on category and situation
    cat = map_category(category)

    if "medicare" in category:
        if "penalty" in situation or "penalty" in outcome:
            keywords.append(f"medicare part b penalty {country} american retiree mistake")
        if "advantage" in situation:
            keywords.append(f"medicare advantage no foreign coverage {country} retiree trap")
        if "denied" in outcome or "denied" in situation:
            keywords.append(f"insurance claim denied {country} american retiree what to do")
        if "pre-existing" in situation or "pre existing" in situation:
            keywords.append(f"pre existing condition insurance denied {country} retiree")

    elif "tax_fbar" in category:
        if "fbar" in situation.lower() or "fbar" in failure_id:
            keywords.append(f"fbar penalty american retiree {country} mistake how to fix")
        if "nhr" in situation.lower():
            keywords.append(f"portugal nhr tax mistake american retiree social security")
        if "willful" in outcome:
            keywords.append(f"fbar willful violation american retiree {country} penalty amount")
        if "amended" in outcome or "overpaid" in outcome:
            keywords.append(f"amended tax return american retiree {country} fbar correction")

    elif "visa_residency" in category:
        if "rejected" in situation or "rejected" in outcome or "denied" in outcome:
            keywords.append(f"{country} visa rejected american retiree reason appeal")
        if "income" in situation:
            keywords.append(f"{country} visa income requirement american retiree proof")
        if "wait" in situation or "delay" in outcome:
            keywords.append(f"{country} residency appointment wait time american retiree 2025")

    elif "banking" in category:
        if "closed" in situation or "closure" in outcome:
            keywords.append(f"us bank account closed expat {country} what to do")
        if "frozen" in situation or "frozen" in outcome or "hold" in outcome:
            keywords.append(f"bank wire transfer frozen american retiree {country}")
        if "social security" in outcome:
            keywords.append(f"social security deposit failed bank closed {country} retiree")

    # Always add an emotional "trap" keyword for failures
    cat_label = category.replace("_", " ").split(" ")[0]
    keywords.append(f"{country} {cat_label} trap american retiree real case")

    return [(kw, cat) for kw in keywords if len(kw.split()) >= 4]


def classify_intent(query):
    q = query.lower()
    if any(w in q for w in ["rejected", "denied", "penalty", "trap", "problem", "mistake", "failed", "closed", "frozen"]):
        return "emotional"
    if any(w in q for w in ["how to", "step by step", "apply", "file", "open", "get", "enroll", "fix"]):
        return "transactional"
    if any(w in q for w in ["best", "vs", "comparison", "review", "cost", "price", "recommend"]):
        return "commercial"
    return "informational"


def main():
    keywords = load_keywords()
    failure_db = load_failure_db()
    failures = failure_db.get("failures", [])
    today = datetime.now().strftime("%Y-%m-%d")

    added = 0
    for failure in failures:
        generated = generate_keywords_from_failure(failure)
        for kw, category in generated:
            kw = kw.strip().lower()
            if is_duplicate(kw, keywords):
                continue
            intent = classify_intent(kw)
            keywords.append({
                "keyword": kw,
                "category": category,
                "intent": intent,
                "source": "failure_db",
                "used": False,
                "added_at": today,
                "priority": "high"  # all failure-derived keywords are high priority
            })
            added += 1

    save_keywords(keywords)
    print(f"Failure DB expansion: added {added} new keywords (total: {len(keywords)})")


if __name__ == "__main__":
    main()
