#!/usr/bin/env python3
"""
Lifecycle Experiment Results — static site generator.

Usage:
    python3 generate.py

Reads data.json and (re)builds index.html plus one page per experiment
in experiments/. Re-run this any time data.json changes — it's safe to
run repeatedly, it always overwrites the generated HTML.
"""
import json
import html
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(ROOT, "data.json"), encoding="utf-8") as f:
    DATA = json.load(f)

EXPERIMENTS = DATA["experiments"]
LAST_SYNCED = DATA.get("last_synced", "")
SOURCE_DB = DATA.get("source_db", "#")
RESULTS_DOC = DATA.get("results_doc", "#")

RESULT_CLASS = {
    "Positive": "positive",
    "Negative": "negative",
    "Neutral": "neutral",
    "Mixed": "mixed",
    "Inconclusive": "inconclusive",
}

CATEGORIES = ["Early Lifecycle", "Appointment", "Patients", "Advocate", "Content", "Operations"]
RESULTS = ["Positive", "Negative", "Neutral", "Mixed", "Inconclusive"]
SOURCE_TAGS = ["HEX", "CIO", "Creative", "Figma", "Other"]


def esc(s):
    return html.escape(s or "", quote=True)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def cat_class(category):
    return f"cat-chip cat-{slugify(category)}"


HEAD = """<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600;700&family=Poppins:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{css_path}">
"""


def render_tag(result):
    cls = RESULT_CLASS.get(result, "inconclusive")
    label = result if result else "Unrecorded"
    return f'<span class="tag {cls}">{esc(label)}</span>'


def render_stamp(result):
    cls = RESULT_CLASS.get(result, "inconclusive")
    label = (result or "Unrecorded").upper()
    return f'<span class="stamp {cls}">{esc(label)}</span>'


def fmt_date(d):
    return d if d else "—"


def render_metric_row(m):
    lift = m.get("lift", "")
    direction = "flat"
    if lift.startswith("+"):
        direction = "up"
    elif lift.startswith("-"):
        direction = "down"
    arrow = {"up": "▲", "down": "▼", "flat": "◆"}[direction]
    control_raw = f'<span class="mraw">{esc(m.get("control_raw",""))}</span>' if m.get("control_raw") else ""
    test_raw = f'<span class="mraw">{esc(m.get("test_raw",""))}</span>' if m.get("test_raw") else ""
    return f"""
      <tr>
        <td>{esc(m.get('label',''))}</td>
        <td>{esc(m.get('control_name',''))}<br>{control_raw}</td>
        <td class="mval">{esc(m.get('control_value',''))}</td>
        <td>{esc(m.get('test_name',''))}<br>{test_raw}</td>
        <td class="mval">{esc(m.get('test_value',''))}</td>
        <td>
          <span class="delta {direction}">{arrow} {esc(lift)}</span>
          <span class="sig-note">{esc(m.get('sig',''))}</span>
        </td>
      </tr>"""


def render_list(items, empty_text):
    if not items:
        return f'<ul class="plain empty"><li>{esc(empty_text)}</li></ul>'
    lis = "\n".join(f"<li>{esc(i)}</li>" for i in items)
    return f'<ul class="plain">{lis}</ul>'


def render_followup(items):
    if not items:
        return '<p class="target-impact">No follow-up actions logged yet.</p>'
    lis = "\n".join(f"<li>{esc(i)}</li>" for i in items)
    return f'<ol class="followup-list">{lis}</ol>'


