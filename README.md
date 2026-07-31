# Lifecycle Experiment Results — Dashboard

A local/hostable results dashboard for the Lifecycle team's experiments —
separate from the Notion doc, built for pulling up on a screen in meetings.

## ⚠️ Extract the zip fully before opening

Don't double-click `index.html` straight out of the zip's preview pane —
Windows/macOS will let you *view* it, but the links to `experiments/`,
`assets/style.css`, etc. won't resolve to real files and you'll get a
"file not found" error the moment you click into an experiment.

**Right-click the zip → "Extract All" (Windows) or double-click it in
Finder (Mac) first**, so you get a real `lifecycle-dashboard` folder on
disk with `index.html`, `assets/`, and `experiments/` all sitting next
to each other. Then open `index.html` from *that* folder.

## How to view it

Once extracted, just open it: double-click `index.html`, or open it in a
browser via File → Open. Every link between pages is relative, so it
works straight off your computer with no server needed.

If your browser blocks anything when opening files directly (rare, but
some browsers restrict local file access), run a tiny local server instead:

```bash
cd lifecycle-dashboard
python3 -m http.server 8000
```

Then visit `http://localhost:8000` in your browser.

## Hosting it for the team

Since it's a plain static site (just HTML/CSS/JS, no backend), you can drop
the whole `lifecycle-dashboard` folder onto **any** static host and it'll
work as-is. The setup below assumes **GitHub Pages**, since the automation
in the next section is built around it — Netlify/Vercel would work too but
you'd wire the automation differently.

1. Create a repo on GitHub and push this folder to it:
   ```bash
   cd lifecycle-dashboard
   git init
   git add .
   git commit -m "Initial lifecycle experiment dashboard"
   git branch -M main
   touch .nojekyll
   git add .nojekyll && git commit -m "Add .nojekyll"
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git push -u origin main
   ```
2. On GitHub: **Settings → Pages → Build and deployment → Source: "Deploy
   from a branch" → Branch: `main`, folder: `/ (root)` → Save.**
3. Give it a minute — it's live at `https://<your-username>.github.io/<repo-name>/`.

Every link in the site is relative, so it works correctly at that
`/repo-name/` subpath with no edits.

