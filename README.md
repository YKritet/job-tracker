# Job Tracker

A tool that searches for jobs across LinkedIn, France Travail and RemoteOK, and lets you track your applications in a simple web interface.

---

## What it does

- Searches multiple job platforms automatically
- Filters out **alternance/apprentissage** offers (CDI/CDD only)
- Tags each job (IT, Sales, Finance, Marketing…)
- Shows everything in a dark web interface you open in your browser
- Saves your tracking (status, notes, applied date) to a local database — nothing is ever lost

---

## For Hamza — How to use it

### First time setup

You need Python 3.11 or later. Check by opening a terminal and typing:
```
python --version
```

**1. Get the code**
```bash
git clone https://github.com/YKritet/job-tracker.git
cd job-tracker
```

**2. Create a virtual environment and install**
```bash
python -m venv .venv
source .venv/bin/activate        # on Mac/Linux
# or on Windows: .venv\Scripts\activate

pip install -e .
```

**3. Start the tracker**
```bash
applier serve
```

Your browser will open automatically at `http://localhost:5050`. The tracker loads the latest job data automatically.

> **That's it.** No account needed, no API keys, no configuration.

---

### Every time new jobs are added

When Youssef runs a new search and pushes updated data:

```bash
git pull
applier serve
```

Then click **Refresh** in the browser — new jobs appear, your existing tracking (status, notes, dates) is preserved.

---

### Tracking your applications

In the web interface you can:

| Column | What to do |
|---|---|
| **Status** | Set to *Applied*, *Interview*, *Offer*, *Rejected*, or *Ignore* |
| **Applied date** | Pick the date you sent your CV |
| **Notes** | Free text — contact name, salary, anything useful |

Everything saves automatically the moment you change it. You can close the browser and come back later — nothing is lost.

---

### Filtering and searching

- **Search bar** — type any word from the job title, company, or location
- **Platform filter** — LinkedIn, France Travail, or RemoteOK
- **Tag filter** — IT, Sales, Security, Finance, Marketing, etc.
- **Stat cards at the top** — click *Applied*, *Interview*, etc. to filter by status
- **Export CSV** button — download everything visible as a spreadsheet

---

## Running a search

### 1. Install

```bash
git clone https://github.com/YKritet/job-tracker.git
cd job-tracker
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Add API tokens (optional but recommended)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Then open `.env` and fill in what you have:

**LinkedIn (`LINKEDIN_LI_AT`)** — improves LinkedIn result quality significantly.

How to get it:
1. Log into [linkedin.com](https://linkedin.com) in your browser
2. Open DevTools (F12) → **Application** tab → **Cookies** → `linkedin.com`
3. Find the cookie named `li_at` and copy its value
4. Paste it into `.env`:
   ```
   LINKEDIN_LI_AT=AQEDATxxxxxxxxxxxxxxxx...
   ```

> The tool works without this cookie — you just get fewer LinkedIn results. France Travail and RemoteOK need no tokens.

**France Travail** — no token needed, uses their public API.

**RemoteOK** — no token needed, uses their public API.

---

### 3. Generate a search profile from your CV

Drop your CV PDF (and optionally your motivation letter) in `assets/` — these are gitignored and never committed.

```bash
# minimal
applier parse-cv --cv assets/cv.pdf

# with motivation letter (improves category detection)
applier parse-cv --cv assets/cv.pdf --letter assets/letter.pdf
```

This reads the PDFs, detects what kind of roles match your profile, and writes `profiles/auto.toml`.

**Review and edit `profiles/auto.toml`** before searching — the detected roles are a starting point, not a final list. Trim or add role queries under `roles_fr` and `roles_en` to match what you actually want.

---

### 4. Run a search

```bash
applier search --profile profiles/auto.toml
```

Or use the default Hamza profile:

```bash
applier search
```

This scrapes all platforms, saves results to `results/applier.db`, and exports `results/jobs.json`.

### 5. Push results so others can see new jobs

```bash
git add results/jobs.json
git commit -m "data: update jobs $(date +%Y-%m-%d)"
git push
```

Others then run `git pull` + `applier serve` and see the new jobs with their tracking intact.

---

## Profiles

Search parameters live in `profiles/*.toml`. You can:
- Generate one automatically: `applier parse-cv --cv assets/cv.pdf`
- Or copy `profiles/hamza.toml` and edit manually

Key fields:
- `roles_fr` — French job titles to search (used for FR locations)
- `roles_en` — English job titles (used for international locations)
- `locations` — list of cities/countries to search in

---

## Commands

| Command | What it does |
|---|---|
| `applier parse-cv` | Parse a CV PDF and generate a search profile |
| `applier search` | Run a full search, save to DB, export JSON |
| `applier serve` | Start the web UI at http://localhost:5050 |
| `applier platforms` | List supported platforms |

### Options for `applier parse-cv`

| Option | Default | Description |
|---|---|---|
| `--cv` | `assets/cv.pdf` | Path to CV PDF |
| `--letter` | — | Path to motivation letter PDF (optional) |
| `--output` | `profiles/auto.toml` | Where to write the generated profile |
| `--name` | — | Override the detected candidate name |

### Options for `applier search`

| Option | Default | Description |
|---|---|---|
| `--profile` | `profiles/hamza.toml` | Which profile to use |
| `--platforms` | `linkedin,francetravail,remoteok` | Which platforms to search |
| `--locations` | `all` | Which locations from the profile |
| `--count` | `25` | Max results per query |
| `--no-filter` | off | Include alternance offers |

---

## Troubleshooting

**Browser doesn't open automatically**
→ Open `http://localhost:5050` manually in your browser.

**"command not found: applier"**
→ Make sure you activated the virtual environment: `source .venv/bin/activate`

**Jobs not updating after git pull**
→ Click the **Refresh** button in the top-right of the web interface.

**Port 5050 already in use**
→ Run `applier serve --port 5051` and open `http://localhost:5051`