def render_details_grid(e):
    rows = []
    field_map = [
        ("Experiment type", e.get("experiment_type", "")),
        ("Method", e.get("experiment_method", "")),
        ("Secondary metrics", e.get("secondary_metrics", "")),
        ("Experiment event", e.get("experiment_event", "")),
        ("Experiment ID", e.get("experiment_id", "")),
    ]
    for label, value in field_map:
        if value:
            rows.append(f'<div class="dg-item"><span class="dg-label">{esc(label)}</span><span class="dg-value">{esc(value)}</span></div>')

    summary_html = ""
    if e.get("experiment_summary"):
        summary_html = f'<p class="summary-text">{esc(e["experiment_summary"])}</p>'

    if not summary_html and not rows:
        return '<p class="section-empty-note">No additional experiment detail was logged on the Notion page beyond the hypothesis and results below.</p>'

    grid_html = f'<div class="details-grid">{"".join(rows)}</div>' if rows else ""
    return summary_html + grid_html


def render_reference_links(e):
    rows = []
    if e.get("linear_ticket") and e["linear_ticket"] not in ("N/A", ""):
        rows.append(('Linear ticket', e["linear_ticket"]))
    if e.get("cio_link"):
        rows.append(('CIO experiment', e["cio_link"]))
    if e.get("hex_link"):
        rows.append(('HEX dashboard', e["hex_link"]))
    if e.get("figma_link"):
        rows.append(('Figma', e["figma_link"]))
    if not rows:
        return '<p class="section-empty-note">No reference links logged for this experiment.</p>'
    trs = "\n".join(
        f'<tr><td>{esc(label)}</td><td><a href="{esc(url)}" target="_blank" rel="noopener">{esc(url)} ↗</a></td></tr>'
        for label, url in rows
    )
    return f'<table class="ref-links-table"><tbody>{trs}</tbody></table>'


def render_creative_copy(e):
    blocks = e.get("creative_copy") or []
    if not blocks:
        return ""
    cards = "".join(
        f'<div class="creative-copy-block"><span class="cc-label">{esc(b.get("label",""))}</span>'
        f'<div class="cc-text">{esc(b.get("text",""))}</div></div>'
        for b in blocks
    )
    return f"""
    <div class="shot-subhead" style="margin-top:26px;">Creative copy tested</div>
    <div class="creative-copy-grid">{cards}</div>"""


def render_notes(e):
    notes = e.get("additional_notes") or []
    if not notes:
        return '<p class="section-empty-note">No additional notes logged.</p>'
    lis = []
    for n in notes:
        byline_parts = [p for p in [n.get("author", ""), n.get("date", "")] if p]
        byline = " — ".join(byline_parts)
        byline_html = f'<span class="note-byline">{esc(byline)}</span>' if byline else ""
        lis.append(f'<li>{byline_html}{esc(n.get("note",""))}</li>')
    return f'<ul class="notes-list">{"".join(lis)}</ul>'


def render_screenshot_section(e):
    source_options = "".join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in SOURCE_TAGS)
    return f"""
    <div class="shot-subhead">Variant comparison — side by side</div>
    <div class="shot-compare">
      <div class="shot-slot" id="shot-slot-a"><span class="shot-label">{esc(e.get('variant_a_label') or 'Variant A')}</span></div>
      <div class="shot-slot" id="shot-slot-b"><span class="shot-label">{esc(e.get('variant_b_label') or 'Variant B')}</span></div>
    </div>

    <div class="shot-subhead">Additional screenshots — HEX, CIO, creative, anything else</div>
    <div class="shot-gallery" id="shot-gallery"></div>
    <button class="btn-add-shot" id="add-shot-btn" type="button">+ Add screenshot</button>
    <div class="add-shot-form" id="add-shot-form">
      <label class="file-label" id="add-shot-file-label">Choose file…
        <input type="file" accept="image/*" id="add-shot-file" hidden>
      </label>
      <select id="add-shot-source">{source_options}</select>
      <input type="text" id="add-shot-caption" placeholder="Caption (optional) — e.g. &quot;HEX funnel re-entry, 6/10 read&quot;">
      <button id="add-shot-save" type="button">Save</button>
      <button id="add-shot-cancel" type="button">Cancel</button>
    </div>

    <p class="shot-note">Screenshots are stored locally in this browser (IndexedDB) — no backend, so this works straight from a static site. That also means they're only visible on this device/browser, not synced to teammates opening the same page elsewhere. Use Export/Import to move a set of screenshots to another machine.</p>
    <div class="shot-io-row">
      <button id="export-shots-btn" type="button">Export screenshots (.json)</button>
      <label class="import-label">Import screenshots (.json)<input type="file" accept="application/json" id="import-shots-input" hidden></label>
    </div>"""