**Heads up on visibility:** on GitHub's free plan, Pages sites are public
to anyone with the link (private repos can't serve Pages at all on Free).
This dashboard has real Solace campaign names, metrics, and hypotheses in
it — if that's not something you want fully public, you'd need GitHub Pro
(to host Pages from a private repo — though the *site* itself is still
open to anyone with the URL) or GitHub Enterprise Cloud (to restrict the
live site to logged-in org members only).

## Keeping it updated automatically

There's a GitHub Actions workflow (`.github/workflows/sync-and-deploy.yml`)
that runs on a schedule, pulls every **Completed** experiment from the
Notion database, updates `data.json`, rebuilds the site, and pushes the
result — so GitHub Pages picks it up with zero manual steps for the parts
it can do reliably. Here's how to turn it on, and — importantly — what it
will and won't do for you.

### One-time setup

1. **Create a Notion integration.** Go to
   [notion.so/my-integrations](https://www.notion.so/my-integrations) →
   "+ New integration" → give it a name (e.g. "Lifecycle Dashboard Sync") →
   associate it with your workspace → Save. Copy the **Internal Integration
   Secret** it gives you (starts with `ntn_` or `secret_`).
2. **Share the database with it.** Open the Lifecycle Experiments database
   in Notion → **•••** menu (top right) → **Connections** → add the
   integration you just created. Without this step, the API will return a
   404 no matter how correct the token is — it's the single most common
   thing to miss.
3. **Add the secret to GitHub.** In your repo: **Settings → Secrets and
   variables → Actions → New repository secret** → name it `NOTION_TOKEN` →
   paste the integration secret → Add secret.
4. **Enable the workflow.** It's already in `.github/workflows/` — as soon
   as it's pushed to GitHub, it'll show up under the **Actions** tab and
   start running on its schedule (default: 8:00 AM UTC daily — edit the
   `cron:` line in the workflow file to change it). You can also trigger it
   any time from **Actions → Sync Notion & Rebuild Dashboard → Run workflow**
   — handy right before a meeting.

I can't test this end-to-end from my side — I don't have network access to
`api.notion.com` from here, so the first real run will be the first time
this code actually talks to your workspace. If it errors, paste me the
error from the Actions log and I'll help debug it.

### What the automation actually does (and doesn't)

Be clear-eyed about this, because it matters for how much you trust the
site between manual passes:

**Fully automatic — the mechanical stuff:** experiment name, category,
campaign, result, hypothesis, target impact, primary metric, impact
summary, dates, and the Linear ticket link. These all live in Notion
database *properties*, which is a clean, structured lookup — the script
just copies them over. New experiments that move to "Completed" in Notion
will show up on the site automatically with all of this filled in.

**Not automatic — the rich stuff:** the "Experiment Details" narrative
(summary/type/method), the CIO/HEX reference links, the control-vs-test
metrics table, "what worked/what didn't," and screenshots. This is
everything I originally built by actually *reading* each Notion page's
body content — cohort tables, dated notes, screenshots, free-form
writeups — and using judgment to turn it into clean structured fields.
That's not a property lookup; it's reading comprehension, and I don't
think it's honest to fake-automate it with a script that would just be
guessing. A script that tried to regex a "final" metrics table out of a
page with five different dated re-reads of the same test would get it
wrong more often than not.

**How the gap is handled:** any experiment the sync script adds or
meaningfully changes gets `"needs_review": true` in `data.json`. On the
site, that shows up as a small dot next to the name in the table and an
orange **"Needs review"** banner at the top of its detail page — so it's
never silently incomplete, it's visibly a placeholder until someone (or I,
if you point me at the Notion page and ask) fills in the rest. Clear the
flag by setting `"needs_review": false` once you're happy with the page.

**If you want the rich stuff automated too:** that's possible, but it's a
different, bigger piece of work — it'd mean adding a step that sends each
new Notion page's content to an LLM (e.g. the Claude API) with instructions
to extract the same structured fields I did by hand, which means an API
key, a per-run cost, and a prompt worth iterating on. I'd suggest treating
that as a deliberate follow-up rather than something to bolt on silently —
happy to build it if you want it, just say so.

## What's in here

```
lifecycle-dashboard/
├── index.html              ← the main dashboard (table of all experiments)
├── data.json                ← ALL the experiment data lives here
├── generate.py               ← rebuilds index.html + experiments/*.html from data.json
├── scripts/
│   └── sync_notion.py        ← pulls Completed experiments from Notion into data.json
├── .github/workflows/
│   └── sync-and-deploy.yml   ← runs the sync + rebuild on a schedule (see "Keeping it updated")
├── assets/
│   ├── style.css
│   ├── app.js                ← filtering/sorting on the index table
│   └── screenshots.js        ← screenshot upload/gallery storage (see below)
└── experiments/
    └── <experiment-slug>.html   ← one page per experiment
```

## Category colors

Each category has its own color, used consistently in the index table,
the filter chips, and the colored chip in each experiment's breadcrumb:

| Category | Color |
|---|---|
| Early Lifecycle | steel blue |
| Appointment | deep teal |
| Patients | plum |
| Advocate | sienna |
| Content | slate |
| Operations | olive |

To change a color, edit the `.cat-*` rules near the top of `assets/style.css`
— search for `cat-early-lifecycle` to find the block.

## Screenshots on each experiment page

Every experiment page now has a **Screenshots & Creative** section with:

- **Variant comparison** — two upload slots (labeled with that experiment's
  actual variant names, e.g. "A — 21-day (CTRL)" vs "B — 10-day (TEST)")
  for viewing the two creative/flow versions side by side.
- **Additional screenshots** — an open gallery for anything else: HEX
  charts, CIO exports, creative previews, whatever. Each one gets a
  source tag (HEX / CIO / Creative / Figma / Other) and an optional caption.

**Important — read before relying on this in a meeting:** screenshots are
stored in the browser's IndexedDB, not on a server. That means:
- They persist across reloads *in that same browser, on that same device*.
- They will **not** appear for a teammate opening the same URL on their
  own laptop, and they will **not** survive if that browser's site data
  gets cleared.
- Each experiment page has **Export screenshots (.json)** / **Import
  screenshots (.json)** buttons — use these to move a set of screenshots
  from one browser/computer to another (e.g., export on your laptop,
  import on the conference-room machine before a meeting).

If you want screenshots that are genuinely shared for everyone who opens
the dashboard, the honest fix is a small backend (or just committing the
images into the repo and referencing them directly in `data.json` the way
`creative_copy` text blocks work now) — this local-storage version is the
zero-backend, works-immediately option.

## Adding a new experiment

1. Open `data.json`.
2. Copy an existing experiment object and edit it. Fields:
   - `slug` — used for the filename, lowercase-with-dashes, must be unique
   - `name`, `category`, `campaign`, `result` (Positive/Negative/Neutral/Mixed/Inconclusive)
   - `start_date` / `end_date` — `YYYY-MM-DD`
   - `hypothesis`, `target_impact`, `primary_metric`, `impact_summary`
   - `experiment_summary`, `experiment_type`, `experiment_method`,
     `secondary_metrics`, `experiment_event`, `experiment_id` — the
     "Experiment Details" fields, matching Notion. Leave any of these as
     `""` if not documented; empty ones just won't render.
   - `cio_link`, `hex_link`, `figma_link` — shown in Reference Links
     alongside `linear_ticket`. Leave `""` to omit a row.
   - `variant_a_label` / `variant_b_label` — labels shown on the two
     screenshot-comparison upload slots (e.g. `"A — 21-day (CTRL)"`).
   - `creative_copy` — optional array of `{"label": "...", "text": "..."}`
     for showing actual tested copy (SMS/email text) side by side. Leave
     as `[]` if there's nothing to show.
   - `additional_notes` — array of `{"author": "...", "date": "...", "note": "..."}`.
     `author`/`date` can be `""` if unknown.
   - `metrics` — array of control-vs-test rows for the results table. Each one:
     ```json
     {
       "label": "Attendance rate",
       "control_name": "Holdout", "control_value": "58.3%", "control_raw": "334 / 573",
       "test_name": "Reminder", "test_value": "62.6%", "test_raw": "333 / 532",
       "lift": "+7.4% relative", "sig": "Not stat sig at 95%"
     }
     ```
     Start `lift` with `+` or `-` to get the green/red arrow; anything else renders neutral.
   - `what_worked`, `what_didnt`, `follow_up` — arrays of short bullet strings
   - `owner_team`, `linear_ticket`, `notion_url`
   - `notion_page_id` — the raw Notion page ID (no dashes), used by the sync
     script to match this entry to its Notion page and avoid creating a
     duplicate. If you're adding an experiment by hand that also exists in
     Notion, grab this from the end of its Notion URL; if it's not in
     Notion at all, leave it out.
   - `needs_review` — `true`/`false`. Set `true` to show the orange banner
     and index-table dot; the sync script sets this automatically for
     anything new or changed that hasn't had a full pass yet.
3. Run `python3 generate.py`.
4. Refresh the browser. Done.

Nothing needs to be deleted or reordered — the generator always rebuilds
everything from scratch, sorted by end date (most recent first).

## Adding real screenshots

Notion's image links are signed and expire quickly, so screenshots aren't
pulled in automatically. To add one:

1. Save the image into `assets/screenshots/<experiment-slug>/`
2. Add an `<img>` tag pointing to it inside that experiment's block in
   `generate.py` (search for `screenshot-note` to find the spot), or just
   drop `<img src="../assets/screenshots/your-slug/file.png">` directly
   into the generated HTML if you don't want to touch the generator.

## Notes on data accuracy

- All 20 experiments here are pulled from the "Completed" view of the
  Lifecycle Experiments Notion database as of **July 10, 2026**.
- One flag: **Advocate June Toggle Campaign** has a strong, well-documented
  positive result on its own Notion page, but the database's Result and
  Impact Summary *properties* are still blank. It's included here with the
  real numbers, but worth fixing in Notion so it doesn't get missed by
  anyone only skimming the database view.
- Owner names aren't shown — Notion's API only exposed owner user IDs, not
  display names, so `owner_team` shows the general pod instead of a person.
  Edit `data.json` directly if you want to add real names.
