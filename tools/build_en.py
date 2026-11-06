#!/usr/bin/env python3
"""Builds the English (US) section of DentsGuide at /en.

Articles live in tools/en_articles/*.md with a small header:
---
title: ...
description: ...
tag: ...
order: 1
---
Product buttons: [[amz:search words|Button label]]
Set AMAZON_TAG below once the Amazon Associates account is approved;
every Amazon link on the English pages picks it up on the next build.

Run from the repo root:  python3 tools/build_en.py
"""
import html
import pathlib
import re
import urllib.parse

import markdown
import yaml

AMAZON_TAG = ""  # e.g. "dentsguide-20"

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "tools" / "en_articles"
OUT = ROOT / "en"

DISCLOSURE = ("As an Amazon Associate, DentsGuide earns from qualifying purchases. "
              "Buying through our links never costs you more.")


def amz_url(query):
    url = "https://www.amazon.com/s?k=" + urllib.parse.quote_plus(query)
    if AMAZON_TAG:
        url += "&tag=" + AMAZON_TAG
    return url


def shortcodes(text):
    def repl(m):
        query, _, label = m.group(1).partition("|")
        return (f'<a class="buy" href="{html.escape(amz_url(query))}" target="_blank" '
                f'rel="sponsored nofollow noopener">{html.escape(label or "See on Amazon")}</a>')
    return re.sub(r"\[\[amz:([^\]]+)\]\]", repl, text)


def page(title, description, body, prefix, canonical, alt_he=None):
    hreflang = ""
    if alt_he:
        hreflang = (f'<link rel="alternate" hreflang="en" href="https://dentsguide.com{canonical}">\n'
                    f'<link rel="alternate" hreflang="he" href="https://dentsguide.com{alt_he}">\n')
    return f"""<!doctype html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="https://dentsguide.com{canonical}">
{hreflang}<link rel="stylesheet" href="{prefix}../style.css">
</head>
<body>
<header class="site"><div class="wrap">
  <a class="logo" href="{prefix}index.html">Dents<span>Guide</span><small>Family Dental Care</small></a>
  <nav><a href="{prefix}index.html">Guides</a><a href="{prefix}about.html">About</a><a class="lang-switch" href="{prefix}../index.html" hreflang="he">עברית</a></nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
DentsGuide publishes general information about oral care products for families. It is not a substitute for advice from a dentist.
<p class="aff"><strong>Affiliate disclosure:</strong> {DISCLOSURE}</p>
</div></footer>
</body>
</html>
"""


def load():
    items = []
    for f in sorted(SRC.glob("*.md")):
        _, head, body = f.read_text(encoding="utf-8").split("---", 2)
        meta = yaml.safe_load(head)
        meta["slug"], meta["body"] = f.stem, body
        items.append(meta)
    return sorted(items, key=lambda a: a.get("order", 99))


def build():
    (OUT / "articles").mkdir(parents=True, exist_ok=True)
    arts = load()
    for a in arts:
        body = markdown.markdown(shortcodes(a["body"]), extensions=["tables"])
        content = (f'<article><div class="tag">{html.escape(a["tag"])}</div><h1>{html.escape(a["title"])}</h1>'
                   f'{body}</article>')
        (OUT / "articles" / f'{a["slug"]}.html').write_text(
            page(a["title"] + " | DentsGuide", a["description"], content, "../",
                 f'/en/articles/{a["slug"]}.html'), encoding="utf-8")
    cards = "".join(
        f'<a class="card" href="articles/{a["slug"]}.html"><div class="tag">{html.escape(a["tag"])}</div>'
        f'<h2>{html.escape(a["title"])}</h2><p>{html.escape(a["description"])}</p></a>' for a in arts)
    home = ('<section class="hero"><h1>Simple, honest guides to healthy teeth for the whole family</h1>'
            '<p>How to choose toothbrushes, toothpaste and flossing tools for kids and adults, without the guesswork.</p></section>'
            f'<section class="cards">{cards}</section>')
    (OUT / "index.html").write_text(
        page("DentsGuide | Family Dental Care Guides",
             "Practical guides to choosing oral care products for kids and adults.", home, "", "/en/",
             alt_he="/"), encoding="utf-8")
    about = ('<article><h1>About DentsGuide</h1>'
             '<p>DentsGuide helps parents and adults choose everyday oral care products: toothbrushes, toothpaste, '
             'flossers and the small tools that make brushing easier.</p>'
             '<h2>Affiliate disclosure</h2><p>' + DISCLOSURE + ' We only recommend product types we would use at home.</p>'
             '<h2>Medical note</h2><p>Everything on this site is general information, not medical advice. '
             'For questions about your own teeth or your child\'s, talk to a dentist.</p></article>')
    (OUT / "about.html").write_text(page("About | DentsGuide", "About DentsGuide and our affiliate disclosure.",
                                         about, "", "/en/about.html"), encoding="utf-8")
    print(f"Built {len(arts)} English articles")
    return arts


if __name__ == "__main__":
    build()
