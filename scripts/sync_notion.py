#!/usr/bin/env python3
"""
Sync completed Lifecycle experiments from Notion into data.json.

What this does automatically (reliable, mechanical):
    - Finds every page in the Lifecycle Experiments database with
      Status = Completed.
    - For pages already in data.json (matched by notion_page_id): updates
      the "surface" fields that live in Notion's database PROPERTIES —
      category, campaign, result, dates, hypothesis, target impact,
      primary metric, impact summary, linear ticket. If any of those
      changed since the last sync, marks the entry needs_review=true.
    - For pages NOT yet in data.json: creates a new stub entry with those
      same surface fields, needs_review=true, and empty rich-detail fields
      (experiment_summary, metrics, what_worked, etc.) — see the "What
      this does NOT do" note below.
    - Never deletes existing entries, even if a page's Status changes away
      from Completed later — remove those by hand if that ever happens.

What this does NOT do (on purpose):
    - It does not read each Notion page's BODY content (the free-form
      "Experiment Details" writeup, metrics tables, screenshots, creative
      copy, what-worked/what-didn't bullets). That content isn't
      structured data — turning it into the dashboard's rich fields is a
      reading-comprehension task, not a property lookup. New/changed
      experiments show up on the site automatically with accurate surface
      data and an obvious "Needs review" banner; a human (or an
      AI assistant, pointed at the Notion page) still needs to do a pass
      to fill in the rest. This keeps the automation honest instead of
      silently guessing.

Setup (see README.md for the full walkthrough):
    1. Create a Notion internal integration at notion.so/my-integrations,
       copy its "Internal Integration Secret".
    2. Share the Lifecycle Experiments database with that integration
       (••• menu on the database → Connections → add the integration).
    3. Set that secret as the NOTION_TOKEN environment variable (in
       GitHub Actions: a repository secret of the same name).
    4. Run: python3 scripts/sync_notion.py
    5. Then: python3 generate.py
       (the GitHub Actions workflow does both steps for you on a schedule)
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data.json")

NOTION_VERSION = "2025-09-03"
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "").strip()

# The Lifecycle Experiments database has a single data source — this is
# its ID (from the collection:// URL Notion's own tools show). If this
# database is ever recreated or a second data source is added, get the
# right ID from Notion's "Retrieve a database" endpoint and update this.
DATA_SOURCE_ID = "3589601d-59a9-806c-a045-000b568d2e4a"

API_ROOT = "https://api.notion.com/v1"


def notion_request(method, path, body=None):
    if not NOTION_TOKEN:
        print("ERROR: NOTION_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    url = f"{API_ROOT}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {NOTION_TOKEN}")
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"Notion API error {e.code} on {method} {path}:\n{err_body}", file=sys.stderr)
        raise


def fetch_completed_pages():
    """Query the data source for every page with Status = Completed, paginating as needed."""
    pages = []
    cursor = None
    while True:
        body = {
            "filter": {"property": "Status", "status": {"equals": "Completed"}},
            "page_size": 100,
        }
        if cursor:
            body["start_cursor"] = cursor
        result = notion_request("POST", f"/data_sources/{DATA_SOURCE_ID}/query", body)
        pages.extend(result.get("results", []))
        if result.get("has_more"):
            cursor = result.get("next_cursor")
            time.sleep(0.35)  # stay comfortably under Notion's ~3 req/s limit
        else:
            break
    return pages


def plain_text(prop):
    """Flatten a title/rich_text property value down to plain text."""
    if not prop:
        return ""
    segments = prop.get("title") or prop.get("rich_text") or []
    return "".join(s.get("plain_text", "") for s in segments)


def first_link(prop):
    """Pull a URL out of a rich_text property — prefer an applied link (href),
    fall back to the plain text if it already looks like a URL."""
    segments = (prop or {}).get("rich_text") or []
    for s in segments:
        if s.get("href"):
            return s["href"]
    text = plain_text(prop).strip()
    if text.startswith("http"):
        return text
    return "" if text in ("", "N/A", "n/a") else text


def select_name(prop):
    val = (prop or {}).get("select")
    return val.get("name", "") if val else ""


def status_name(prop):
    val = (prop or {}).get("status")
    return val.get("name", "") if val else ""


def date_value(prop, which="start"):
    val = (prop or {}).get("date")
    return (val or {}).get(which) or ""


def owner_team_guess(prop):
    """People property → best-effort display name. Notion only returns a
    person's name to integrations with the 'Read user information'
    capability enabled; otherwise this falls back to the raw user id."""
    people = (prop or {}).get("people") or []
    if not people:
        return ""
    names = [p.get("name") or p.get("id", "") for p in people]
    return ", ".join(names)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def notion_url_for(page_id):
    return f"https://www.notion.so/{page_id.replace('-', '')}"


def page_to_surface_fields(page):
    props = page.get("properties", {})
    return {
        "name": plain_text(props.get("Experiment Name")),
        "category": select_name(props.get("Category")),
        "campaign": plain_text(props.get("Campaign")),
        "result": select_name(props.get("Result")) or "Inconclusive",
        "start_date": date_value(props.get("Start Date"), "start"),
        "end_date": date_value(props.get("End Date"), "start"),
        "hypothesis": plain_text(props.get("Hypothesis")),
        "target_impact": plain_text(props.get("Target Impact")),
        "primary_metric": plain_text(props.get("Primary Metric")),
        "impact_summary": plain_text(props.get("Impact Summary")),
        "linear_ticket": first_link(props.get("Linear Ticket")),
        "owner_team": owner_team_guess(props.get("Owner")),
        "notion_url": notion_url_for(page["id"]),
        "notion_page_id": page["id"],
    }


SURFACE_FIELDS = [
    "name", "category", "campaign", "result", "start_date", "end_date",
    "hypothesis", "target_impact", "primary_metric", "impact_summary",
    "linear_ticket",
]

RICH_FIELD_DEFAULTS = {
    "experiment_summary": "",
    "experiment_type": "",
    "experiment_method": "",
    "secondary_metrics": "",
    "experiment_event": "",
    "experiment_id": "",
    "cio_link": "",
    "hex_link": "",
    "figma_link": "",
    "variant_a_label": "Variant A",
    "variant_b_label": "Variant B",
    "creative_copy": [],
    "additional_notes": [],
    "metrics": [],
    "what_worked": [],
    "what_didnt": [],
    "follow_up": [],
}


def unique_slug(base, taken):
    slug = base
    i = 2
    while slug in taken:
        slug = f"{base}-{i}"
        i += 1
    return slug


def sync():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    experiments = data["experiments"]
    by_page_id = {e.get("notion_page_id"): e for e in experiments if e.get("notion_page_id")}
    existing_slugs = {e["slug"] for e in experiments}

    pages = fetch_completed_pages()
    print(f"Fetched {len(pages)} Completed page(s) from Notion.")

    new_count = 0
    updated_count = 0

    for page in pages:
        fields = page_to_surface_fields(page)
        page_id = fields["notion_page_id"]
        existing = by_page_id.get(page_id)

        if existing:
            changed = any(existing.get(k, "") != fields.get(k, "") for k in SURFACE_FIELDS)
            for k in SURFACE_FIELDS + ["owner_team", "notion_url"]:
                existing[k] = fields[k]
            if changed:
                existing["needs_review"] = True
                updated_count += 1
        else:
            slug = unique_slug(slugify(fields["name"]) or f"exp-{page_id[:8]}", existing_slugs)
            existing_slugs.add(slug)
            entry = {"slug": slug, **fields}
            for k in SURFACE_FIELDS:
                entry.setdefault(k, fields.get(k, ""))
            entry.update({k: v for k, v in RICH_FIELD_DEFAULTS.items()})
            entry["needs_review"] = True
            experiments.append(entry)
            by_page_id[page_id] = entry
            new_count += 1

    data["experiments"] = experiments
    data["last_synced"] = datetime.now(timezone.utc).strftime("%B %-d, %Y")
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"New experiments added: {new_count}")
    print(f"Existing experiments updated: {updated_count}")
    print(f"Total experiments: {len(experiments)}")
    print(f"last_synced stamped: {data['last_synced']}")


if __name__ == "__main__":
    sync()
