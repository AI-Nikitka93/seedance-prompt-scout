# AGENT CONTRACT: EXTERNAL SEEDANCE PROMPT SCOUT

Ты работаешь в переносимом GitHub Actions scaffold для Seedance 2 prompt scouting.

## Цель

Сделать внешний сборщик, который запускается не на ПК пользователя, а в GitHub Actions или аналогичной бесплатной платформе.

## Правила

1. Не привязывай сбор к локальному `M:\AI` и не создавай локальные scheduled tasks.
2. Основная поверхность выполнения - `.github/workflows/seedance-prompt-scout.yml`.
3. Парсер должен оставаться stdlib-only, чтобы GitHub Actions запускался без dependency install.
4. Источники добавляй через `config/sources.json`.
5. Сборщик хранит candidates, snippets, links, provenance и reports, а не объявляет найденное "best prompt" автоматически.
6. Не обходи login, paywall, anti-bot, robots/ToS или rate limits.
7. Рискованные находки с jailbreak, bypass, NSFW, deepfake/impersonation не переносить в best library.
8. Для публикации в GitHub repo нужна явная команда пользователя; локально держи scaffold как подготовленный artifact.

## Definition of done

- workflow валиден и запускает `scripts/seedance_prompt_scout.py`;
- конфиг источников читается;
- скрипт проходит `python -m py_compile`;
- `--dry-run` показывает источники без сетевого сбора;
- инструкции деплоя описывают, что после публикации сбор идет на GitHub, не на ПК.
