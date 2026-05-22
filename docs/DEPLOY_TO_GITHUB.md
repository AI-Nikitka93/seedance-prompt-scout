# Deploy To GitHub

Цель: один раз выложить эту папку как отдельный репозиторий, после этого сбор работает на GitHub, а не на ПК.

## 1. Создать репозиторий

Рекомендуемый вариант: публичный GitHub repo `seedance-prompt-scout`.

Почему публичный: для такого research-сборщика не нужны секреты, а публичные репозитории лучше подходят под бесплатный scheduled workflow.

## 2. Скопировать scaffold в корень repo

Источник:

`M:\AI\VIDEO\05_PROMPTS\SEEDANCE_2_AGENT_PROMPT_LAB\10_EXTERNAL_COLLECTOR\github-actions-seedance-prompt-scout`

В корне GitHub repo должны оказаться:

- `.github/workflows/seedance-prompt-scout.yml`
- `config/sources.json`
- `scripts/seedance_prompt_scout.py`
- `data/`
- `dashboard/`
- `reports/`
- `prompts/`
- `docs/`
- `README.md`

## 3. Включить запись результатов

В GitHub:

`Settings -> Actions -> General -> Workflow permissions -> Read and write permissions`

Это нужно, чтобы workflow мог коммитить `data/`, `reports/`, `prompts/` обратно в репозиторий через стандартный `GITHUB_TOKEN`.

## 3.1. Опционально включить плотный web search

Без секретов сборщик уже ищет по GitHub, Hugging Face, arXiv, Stack Exchange и фиксированным URL.

Для более широкого web search добавь любые доступные бесплатные ключи:

- `TAVILY_API_KEY`
- `EXA_API_KEY`
- `BRAVE_SEARCH_API_KEY`
- `SERPAPI_API_KEY`
- `YOUTUBE_API_KEY`
- `STACKAPPS_KEY`

GitHub путь:

`Settings -> Secrets and variables -> Actions -> New repository secret`

Подробности и лимиты: `docs/FREE_DENSE_SEARCH_SETUP_2026-05-21.md`.

## 4. Запустить вручную первый прогон

`Actions -> Seedance Prompt Scout -> Run workflow`

После запуска проверить последний workflow run. Если все нормально, появятся новые файлы:

- `dashboard/README.md`
- `reports/LATEST_seedance_prompt_scout.md`
- `prompts/LATEST_candidate_index.md`
- `reports/YYYY-MM-DD_seedance_prompt_scout.md`
- `data/YYYY-MM-DD_sources.jsonl`
- `data/candidate_prompts.jsonl`
- `prompts/YYYY-MM-DD_candidate_index.md`

Начинать просмотр лучше с `dashboard/README.md`: это аккуратная витрина последнего прогона, а не raw dump.

## 5. Расписание

Сейчас стоит ежедневно:

```yaml
schedule:
  - cron: "17 5 * * *"
```

Это каждый день в 05:17 UTC. Если нужно снизить нагрузку на бесплатные лимиты, можно вернуть еженедельный режим:

```yaml
schedule:
  - cron: "17 5 * * 1"
```

Не ставь слишком частый запуск: для prompt research обычно достаточно 1 раз в день. Если подключены маленькие бесплатные лимиты вроде SerpAPI или YouTube, держи число запросов в `config/sources.json` низким.

## 6. Как добавлять источники

Править `config/sources.json`.

Поддержанные типы:

- `web` - публичная HTML/text/json страница;
- `github_repo` - GitHub repo, из которого читается README и metadata;
- `github_search` - GitHub repository search.

Если источник требует логин, обход антибота, paywall или сомнительные условия доступа, не включать его в автоматический сборщик.

## 7. Как переносить лучшие промпты в локальный vault

Сборщик пишет только candidates. Лучшее переносить вручную или отдельным review-agent этапом в:

`M:\AI\VIDEO\05_PROMPTS\SEEDANCE_2_AGENT_PROMPT_LAB\01_PROMPT_LIBRARY`

Перед переносом нужен provenance/licensing check и перепаковка под локальный стандарт Seedance prompt agent.
