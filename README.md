# Applier — Job Search CLI & Tracker

Automated job search across 19 French platforms (LinkedIn, France Travail, Indeed FR, WTTJ, HelloWork, APEC, RemoteOK, Keljob, AeroEmploi, Adecco, Manpower, Randstad, Synergie, Hays, Michael Page, Cadremploi, Malt, JobEtudiant, Side). Filters results by poste and domain, tracks applications in a local SQLite database, and monitors 100+ company career pages for changes.

---

## What it does

- Searches 19 platforms automatically (Tier 1: API/RSS · Tier 2: HTML)
- Filters out **alternance/apprentissage** offers by default (CDI/CDD only)
- Applies **profile-level exclusions** — e.g. digital marketing profile drops finance/comptabilité
- **Auto-tags** each job: category label (IT, Sales, Marketing…) + **Poste** + **Domain**
- Shows everything in a dark web UI with Poste, Domain, and Platform filter dropdowns
- Saves tracking (status, notes, applied date) to local SQLite — nothing is lost
- **Watchlist check** — monitors 100+ company career pages for content changes
- **GitHub Action** — runs daily at 08:00 UTC, commits `results/jobs.json`, sends Telegram alert

---

## For Hamza — How to use it

### First time setup

Requires Python 3.11+. Use `uv` (recommended) or `pip`.

```bash
git clone https://github.com/YKritet/job-tracker.git
cd job-tracker

# With uv (recommended)
uv sync
uv run applier serve

# Or with pip
python -m venv .venv && source .venv/bin/activate
pip install -e .
applier serve
```

Your browser opens at `http://localhost:5050`.

> **No API keys required for most platforms.** France Travail and RemoteOK work without any tokens.

---

### After Youssef pushes new results

```bash
git pull
applier serve     # then click Refresh in the browser
```

Your tracking (status, notes, dates) is preserved across updates.

---

### Tracking applications

| Column | What to do |
|---|---|
| **Status** | Set to *Applied*, *Interview*, *Offer*, *Rejected*, or *Ignore* |
| **Applied date** | Pick the date you sent your CV |
| **Notes** | Contact name, salary, anything useful |

Saves automatically on every change.

---

### Filtering jobs in the UI

- **Search bar** — title, company, location
- **Platform** — LinkedIn, FranceTravail, Indeed, WTTJ, RemoteOK, HelloWork, APEC
- **Poste** — livreur, conducteur, ouvrier, stockiste, vendeur, it support, marketer, gestion, ingénieur, facteur, technicien, opérateur, serrurier, testeur
- **Domain** — logistique, transport, grande distribution, btp, industrie, agroalimentaire, santé, nettoyage, télécom, it, événementiel, retail, aéroport, imprimerie, immobilier
- **Tag** — IT, Sales, Security, Finance, Marketing, etc.
- **Skills** — CACES (any R-number), permis (any class), habilitation élec., HACCP, SST, AIPR, ADR, ISO 9001, Excel, SAP, WMS, Python, SQL, anglais — detected dynamically from job text, hover a chip for the full description
- **Stat cards** — click Applied, Interview, etc. to filter by status
- **Export CSV** — download everything visible (Skills column included)

---

## Running a search

### 1. Optional: add API tokens

Copy `.env.example` to `.env` and fill in what you have:

```bash
cp .env.example .env
```

| Token | Where to get it | Effect |
|---|---|---|
| `LINKEDIN_LI_AT` | LinkedIn DevTools → Cookies → `li_at` | More LinkedIn results |
| `FRANCETRAVAIL_CLIENT_ID` | pole-emploi.io API keys | FR job listings |
| `FRANCETRAVAIL_CLIENT_SECRET` | pole-emploi.io | FR job listings |

Everything works without tokens — you just get fewer results on authenticated platforms.

### 2. Generate a profile from your CV

```bash
applier parse-cv --cv assets/cv.pdf
# With motivation letter:
applier parse-cv --cv assets/cv.pdf --letter assets/letter.pdf
```

Writes `profiles/auto.toml`. Review and edit before searching.

### 3. Run a search

```bash
# Default (LinkedIn + FranceTravail + RemoteOK, Hamza's profile)
applier search

# All Tier 1 platforms, Île-de-France only
applier search --platforms linkedin,francetravail,indeed_fr,wttj --locations "Île-de-France"

# Add Tier 2 HTML scrapers (general)
applier search --platforms linkedin,francetravail,indeed_fr,wttj,hellowork,apec,keljob

# Add interim agency scrapers
applier search --platforms francetravail,indeed_fr,adecco,manpower,randstad,synergie

# Aviation/airport jobs
applier search --platforms francetravail,indeed_fr,aeroemploi

# Headhunter/cadre agencies
applier search --platforms apec,cadremploi,hays,michaelpage

# Freelance missions
applier search --platforms malt

# Student / étudiant jobs
applier search --platforms francetravail,jobetudiant,side

# Digital marketing profile with finance exclusions
applier search --profile profiles/digital-marketing.toml

# No filter (include alternance)
applier search --no-filter
```

### 4. Check company career pages

```bash
# Check all 100+ watchlisted companies for page changes
applier watchlist-check

# Filter by sector
applier watchlist-check --sector logistique

# Adjust timeout (default 10s)
applier watchlist-check --timeout 15
```

Reports a `CHANGED` flag if a career page content has changed since last check (SHA-16 diff). On first run, establishes baselines.

### 5. See source check history

