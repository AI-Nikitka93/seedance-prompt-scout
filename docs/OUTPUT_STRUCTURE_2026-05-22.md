# Output Structure - 2026-05-22

Goal: make the GitHub repository readable as a daily prompt-research inbox, not only a raw data dump.

## Human-First Surfaces

Open these first:

```text
dashboard/README.md
prompts/LATEST_candidate_index.md
reports/LATEST_seedance_prompt_scout.md
```

### `dashboard/README.md`

The public landing page for the latest run. It contains:

- latest run date;
- quick links to latest report, latest review inbox, raw source log, and cumulative candidates;
- a compact run summary table;
- de-duplicated top review targets;
- source health table;
- skipped/setup-needed table;
- promotion path.

### `prompts/LATEST_candidate_index.md`

The copy/review surface. It uses candidate cards with:

- title;
- score;
- trust label;
- source URL;
- candidate ID;
- snippet in a fenced text block.

This file is still an inbox. It is not an approved prompt library.

### `reports/LATEST_seedance_prompt_scout.md`

The latest detailed run report. It includes the same readable sections plus raw source status lines for diagnostics.

## Dated Archive

The collector still writes dated files for traceability:

```text
data/YYYY-MM-DD_sources.jsonl
reports/YYYY-MM-DD_seedance_prompt_scout.md
prompts/YYYY-MM-DD_candidate_index.md
```

## Cumulative Data

```text
data/candidate_prompts.jsonl
```

This remains the de-duplicated machine-readable candidate store. Repeated runs may find many candidates but append only a few new IDs.

## GitHub Actions Commit Scope

The workflow now commits:

```text
dashboard/
data/
reports/
prompts/
```

That keeps the repo readable on GitHub while preserving raw audit data.

## Promotion Rule

Nothing from the collector is automatically a best prompt. Promotion requires:

1. provenance/source check;
2. safety and license check;
3. rewrite into local Seedance prompt-lab format;
4. quality-gate review before moving into the local best-prompt library.
