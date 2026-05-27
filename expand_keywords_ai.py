#!/usr/bin/env python3
"""Expand keywords.json using Claude API to generate related keywords from published articles."""
import anthropic
import json
import os
import re
import glob
from datetime import datetime

SIMILARITY_THRESHOLD = 0.70
KEYWORDS_PER_TOPIC = 10


def load_keywords():
    with open("keywords.json", "r") as f:
        return json.load(f)


def save_keywords(data):
    with open("keywords.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
    if any(w in q for w in ["property", "real estate", "ejido", "fideicomiso"]):
        return "category_5_real_estate"
    if any(w in q for w in ["social security", "wep", "gpo", "ssa"]):
        return "category_6_social_security"
    if any(w in q for w in ["sns", "imss", "hospital", "dental", "healthcare", "prescription"]):
        return "category_7_healthcare_local"
    if any(w in q for w in ["cost of living", "budget", "utilities", "inflation"]):
        return "category_8_cost_of_living"
    return "category_1_medicare_insurance"


def get_article_topics():
    topics = []
    # Collect topics from used keywords (articles already written)
    try:
        keywords = load_keywords()
        used = [e for e in keywords if e.get("used")]
        for entry in used[:10]:
            topics.append({"topic": entry["keyword"], "category": entry["category"]})
    except Exception:
        pass
    # Also scan articles directory for HTML files
    for filepath in glob.glob("articles/*.html")[:10]:
        basename = os.path.basename(filepath)
        # Extract topic from filename: YYYY-MM-DD-topic-slug.html
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", basename).replace(".html", "").replace("-", " ")
        if slug and not any(t["topic"] == slug for t in topics):
            topics.append({"topic": slug, "category": infer_category(slug)})
    return topics[:10]


def expand_topic(client, topic, category, existing_keywords):
    prompt = f"""You are a keyword research assistant for a website targeting Americans aged 55-70 planning to retire in Portugal or Mexico.

Topic: "{topic}"
Category: {category}

Generate exactly {KEYWORDS_PER_TOPIC} long-tail search keywords that someone dealing with this topic would actually search for. Focus on:
- Specific problems, failures, penalties, and pitfalls (emotional/pain keywords)
- How-to and step-by-step action queries (transactional)
- Comparison/decision queries (commercial)

Format: One keyword per line, no numbers, no quotes, no explanations.
Keywords must be 4-10 words, lowercase, include "american retiree", "portugal", or "mexico" where natural.

Example for "D7 visa rejected":
d7 visa appeal process portugal american retiree
d7 visa reapply timeline after rejection
d7 visa lawyer cost portugal american
portugal d7 visa rejected what to do next
d7 visa income proof requirements 2024
portuguese consulate d7 visa rejection reasons
d7 visa bank statement requirements american
portugal d7 passive income proof documents
d7 visa interview preparation american retiree
portugal d7 reapplication success rate american"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    new_keywords = []
    for line in raw.splitlines():
        kw = line.strip().lower()
        if not kw or len(kw.split()) < 3:
            continue
        if is_duplicate(kw, existing_keywords + new_keywords):
            continue
        new_keywords.append({
            "keyword": kw,
            "category": category,
            "intent": classify_intent(kw),
            "source": "ai_expansion",
            "used": False,
            "added_at": datetime.now().strftime("%Y-%m-%d"),
            "priority": "high" if classify_intent(kw) == "emotional" else "normal"
        })
    return new_keywords


def main():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    keywords = load_keywords()
    topics = get_article_topics()

    if not topics:
        print("No topics found for AI expansion.")
        return

    total_added = 0
    for topic_info in topics:
        new_kws = expand_topic(client, topic_info["topic"], topic_info["category"], keywords)
        keywords.extend(new_kws)
        total_added += len(new_kws)
        print(f"Topic '{topic_info['topic']}': added {len(new_kws)} keywords")

    save_keywords(keywords)
    print(f"\nAI expansion: added {total_added} new keywords (total: {len(keywords)})")


if __name__ == "__main__":
    main()