```bash
# Sources not checked in the last 7 days → STALE
applier coverage

# Custom staleness window
applier coverage --days 3
```

### 6. Push results so Hamza can see them

```bash
git add results/jobs.json
git commit -m "data: update jobs $(date +%Y-%m-%d)"
git push
```

> **Do not commit:** `.env`, `jobs.db`, `assets/`, `profiles/auto.toml`, or anything under `.claude/` (agent session state). These are in `.gitignore`. Only `results/jobs.json` is meant to be shared as data.

---

## Profiles

Search profiles live in `profiles/*.toml`. Key sections:

```toml
[search]
roles_fr = ["livreur", "préparateur de commandes"]   # FR searches
roles_en = ["delivery driver", "warehouse operator"]  # EN/international

[[search.locations]]
label = "Île-de-France"
country = "FR"
ft_location = "Île-de-France"

[filter]
exclude_keywords = ["comptabilité", "finance", "audit"]  # drop jobs with these words
postes = ["livreur", "ouvrier"]                          # show only these postes in UI
domains = ["logistique", "transport"]                    # show only these domains in UI
```

Profiles included:
- `profiles/hamza.toml` — IT/hardware technico-commercial focus
- `profiles/digital-marketing.toml` — Marketing roles, excludes finance/compta jobs

---

## Watchlist

`watchlist/companies.toml` contains 100+ company career page URLs across 14 sectors:

- transport · aéroport · logistique · grande distribution · retail · it
- événementiel · industrie · agroalimentaire · btp · télécom · santé · nettoyage · interim

Add any company with:
```toml
[[company]]
name = "Acme Corp"
sector = "logistique"
careers_url = "https://acme.com/careers"
```

---

## GitHub Actions — Daily Automation

`.github/workflows/daily-search.yml` runs every day at 08:00 UTC:

1. Runs `applier search` (all Tier 1 platforms, Île-de-France + France)
2. Runs `applier watchlist-check`
3. Commits `results/jobs.json` + `results/jobs.html`
4. Sends a Telegram message with job count

**Required GitHub secrets:**
| Secret | Required | Description |
|---|---|---|
| `LINKEDIN_LI_AT` | No | LinkedIn cookie |
| `FRANCETRAVAIL_CLIENT_ID` | No | FT API key |
| `FRANCETRAVAIL_CLIENT_SECRET` | No | FT API secret |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token (skip notification if absent) |
| `TELEGRAM_CHAT_ID` | No | Telegram chat/user ID |

Trigger manually from GitHub → Actions → Daily Job Search → Run workflow.

---

## Commands

| Command | What it does |
|---|---|
| `applier parse-cv` | Parse a CV PDF and generate a search profile |
| `applier search` | Run a full search, save to DB, export JSON |
| `applier serve` | Start the web UI at http://localhost:5050 |
| `applier watchlist-check` | Check company career pages for changes |
| `applier coverage` | Show source check history (flag stale sources) |
| `applier platforms` | List all supported platforms with tiers |

### `applier search` options

| Option | Default | Description |
|---|---|---|
| `--profile` | `profiles/hamza.toml` | Search profile |
| `--platforms` | `linkedin,francetravail,remoteok` | Platforms to use |
| `--locations` | `all` | Locations from profile |
| `--count` | `25` | Max results per query |
| `--output` | `results/jobs.html` | Output file |
| `--no-filter` | off | Include alternance + skip profile exclusions |

### `applier watchlist-check` options

| Option | Default | Description |
|---|---|---|
| `--watchlist` | `watchlist/companies.toml` | Path to watchlist |
| `--timeout` | `10` | HTTP timeout per request (seconds) |
| `--sector` | (all) | Filter by sector |

### `applier coverage` options

| Option | Default | Description |
|---|---|---|
| `--days` | `7` | Mark sources not checked in N days as STALE |

---

## Platforms

| Platform | Method | Scope |
|---|---|---|
| `linkedin` | Guest API | Global |
| `francetravail` | REST API | FR only |
| `indeed_fr` | RSS feed | FR |
| `wttj` | JSON API | Global |
| `remoteok` | JSON API | Remote/global |
| `hellowork` | HTML scraper | FR |
| `apec` | HTML scraper | FR (cadres) |
| `keljob` | HTML scraper | FR |
| `aeroemploi` | HTML scraper | FR (aéroport/aviation) |
| `adecco` | HTML scraper | FR (intérim) |
| `manpower` | HTML scraper | FR (intérim) |
| `randstad` | HTML scraper | FR (intérim) |
| `synergie` | HTML scraper | FR (intérim) |
| `hays` | HTML scraper | FR (cadres/intérim) |
| `michaelpage` | HTML scraper | FR (cadres) |
| `cadremploi` | HTML scraper | FR (cadres) |
| `malt` | HTML scraper | FR (freelance) |
| `jobetudiant` | HTML scraper | FR (étudiant) |
| `side` | HTML scraper | FR (étudiant/intérim) |

---

## Troubleshooting

**Browser doesn't open**
→ Open `http://localhost:5050` manually.

**"command not found: applier"**
→ Activate your environment: `source .venv/bin/activate` (or use `uv run applier`).

**Jobs not showing after git pull**
→ Click **Refresh** in the top-right of the web UI.

**Port 5050 in use**
→ `applier serve --port 5051`

**HelloWork / APEC returns 0 results**
→ These sites have bot protection. Results may vary. Tier 1 platforms (FranceTravail, Indeed RSS, WTTJ) are more reliable.
