"""Copy the newest deal from the Telegram channel to the Facebook page.

Runs once a day from GitHub Actions (.github/workflows/fb-crosspost.yml).
Reads the public channel preview at t.me/s/kids_deals_il, picks the newest
post with a photo that was not posted yet, and publishes it to the page as a
photo post. The buy link points to the Telegram post itself, so Facebook
visitors land in the channel and can join it.

Secrets (GitHub repo settings > Secrets and variables > Actions):
  FB_PAGE_ID     numeric id of the page "דילים לקטנטנים מעלי"
  FB_PAGE_TOKEN  long-lived Page access token with pages_manage_posts
State: tools/fb_state.json keeps the last Telegram post number published.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

CHANNEL = "kids_deals_il"
GRAPH = "https://graph.facebook.com/v23.0"
STATE = Path(__file__).with_name("fb_state.json")
CTA_RE = re.compile(r"👉\s*לקנייה לחצו כאן\s*$")


def fetch(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def channel_posts(html):
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    for m in soup.select(".tgme_widget_message[data-post]"):
        num = int(m["data-post"].split("/")[-1])
        text_el = m.select_one(".tgme_widget_message_text")
        photo = m.select_one(".tgme_widget_message_photo_wrap")
        if not text_el or not photo:
            continue
        img = re.search(r"url\(['\"]?(.*?)['\"]?\)", photo.get("style", ""))
        if not img:
            continue
        for br in text_el.find_all("br"):
            br.replace_with("\n")
        posts.append({"num": num, "text": text_el.get_text().strip(), "image": img.group(1)})
    return posts


def caption(post):
    text = CTA_RE.sub("", post["text"]).rstrip()
    return (f"{text}\n👉 לפרטים ולקנייה: https://t.me/{CHANNEL}/{post['num']}\n\n"
            f"עוד דילים לילדים כל יום בערוץ הטלגרם שלנו: https://t.me/{CHANNEL}")


def main():
    page_id = os.environ.get("FB_PAGE_ID", "").strip()
    token = os.environ.get("FB_PAGE_TOKEN", "").strip()
    dry = "--dry-run" in sys.argv
    if not dry and (not page_id or not token):
        print("FB_PAGE_ID / FB_PAGE_TOKEN not set yet - skipping.")
        return
    state = json.loads(STATE.read_text()) if STATE.exists() else {"last_post": 0}
    posts = [p for p in channel_posts(fetch(f"https://t.me/s/{CHANNEL}")) if p["num"] > state["last_post"]]
    if not posts:
        print("No new Telegram posts since", state["last_post"])
        return
    post = max(posts, key=lambda p: p["num"])
    msg = caption(post)
    if dry:
        print(msg, "\n", post["image"])
        return
    data = urllib.parse.urlencode({"url": post["image"], "caption": msg, "access_token": token}).encode()
    try:
        resp = json.loads(fetch(f"{GRAPH}/{page_id}/photos", data))
    except urllib.error.HTTPError as e:
        print("Facebook error:", e.read().decode("utf-8", "replace"))
        sys.exit(1)
    print("Posted to Facebook:", resp)
    STATE.write_text(json.dumps({"last_post": post["num"]}) + "\n")


if __name__ == "__main__":
    main()
