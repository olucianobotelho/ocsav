#!/usr/bin/env python3
"""
PaivaIPTV Proxy - Fetches Xtream Codes API data and generates
lightweight per-category JSON files for the Roku app.

GitHub Actions runs this on schedule (every 6 hours).
Output goes to /data/ directory which gets committed to the repo.
"""

import json
import os
import sys
import urllib.request

# ============================================================
# CONFIGURATION - Edit these for your IPTV provider
# ============================================================
SERVER = os.environ.get("IPTV_SERVER", "http://sinalmycn.com:80")
USERNAME = os.environ.get("IPTV_USERNAME", "3610472")
PASSWORD = os.environ.get("IPTV_PASSWORD", "3610472")
# ============================================================

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
BASE = f"{SERVER}/player_api.php?username={USERNAME}&password={PASSWORD}"


def fetch_json(url):
    """Fetch URL and parse JSON."""
    print(f"  Fetching: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "PaivaIPTV-Proxy/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_text(url):
    """Fetch URL as raw text."""
    print(f"  Fetching: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "PaivaIPTV-Proxy/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8")


def save_json(filename, data):
    """Save data as compact JSON to data directory."""
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(path)
    print(f"  Saved {filename}: {len(data) if isinstance(data, list) else 'N/A'} items, {size:,} bytes")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    # ---- Auth check ----
    print("[1/7] Checking auth...")
    auth = fetch_json(BASE)
    if auth.get("user_info", {}).get("auth", 0) != 1:
        print("ERROR: Auth failed!")
        sys.exit(1)
    print(f"  Auth OK. Status: {auth['user_info'].get('status')}")

    # ---- Live Categories (1.4KB) ----
    print("[2/7] Fetching live categories...")
    live_cats = fetch_json(f"{BASE}&action=get_live_categories")
    save_json("live_categories.json", live_cats)

    # ---- Live Streams (234KB) ----
    print("[3/7] Fetching live streams...")
    live_streams_raw = fetch_json(f"{BASE}&action=get_live_streams")
    save_json("live_streams.json", live_streams_raw)

    # Build category lookup for live
    live_cat_lookup = {c["category_id"]: c["category_name"] for c in live_cats}

    # Split live streams per category
    live_by_cat = {}
    for st in live_streams_raw:
        cat_id = str(st.get("category_id", ""))
        cat_name = live_cat_lookup.get(cat_id, "Sem Grupo")
        if cat_name not in live_by_cat:
            live_by_cat[cat_name] = []
        live_by_cat[cat_name].append({
            "n": st.get("name", ""),
            "s": str(st.get("stream_id", "")),
            "l": st.get("stream_icon", ""),
            "c": cat_name,
        })
    # Save per-category live files
    for cat_name, channels in live_by_cat.items():
        safe_name = cat_name.replace("|", "").replace("  ", " ").strip().replace(" ", "_")
        save_json(f"live_{safe_name}.json", channels)

    print(f"  Live: {len(live_streams_raw)} channels in {len(live_by_cat)} categories")

    # ---- VOD Categories (1.5KB) ----
    print("[4/7] Fetching VOD categories...")
    vod_cats = fetch_json(f"{BASE}&action=get_vod_categories")
    save_json("vod_categories.json", vod_cats)

    # ---- VOD Streams (5.5MB) — split per category ----
    print("[5/7] Fetching VOD streams...")
    vod_streams_raw = fetch_json(f"{BASE}&action=get_vod_streams")
    save_json("vod_streams.json", vod_streams_raw)

    vod_cat_lookup = {c["category_id"]: c["category_name"] for c in vod_cats}

    vod_by_cat = {}
    for st in vod_streams_raw:
        cat_id = str(st.get("category_id", ""))
        cat_name = vod_cat_lookup.get(cat_id, "Sem Grupo")
        if cat_name not in vod_by_cat:
            vod_by_cat[cat_name] = []
        vod_by_cat[cat_name].append({
            "n": st.get("name", ""),
            "s": str(st.get("stream_id", "")),
            "l": st.get("stream_icon", ""),
            "c": cat_name,
            "e": st.get("container_extension", "mp4"),
        })
    for cat_name, movies in vod_by_cat.items():
        safe_name = cat_name.replace("|", "").replace("  ", " ").strip().replace(" ", "_")
        save_json(f"vod_{safe_name}.json", movies)

    print(f"  VOD: {len(vod_streams_raw)} movies in {len(vod_by_cat)} categories")

    # ---- Series Categories (2KB) ----
    print("[6/7] Fetching series categories...")
    series_cats = fetch_json(f"{BASE}&action=get_series_categories")
    save_json("series_categories.json", series_cats)

    # ---- Series Streams (7.5MB) — split per category ----
    print("[7/7] Fetching series streams...")
    series_streams_raw = fetch_json(f"{BASE}&action=get_series")
    save_json("series_streams.json", series_streams_raw)

    series_cat_lookup = {c["category_id"]: c["category_name"] for c in series_cats}

    series_by_cat = {}
    for st in series_streams_raw:
        cat_id = str(st.get("category_id", ""))
        cat_name = series_cat_lookup.get(cat_id, "Sem Grupo")
        if cat_name not in series_by_cat:
            series_by_cat[cat_name] = []
        series_by_cat[cat_name].append({
            "n": st.get("name", ""),
            "s": str(st.get("series_id", "")),
            "l": st.get("cover", ""),
            "c": cat_name,
        })
    for cat_name, shows in series_by_cat.items():
        safe_name = cat_name.replace("|", "").replace("  ", " ").strip().replace(" ", "_")
        save_json(f"series_{safe_name}.json", shows)

    print(f"  Series: {len(series_streams_raw)} shows in {len(series_by_cat)} categories")

    # ---- Index file (tells the app what's available) ----
    index = {
        "server": SERVER,
        "username": USERNAME,
        "updated": auth.get("server_info", {}).get("time_now", ""),
        "live_categories": [
            {"id": c["category_id"], "name": c["category_name"]}
            for c in live_cats
        ],
        "live_total": len(live_streams_raw),
        "vod_categories": [
            {"id": c["category_id"], "name": c["category_name"]}
            for c in vod_cats
        ],
        "vod_total": len(vod_streams_raw),
        "series_categories": [
            {"id": c["category_id"], "name": c["category_name"]}
            for c in series_cats
        ],
        "series_total": len(series_streams_raw),
    }
    save_json("index.json", index)

    print("\nDone! All files saved to data/")


if __name__ == "__main__":
    main()