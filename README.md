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

## For Youssef — Running a new search

### Setup

Copy `.env.example` to `.env` and fill in your LinkedIn session cookie if you have one (optional — the tool works without it, just with fewer LinkedIn results):

```bash
cp .env.example .env
# edit .env and set LINKEDIN_LI_AT=your_cookie_value
```

### Run a search

```bash
source .venv/bin/activate
applier search
```

This scrapes all platforms, saves results to `results/applier.db`, and exports `results/jobs.json`.

### Push to GitHub so Hamza can see the new jobs

```bash
git add results/jobs.json
git commit -m "data: update jobs $(date +%Y-%m-%d)"
git push
```

Hamza then runs `git pull` + `applier serve` and sees the new jobs with his tracking intact.

---

## Profiles

Job search parameters live in `profiles/hamza.toml`. You can edit:
- `roles_fr` — French job titles to search
- `roles_en` — English job titles (used for international locations)
- `locations` — list of cities/countries to search in

---

## Commands

| Command | What it does |
|---|---|
| `applier search` | Run a full search, save to DB, export JSON |
| `applier serve` | Start the web UI at http://localhost:5050 |
| `applier platforms` | List supported platforms |

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
