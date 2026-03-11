# Profs

`profs` is a beginner-friendly Python package for finding faculty profile pages, extracting professor details, looking up recent publications, scoring startup signals, summarizing research focus, and drafting outreach emails.

The project now uses a modular package layout instead of a single CMU-only script. CMU is still supported, but through YAML config in [`config/universities/cmu.yaml`](/Users/moonkwoun/Downloads/Profs/config/universities/cmu.yaml), not through hardcoded CMU logic.

## What It Does

Given a department or faculty directory URL, the pipeline can:

1. discover likely faculty profile pages
2. extract structured professor details
3. score founder/startup signals
4. look up recent publications with OpenAlex first and Crossref as fallback
5. summarize a research focus phrase and security relevance
6. draft an outreach email using the exact required template
7. write CSV and JSON outputs

## Project Layout

```text
README.md
requirements.txt
.env.example
pyproject.toml
src/profs/
config/universities/
templates/
tests/
```

## Requirements

- Python 3.11 or newer
- `pip`
- Optional: Playwright browser binaries for JavaScript-heavy sites
- Optional: OpenAI API key for model-based research focus summarization

## Setup

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install the package

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

### 3. Create an environment file

```bash
cp .env.example .env
```

Edit `.env` if you want model-based summarization:

```bash
OPENAI_API_KEY=your_key_here
PROFS_OPENAI_MODEL=gpt-4.1-mini
```

### 4. Install Playwright browser support

Playwright is only used as a fallback when normal `requests` + BeautifulSoup scraping is not enough.

```bash
playwright install chromium
```

## Quick Start

### Small test run

```bash
python -m profs.cli test \
  --directory-url "https://www.csd.cs.cmu.edu/people/faculty" \
  --university "Carnegie Mellon University" \
  --department "Computer Science"
```

### Full run

```bash
python -m profs.cli run \
  --directory-url "https://www.csd.cs.cmu.edu/people/faculty" \
  --university "Carnegie Mellon University" \
  --department "Computer Science" \
  --config config/universities/cmu.yaml
```

## CLI Commands

### `run`

Runs the full pipeline.

```bash
python -m profs.cli run \
  --directory-url "https://example.edu/faculty" \
  --university "Example University" \
  --department "Computer Science"
```

Useful flags:

- `--config`: path to a university YAML file
- `--max-pages`: limit directory pagination crawling
- `--max-profiles`: limit how many discovered profiles are processed
- `--output-dir`: where CSV and JSON files should be written
- `--disable-browser-fallback`: skip Playwright fallback

### `test`

Runs the same pipeline with safe defaults for quick validation:

- `max_pages=1`
- `max_profiles=5`

## Configuration

University settings live in YAML files inside `config/universities/`.

[`config/universities/default.yaml`](/Users/moonkwoun/Downloads/Profs/config/universities/default.yaml) contains generic defaults.

[`config/universities/cmu.yaml`](/Users/moonkwoun/Downloads/Profs/config/universities/cmu.yaml) overrides those defaults to preserve the old CMU workflow using configuration only.

Current config values include:

- profile link regex hints
- pagination parameter
- title aliases
- startup keywords
- research keywords
- discovery limits

## Output Files

Each run writes two files in the selected output directory:

- `faculty_results.csv`
- `faculty_results.json`

Each row/object includes:

- `name`
- `first_name`
- `title`
- `email`
- `personal_website`
- `profile_url`
- `university`
- `department`
- `research_text`
- `startup_signal_hard`
- `startup_evidence_hard`
- `dealflow_score`
- `publications_json`
- `focus_phrase`
- `is_security_related`
- `alignment_sentence`
- `draft_email`
- `discovery_method`
- `extraction_confidence`
- `publication_confidence`
- `no_recent_publications`
- `notes`

## Testing

Run the unit tests with:

```bash
pytest
```

## Troubleshooting

### No faculty URLs discovered

- Check that the directory URL is correct.
- Try increasing `--max-pages`.
- Add or adjust profile URL regexes in your YAML config.
- If the site is JavaScript-heavy, remove `--disable-browser-fallback` and install Playwright.

### Playwright fallback is not working

- Confirm Playwright is installed:

```bash
pip install playwright
playwright install chromium
```

### OpenAI summarization is skipped

- If `OPENAI_API_KEY` is missing, the package falls back to deterministic heuristics for research focus.
- This is expected for local tests and offline development.

### Publication lookup returns zero recent publications

- The pipeline intentionally keeps zero results when nothing is found in the allowed date window.
- It sets `no_recent_publications=true` instead of inventing older or uncertain papers.

## Notes For Beginners

- Start with the `test` command first.
- Use `config/universities/default.yaml` as your template for a new school.
- The scraper always tries `requests` + BeautifulSoup first.
- Playwright is a fallback, not the default path.