def render_needs_review_banner(e):
    if not e.get("needs_review"):
        return ""
    note = e.get("review_note")
    if note:
        return f"""
    <div class="needs-review-banner">
      <strong>Flagged for follow-up</strong> — {esc(note)}
    </div>"""
    return """
    <div class="needs-review-banner">
      <strong>Needs review</strong> — this experiment was pulled in automatically from Notion (name, hypothesis, result, impact summary). The Experiment Details, metrics breakdown, and learnings below haven't had a human/AI pass yet — treat this page as a placeholder until someone fills those in.
    </div>"""


def build_index():
    total = len(EXPERIMENTS)
    pos = sum(1 for e in EXPERIMENTS if e["result"] == "Positive")
    neg = sum(1 for e in EXPERIMENTS if e["result"] == "Negative")
    neutral = sum(1 for e in EXPERIMENTS if e["result"] in ("Neutral", "Mixed", "Inconclusive"))
    learned = sum(1 for e in EXPERIMENTS if e.get("reached_significance"))
    learn_rate = round((learned / total) * 100) if total else 0
    cats_present = sorted(set(e["category"] for e in EXPERIMENTS))
    win_rate = round((pos / total) * 100) if total else 0

    cat_chips = '<span class="chip active" data-cat="All">All categories</span>' + "".join(
        f'<span class="chip cat-{slugify(c)}" data-cat="{esc(c)}">{esc(c)}</span>' for c in CATEGORIES if c in cats_present
    )
    res_chips = '<span class="chip active" data-res="All">All results</span>' + "".join(
        f'<span class="chip" data-res="{esc(r)}">{esc(r)}</span>' for r in RESULTS
        if any(e["result"] == r for e in EXPERIMENTS)
    )

    rows = []
    sorted_exps = sorted(EXPERIMENTS, key=lambda e: e.get("end_date", ""), reverse=True)
    for e in sorted_exps:
        search_blob = " ".join([
            e["name"], e["category"], e["campaign"], e.get("hypothesis", ""), e.get("impact_summary", "")
        ]).lower()
        rows.append(f"""
        <tr data-cat="{esc(e['category'])}" data-res="{esc(e['result'])}"
            data-search="{esc(search_blob)}" data-href="experiments/{e['slug']}.html"
            data-name="{esc(e['name'])}" data-enddate="{esc(e.get('end_date',''))}">
          <td class="col-name">{esc(e['name'])}{' <span class=\"review-dot\" title=\"Flagged — see the page for why\"></span>' if e.get('needs_review') else ''}<span class="campaign">{esc(e['campaign'])}</span></td>
          <td><span class="{cat_class(e['category'])}">{esc(e['category'])}</span></td>
          <td>{render_tag(e['result'])}</td>
          <td class="col-metric">{esc(e['primary_metric'])}</td>
          <td class="col-summary">{esc(e['impact_summary'][:160])}{'…' if len(e['impact_summary'])>160 else ''}</td>
          <td class="col-date">{fmt_date(e.get('end_date'))}</td>
        </tr>""")

    html_out = f"""<!doctype html>
<html lang="en">
<head>
<title>Lifecycle Experiment Results</title>
{HEAD.format(css_path="assets/style.css")}
</head>
<body>
<div class="topbar">
  <div class="wrap topbar-inner">
    <div class="brand">Lifecycle Experiment Results<span class="sub">Solace Health · Growth &amp; Lifecycle</span></div>
    <div class="topnav">
      <a href="{esc(SOURCE_DB)}" target="_blank" rel="noopener">Source database ↗</a>
      <a href="{esc(RESULTS_DOC)}" target="_blank" rel="noopener">Notion writeup ↗</a>
    </div>
  </div>
  <div class="wrap sync-note">Last synced {esc(LAST_SYNCED)} · {total} completed experiments</div>
</div>

<div class="wrap">
  <div class="stat-strip">
    <div class="stat-cell"><div class="stat-num">{total}</div><div class="stat-label">Completed experiments</div></div>
    <div class="stat-cell"><div class="stat-num pos">{pos}</div><div class="stat-label">Positive results</div></div>
    <div class="stat-cell"><div class="stat-num neg">{neg}</div><div class="stat-label">Negative results</div></div>
    <div class="stat-cell"><div class="stat-num">{neutral}</div><div class="stat-label">Neutral / mixed / inconclusive</div></div>
    <div class="stat-cell"><div class="stat-num">{win_rate}%</div><div class="stat-label">Win rate</div></div>
    <div class="stat-cell learnings-cell"><div class="stat-num learn">{learn_rate}%</div><div class="stat-label">Leah Rate <span class="stat-sublabel">reached significance, + or \u2212 \u2014 only a flat/inconclusive result taught us nothing</span></div></div>
  </div>

  <div class="filters">
    <label>Category</label>
    <div class="chip-group">{cat_chips}</div>
    <label style="margin-left:14px;">Result</label>
    <div class="chip-group">{res_chips}</div>
    <input id="search-input" type="text" placeholder="Search experiments…" style="margin-left:auto;">
  </div>

  <div class="table-wrap">
    <table class="exp-table">
      <thead>
        <tr>
          <th data-sort="name">Experiment</th>
          <th>Category</th>
          <th>Result</th>
          <th>Primary metric</th>
          <th>Key finding</th>
          <th data-sort="enddate">Ended</th>
        </tr>
      </thead>
      <tbody id="exp-tbody">
        {''.join(rows)}
      </tbody>
    </table>
    <div id="empty-state" class="empty-state" style="display:none;">No experiments match these filters.</div>
  </div>
</div>

<footer class="site-footer">Click any row to open the full experiment report · Generated from the Lifecycle Experiments Notion database · Re-run generate.py after editing data.json</footer>

<script src="assets/app.js"></script>
</body>
</html>
"""
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_out)


