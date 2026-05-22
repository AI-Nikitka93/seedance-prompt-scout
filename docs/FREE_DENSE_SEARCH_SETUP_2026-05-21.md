# Free Dense Search Setup - 2026-05-21

## Verdict

Нельзя честно настроить "поиск по всему интернету" полностью бесплатно без внешнего поискового индекса. GitHub Actions - это runner, а не search engine.

Рабочая бесплатная плотная схема:

1. Always-on no-key слой: GitHub Search, Hugging Face Hub, Stack Exchange API, фиксированные web URLs.
2. Research-only no-key слой: arXiv API поддержан, но выключен по умолчанию из-за timeout/429 в локальном smoke и низкой ценности для prompt packs.
3. Optional free-credit слой: Tavily, Exa, Brave Search API, SerpAPI, YouTube Data API.
4. Все результаты хранить как candidates/snippets/provenance, а не как автоматически одобренные best prompts.

## Source-Backed Free Options

| Provider | Free status on 2026-05-21 | Secret | Use in scout | Notes |
|---|---:|---|---|---|
| GitHub REST/Search | `GITHUB_TOKEN` works in Actions; rate limit for `GITHUB_TOKEN` is 1,000 requests/hour/repo | built-in | enabled | Good for prompt repos and README discovery. |
| Hugging Face Hub | Open Hub endpoints/search docs; HF-wide rate limits apply | none | enabled | Good for models/datasets/spaces that mention Seedance/video prompts. |
| arXiv API | no auth; use polite delay and cache | none | supported, disabled by default | Technical research, not prompt packs; local smoke hit timeout/429. |
| Stack Exchange API | no-key access works with lower/shared quota; key can raise quota | optional `STACKAPPS_KEY` | enabled | Technical Q&A only; likely lower prompt yield. |
| Tavily | 1,000 free API credits/month, no credit card | `TAVILY_API_KEY` | optional | Good broad AI search; basic search costs 1 credit. |
| Exa | pricing page says up to 1,000 requests/month free | `EXA_API_KEY` | optional | Good semantic search; useful for guides and long-tail pages. |
| Brave Search API | $5 free monthly credits; Search listed at $5/1,000 requests | `BRAVE_SEARCH_API_KEY` | optional | Broad independent web index; card may be required for anti-fraud. |
| SerpAPI | free plan listed at 250 searches/month | `SERPAPI_API_KEY` | optional | Small but useful Google SERP fallback. |
| YouTube Data API | default 10,000 units/day; `search.list` costs 100 units/call | `YOUTUBE_API_KEY` | optional | Search titles/descriptions only; do not scrape transcripts by default. |
| Google Custom Search JSON API | 100 queries/day only for existing customers; not available for new customers; discontinuation Jan 1, 2027 | not wired | rejected | Not a good new setup path. |

## Official Sources Checked

- GitHub REST API rate limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- GitHub `GITHUB_TOKEN`: https://docs.github.com/en/actions/tutorials/authenticate-with-github_token
- Hugging Face Hub search: https://huggingface.co/docs/hub/search
- Hugging Face Hub API endpoints: https://huggingface.co/docs/hub/main/api
- arXiv API manual: https://info.arxiv.org/help/api/user-manual.html
- Stack Exchange API throttles: https://api.stackexchange.com/docs/throttle
- Tavily credits/pricing: https://docs.tavily.com/documentation/api-credits
- Tavily Search API: https://docs.tavily.com/api-reference/endpoint/search
- Exa API pricing: https://exa.ai/pricing?tab=api
- Exa Search API: https://docs.exa.ai/reference/search
- Brave Search API: https://brave.com/search/api/
- SerpAPI pricing: https://serpapi.com/pricing
- YouTube Data API quota and compliance: https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits
- YouTube `search.list`: https://developers.google.com/youtube/v3/docs/search/list
- Google Custom Search JSON API: https://developers.google.com/custom-search/v1/overview

## Recommended Dense Free Profile

### No secrets

Runs immediately:

- fixed official/community URLs;
- GitHub repos;
- GitHub repository search;
- Hugging Face models/datasets/spaces;
- arXiv API is supported but disabled by default; enable only for technical-paper checks;
- Stack Exchange API.

### Add these GitHub Secrets for broader web search

Best order:

1. `TAVILY_API_KEY` - easiest free AI-search budget.
2. `EXA_API_KEY` - semantic long-tail web search.
3. `BRAVE_SEARCH_API_KEY` - broad independent web index.
4. `YOUTUBE_API_KEY` - video tutorial discovery, but keep query count low.
5. `SERPAPI_API_KEY` - small fallback when Google SERP shape matters.
6. `STACKAPPS_KEY` - optional quota improvement for Stack Exchange.

GitHub path:

`Repo -> Settings -> Secrets and variables -> Actions -> New repository secret`

## Query Budget

Default config is intentionally conservative:

- Tavily: 4 queries/run x basic search = 4 credits/run.
- Exa: 3 queries/run.
- Brave: 6 queries/run.
- SerpAPI: 3 queries/run.
- YouTube: 3 queries/run x 100 units = 300 units/run.

Daily schedule is the active default for this scout. It is still plausible if only no-key sources and light Tavily/Exa/Brave usage are enabled, but SerpAPI and YouTube should stay low. Weekly schedule remains the safer fallback for very small free quotas.

## What Changed In This Scaffold

New source types:

- `brave_search`
- `tavily_search`
- `exa_search`
- `serpapi_search`
- `youtube_search`
- `huggingface_search`
- `arxiv_search`
- `stackexchange_search`
- `rss_feed`

Providers that require secrets are enabled in config but safely skipped when the secret is missing. That means the repo can stay public without exposing keys.
