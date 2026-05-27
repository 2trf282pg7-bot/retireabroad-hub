#!/usr/bin/env python3
"""Add /portugal/ article URLs to sitemap.xml after article generation."""
import os
from datetime import datetime

SITE_DOMAIN = "retireabroad-hub.com"
TODAY = datetime.now().strftime("%Y-%m-%d")

NEW_URLS = [
    "/portugal/health-insurance/medicare-part-b-penalty/",
    "/portugal/fbar-tax/fbar-requirement-retiree/",
    "/portugal/d7-rejection/why-d7-visa-rejected/",
    "/portugal/banking/us-bank-account-closed-expat/",
    "/portugal/health-insurance/health-insurance-gap-retiree/",
]

sitemap_path = "sitemap.xml"
with open(sitemap_path, "r") as f:
    content = f.read()

added = 0
for path in NEW_URLS:
    url = f"https://{SITE_DOMAIN}{path}"
    if url not in content:
        entry = (
            f"  <url>\n    <loc>{url}</loc>\n"
            f"    <lastmod>{TODAY}</lastmod>\n"
            f"    <changefreq>monthly</changefreq>\n"
            f"    <priority>0.8</priority>\n  </url>"
        )
        content = content.replace("</urlset>", f"{entry}\n</urlset>")
        added += 1
        print(f"Added: {url}")

with open(sitemap_path, "w") as f:
    f.write(content)

print(f"Done. {added} URLs added to sitemap.xml")
