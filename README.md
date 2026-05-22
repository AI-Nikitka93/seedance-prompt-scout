# Seedance 2 Prompt Scout

Внешний сборщик для Seedance 2.0 prompt research. Он рассчитан на отдельный GitHub-репозиторий и запускается не на ПК пользователя, а в GitHub Actions по расписанию.

## Что делает

- ежедневно или вручную открывает список публичных источников из `config/sources.json`;
- проверяет официальные страницы, GitHub-репозитории, GitHub Search и выбранные публичные guide-страницы;
- вытаскивает короткие prompt-сигналы, ссылки, дату проверки, тип источника и риск-флаги;
- пишет аккуратную витрину в `dashboard/`, review inbox в `prompts/`, отчеты в `reports/` и raw data в `data/`;
- сам коммитит изменения обратно в репозиторий через `GITHUB_TOKEN`.

## Что не делает

- не запускает генерацию видео;
- не требует платных API;
- не обходит антибот-защиту, логины, paywall или robots/ToS;
- не копирует целые статьи или чужие библиотеки без разбора лицензии;
- не считает найденный prompt автоматически "лучшим" без human/agent review.

## Быстрый запуск на GitHub

1. Создать новый публичный GitHub-репозиторий, например `seedance-prompt-scout`.
2. Скопировать содержимое этой папки в корень репозитория.
3. В GitHub включить Actions.
4. В `Settings -> Actions -> General -> Workflow permissions` выбрать `Read and write permissions`.
5. Открыть `Actions -> Seedance Prompt Scout -> Run workflow`.
6. После прогона сначала смотреть:
   - `dashboard/README.md`
   - `prompts/LATEST_candidate_index.md`
   - `reports/LATEST_seedance_prompt_scout.md`
7. Если нужен raw audit, смотреть:
   - `reports/YYYY-MM-DD_seedance_prompt_scout.md`
   - `data/YYYY-MM-DD_sources.jsonl`
   - `data/candidate_prompts.jsonl`
   - `prompts/YYYY-MM-DD_candidate_index.md`

Секреты не нужны: стандартный `GITHUB_TOKEN` GitHub Actions используется для GitHub API и коммита результатов.

## Как переносить в локальную лабораторию

Сборщик - внешний inbox. Лучшие находки переносить в локальный vault:

`M:\AI\VIDEO\05_PROMPTS\SEEDANCE_2_AGENT_PROMPT_LAB\01_PROMPT_LIBRARY`

Перед переносом прогонять качество по:

`M:\AI\VIDEO\05_PROMPTS\SEEDANCE_2_AGENT_PROMPT_LAB\04_EVALUATION\SEEDANCE2_PROMPT_QUALITY_GATE.md`

## Почему GitHub Actions

GitHub Actions дает бесплатный repo-native cron для публичного репозитория, умеет писать результаты прямо в git, имеет стандартный `GITHUB_TOKEN` и не требует держать локальный ПК включенным.

Текущее расписание: ежедневно в 05:17 UTC через `.github/workflows/seedance-prompt-scout.yml`.

## Search scope

Текущая версия не ищет "по всему интернету". Она проверяет только источники из `config/sources.json`: фиксированные web URLs, выбранные GitHub repos и GitHub repository search queries.

Audit: `docs/SEARCH_SCOPE_AUDIT_2026-05-21.md`.

Расширенная бесплатная схема добавлена в `docs/FREE_DENSE_SEARCH_SETUP_2026-05-21.md`: без ключей работает GitHub/Hugging Face/arXiv/StackExchange, а для более широкого web search можно добавить GitHub Secrets для Tavily, Exa, Brave, SerpAPI и YouTube.

Сравнение с альтернативами лежит в `docs/FREE_HOSTING_OPTIONS_2026-05-21.md`.
