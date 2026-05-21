# Search Scope Audit - 2026-05-21

## Verdict

Current scaffold still does **not** literally search the whole internet by itself.

It now has two layers:

- no-key configured sources: public web URLs, GitHub repos/search, Hugging Face, Stack Exchange;
- research-only no-key source: arXiv is supported but disabled by default after timeout/429 in local smoke;
- optional free-credit web-search providers: Brave, Tavily, Exa, SerpAPI, YouTube.

Optional providers are skipped until their GitHub Actions secrets are set.

## Current Source Counts

- total configured sources: 17;
- enabled sources: 15;
- source types:
  - `web`: 3;
  - `github_repo`: 4;
  - `github_search`: 2.
  - `huggingface_search`: 1;
  - `arxiv_search`: 1 disabled by default;
  - `stackexchange_search`: 1;
  - `brave_search`: 1;
  - `tavily_search`: 1;
  - `exa_search`: 1;
  - `serpapi_search`: 1;
  - `youtube_search`: 1.

## What The Workflow Runs

`.github/workflows/seedance-prompt-scout.yml` runs:

```bash
python scripts/seedance_prompt_scout.py
```

The script currently supports:

- `web`;
- `github_repo`;
- `github_search`.
- `huggingface_search`;
- `arxiv_search`;
- `stackexchange_search`;
- `brave_search`;
- `tavily_search`;
- `exa_search`;
- `serpapi_search`;
- `youtube_search`;
- `rss_feed`.

There is still no recursive crawler, no sitemap crawler, and no link-following crawler.

## What "Whole Internet" Would Require

GitHub Actions is only a runner. It does not provide a web search index.

To search broadly across the public web, the project needs one of these added explicitly:

- GitHub Actions secrets for one or more real search API providers;
- a curated RSS/sitemap/source registry;
- a compliant crawler over a narrow allowlist of sites;
- a hybrid route: GitHub Search + web search API + curated source watchlist.

## Safe Recommendation

Use the new dense free profile in `FREE_DENSE_SEARCH_SETUP_2026-05-21.md`.

Do not use search-engine HTML scraping or anti-bot bypass as the default route.