def build_detail(e, prev_e, next_e):
    metrics_rows = "".join(render_metric_row(m) for m in e.get("metrics", []))
    if e.get("metrics"):
        metrics_block = f"""
    <table class="metric-table">
      <thead>
        <tr>
          <th>Metric</th>
          <th>Control</th>
          <th>Control value</th>
          <th>Test</th>
          <th>Test value</th>
          <th>Lift / significance</th>
        </tr>
      </thead>
      <tbody>{metrics_rows}</tbody>
    </table>"""
    else:
        metrics_block = '<p class="section-empty-note">No baseline-vs-test breakdown was logged for this experiment — see impact summary above.</p>'

    target_impact_html = ""
    if e.get("target_impact"):
        target_impact_html = f'<div class="target-impact"><strong>Target impact:</strong> {esc(e["target_impact"])}</div>'

    prev_link = f'<a href="{prev_e["slug"]}.html">← {esc(prev_e["name"])}</a>' if prev_e else '<span class="disabled">← Start of list</span>'
    next_link = f'<a href="{next_e["slug"]}.html">{esc(next_e["name"])} →</a>' if next_e else '<span class="disabled">End of list →</span>'

    html_out = f"""<!doctype html>
<html lang="en">
<head>
<title>{esc(e['name'])} — Lifecycle Experiment Results</title>
{HEAD.format(css_path="../assets/style.css")}
</head>
<body>
<div class="topbar">
  <div class="wrap topbar-inner">
    <div class="brand">Lifecycle Experiment Results<span class="sub">Solace Health · Growth &amp; Lifecycle</span></div>
    <div class="topnav"><a href="../index.html">← All experiments</a></div>
  </div>
</div>

<div class="wrap">
  <div class="detail-header">
    <div class="detail-breadcrumb">
      <span class="{cat_class(e['category'])}">{esc(e['category'])}</span> · {esc(e['campaign'])}
    </div>
    <div class="detail-title-row">
      <div>
        <h1 class="detail-title">{esc(e['name'])}</h1>
        <div class="detail-meta">
          <span><strong>Owner:</strong> {esc(e.get('owner_team','—'))}</span>
          <span><strong>Ran:</strong> {fmt_date(e.get('start_date'))} → {fmt_date(e.get('end_date'))}</span>
          <span><strong>Primary metric:</strong> {esc(e.get('primary_metric',''))}</span>
        </div>
      </div>
      {render_stamp(e['result'])}
    </div>
  </div>
  {render_needs_review_banner(e)}

  <div class="section">
    <h2>Hypothesis</h2>
    <div class="hypothesis-block">{esc(e.get('hypothesis') or 'Not recorded.')}</div>
    {target_impact_html}
  </div>

  <div class="section">
    <h2>Experiment Details</h2>
    {render_details_grid(e)}
  </div>

  <div class="section">
    <h2>Reference Links</h2>
    {render_reference_links(e)}
  </div>

  <div class="section">
    <h2>Screenshots &amp; Creative</h2>
    {render_creative_copy(e)}
    {render_screenshot_section(e)}
  </div>

  <div class="section">
    <h2>Results — control vs. test</h2>
    {metrics_block}
  </div>

  <div class="section">
    <h2>Impact summary</h2>
    <p class="impact-text">{esc(e.get('impact_summary') or 'No impact summary recorded yet.')}</p>
  </div>

  <div class="section">
    <h2>Learnings</h2>
    <div class="two-col">
      <div class="list-block worked">
        <h3>What worked</h3>
        {render_list(e.get('what_worked'), 'Nothing notable worked here.')}
      </div>
      <div class="list-block didnt">
        <h3>What didn't</h3>
        {render_list(e.get('what_didnt'), 'No notable misses.')}
      </div>
    </div>
  </div>

  <div class="section">
    <h2>Follow-up actions</h2>
    {render_followup(e.get('follow_up'))}
  </div>

  <div class="section" style="border-bottom:none;">
    <h2>Additional notes</h2>
    {render_notes(e)}
    <p class="screenshot-note" style="margin-top:18px;"><a href="{esc(e.get('notion_url','#'))}" target="_blank" rel="noopener">Open the full Notion page ↗</a> for the raw HEX/CIO exports and complete history.</p>
  </div>

  <div class="detail-nav">
    <div>{prev_link}</div>
    <div class="center-link"><a href="../index.html">All experiments</a></div>
    <div>{next_link}</div>
  </div>
</div>

<script src="../assets/screenshots.js"></script>
<script>
  ScreenshotUI.init({{
    slug: {json.dumps(e['slug'])},
    variantALabel: {json.dumps(e.get('variant_a_label') or 'Variant A')},
    variantBLabel: {json.dumps(e.get('variant_b_label') or 'Variant B')}
  }});
</script>
</body>
</html>
"""
    out_path = os.path.join(ROOT, "experiments", f"{e['slug']}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)


def main():
    os.makedirs(os.path.join(ROOT, "experiments"), exist_ok=True)
    build_index()
    sorted_exps = sorted(EXPERIMENTS, key=lambda e: e.get("end_date", ""), reverse=True)
    for i, e in enumerate(sorted_exps):
        prev_e = sorted_exps[i - 1] if i > 0 else None
        next_e = sorted_exps[i + 1] if i < len(sorted_exps) - 1 else None
        build_detail(e, prev_e, next_e)
    print(f"Built index.html + {len(EXPERIMENTS)} experiment pages.")


if __name__ == "__main__":
    main()
