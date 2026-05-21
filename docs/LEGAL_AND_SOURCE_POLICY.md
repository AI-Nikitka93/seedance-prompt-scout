# Legal And Source Policy

Этот сборщик нужен для research inbox, а не для бездумного копирования чужих материалов.

## Правила

- Хранить ссылку на источник, дату проверки и trust-level.
- По умолчанию сохранять короткие snippets, а не полные страницы.
- Полные prompts переносить в best library только если источник явно разрешает reuse или prompt переписан как собственный производный шаблон с сохраненной provenance-ссылкой.
- Не обходить логины, антибот, paywall, robots/ToS или rate limits.
- Не собирать deepfake/impersonation/NSFW/jailbreak-находки в best library.

## Статусы

- `candidate` - найдено автоматически, не проверено.
- `reviewed` - агент/человек проверил источник, лицензию и полезность.
- `promoted` - можно переносить в локальную best library.
- `rejected` - риск, мусор, дубль или слабый prompt.

## Минимальный provenance block

```text
source_url:
source_type:
date_found:
license_or_reuse_note:
why_useful:
risk_flags:
local_rewrite_status:
```
