# Seedance Prompt Scout Health Audit - 2026-05-22

Status: diagnosis plus follow-up schedule update. Parser code was not changed.

## Verdict

The collector is working, but it is not configured to collect "always" or across the whole internet.

The previous behavior could look broken because:

1. The GitHub Actions schedule was weekly, not daily or continuous.
2. Broad web/video providers are configured but skipped until GitHub Secrets are added.
3. Candidate dedupe means repeated runs may append very few new rows.
4. Same-day runs overwrite the same dated report/source files.
5. The current source scope is limited and intentionally filtered.

## Evidence Checked

- Repository: `AI-Nikitka93/seedance-prompt-scout`
- Local repo path: `M:\AI\VIDEO\05_PROMPTS\SEEDANCE_2_AGENT_PROMPT_LAB\10_EXTERNAL_COLLECTOR\github-actions-seedance-prompt-scout`
- Workflow file: `.github/workflows/seedance-prompt-scout.yml`
- Workflow state from GitHub API: `active`
- GitHub Actions permissions from API: `enabled=true`, `allowed_actions=all`
- Latest GitHub run inspected: `26251197335`, completed successfully on `2026-05-21T20:27:13Z`
- Latest GitHub run result: `143 scans`, `205 candidates`, `1 appended`
- Local smoke run on `2026-05-22`: `143 scans`, `204 candidates`, `13 appended`

## Root Causes

### 1. Schedule Is Weekly

Workflow schedule:

```yaml
schedule:
  - cron: "17 5 * * 1"
```

This used to run once per week, Monday at 05:17 UTC. The workflow was created on 2026-05-21, so a scheduled run would not be expected until the next Monday. The runs seen so far were manual `workflow_dispatch` runs.

Follow-up change applied on 2026-05-22:

```yaml
schedule:
  - cron: "17 5 * * *"
```

The scout is now configured to run daily at 05:17 UTC after this change is pushed to GitHub.

### 2. Broad Search Providers Are Missing Secrets

The workflow exposes these optional secrets:

```yaml
BRAVE_SEARCH_API_KEY
TAVILY_API_KEY
EXA_API_KEY
SERPAPI_API_KEY
YOUTUBE_API_KEY
STACKAPPS_KEY
```

The inspected GitHub run showed those values empty. The script therefore safely skips broad web/video providers. The local 2026-05-22 report shows these skipped provider rows:

- `brave_web_seedance_prompt_search`
- `tavily_web_seedance_prompt_search`
- `exa_web_seedance_prompt_search`
- `serpapi_google_seedance_prompt_search`
- `youtube_seedance_prompt_video_search`

This means the collector currently searches mostly fixed URLs, GitHub, Hugging Face, and Stack Exchange, not the full web or YouTube.

### 3. Dedupe Makes Runs Look Empty

The collector appends to:

```text
data/candidate_prompts.jsonl
```

but only if a candidate ID is new. This is handled by `append_jsonl()` in `scripts/seedance_prompt_scout.py`. The latest GitHub run found 205 candidate snippets but appended only 1 new row because most were already known.

### 4. Same-Day Files Are Overwritten

The script writes dated files:

```text
data/YYYY-MM-DD_sources.jsonl
reports/YYYY-MM-DD_seedance_prompt_scout.md
prompts/YYYY-MM-DD_candidate_index.md
```

Multiple runs on the same UTC date update the same filenames. This can hide activity because the repo does not keep per-run files unless the date changes.

### 5. Scope Is Limited By Design

`README.md` says the current version does not search the whole internet. It checks configured sources from `config/sources.json`. Broader search needs optional provider secrets.

## Current Local Diagnostic Artifacts

The local smoke run created or modified:

```text
data/2026-05-22_sources.jsonl
reports/2026-05-22_seedance_prompt_scout.md
prompts/2026-05-22_candidate_index.md
data/candidate_prompts.jsonl
```

These local artifacts were not pushed to GitHub during this audit.

## Recommended Fixes

1. Done locally: change the cron schedule from weekly to daily if the desired behavior is regular daily collection.
2. Add at least one broad web search secret, preferably `TAVILY_API_KEY` or `BRAVE_SEARCH_API_KEY`.
3. Add `YOUTUBE_API_KEY` only if video titles/descriptions are important.
4. Add run IDs or timestamps to report filenames if per-run history matters.
5. Improve the report so skipped providers show their error messages, not only `ok=False`.
6. Add a summary section separating:
   - scanned successfully;
   - skipped because missing secret;
   - disabled by policy;
   - filtered out;
   - newly appended.

## Suggested Default

For a free but denser setup:

- run daily at a stable low-traffic UTC time;
- keep fixed sources, GitHub, Hugging Face, and Stack Exchange enabled;
- add `TAVILY_API_KEY` for broad web search;
- add `YOUTUBE_API_KEY` only if prompt videos are a priority;
- keep Reddit disabled unless an allowed API route is added.
