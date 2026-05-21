#!/usr/bin/env python3
"""Seedance 2 prompt scout.

Stdlib-only collector for GitHub Actions. It gathers short snippets and source
metadata from configured public sources, then writes git-friendly artifacts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html.parser
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "sources.json"
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
PROMPTS_DIR = ROOT / "prompts"

DEFAULT_KEYWORDS = [
    "seedance",
    "prompt",
    "camera",
    "shot",
    "cinematic",
    "timeline",
    "i2v",
    "t2v",
    "reference image",
]

DEFAULT_RISK_TERMS = [
    "jailbreak",
    "bypass",
    "paywall",
    "uncensored",
    "nsfw",
    "deepfake",
    "celebrity deepfake",
    "impersonation",
]


class HTMLTextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in {"p", "br", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in {"p", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
        self.parts.append(data)

    @property
    def title(self) -> str:
        return normalize_ws(" ".join(self.title_parts))

    @property
    def text(self) -> str:
        return normalize_ws(" ".join(self.parts))


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def stable_id(*parts: str) -> str:
    payload = "\n".join(parts).encode("utf-8", "ignore")
    return hashlib.sha256(payload).hexdigest()[:16]


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def fetch_text(
    url: str,
    *,
    token: str | None = None,
    accept: str | None = None,
    headers_extra: dict[str, str] | None = None,
    method: str | None = None,
    data: bytes | None = None,
    attempts: int = 2,
) -> dict[str, Any]:
    headers = {
        "User-Agent": "seedance-prompt-scout/0.1",
        "Accept": accept or "text/html,application/json,text/plain,*/*",
    }
    if headers_extra:
        headers.update(headers_extra)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last_error: str | None = None
    for attempt in range(1, max(1, attempts) + 1):
        req = request.Request(url, headers=headers, data=data, method=method)
        try:
            with request.urlopen(req, timeout=35) as resp:
                raw = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                text = raw.decode(charset, "replace")
                return {
                    "ok": True,
                    "status": resp.status,
                    "url": resp.geturl(),
                    "content_type": resp.headers.get("content-type", ""),
                    "text": text,
                }
        except error.HTTPError as exc:
            body = exc.read(3000).decode("utf-8", "replace")
            if exc.code in {429, 500, 502, 503, 504} and attempt < attempts:
                time.sleep(2 * attempt)
                last_error = str(exc)
                continue
            return {"ok": False, "status": exc.code, "url": url, "error": str(exc), "text": body}
        except Exception as exc:  # noqa: BLE001 - CI collector should report, not crash whole run.
            last_error = repr(exc)
            if attempt < attempts:
                time.sleep(2 * attempt)
                continue
            return {"ok": False, "status": None, "url": url, "error": last_error, "text": ""}
    return {"ok": False, "status": None, "url": url, "error": last_error or "request failed", "text": ""}


def fetch_json_get(url: str, *, headers_extra: dict[str, str] | None = None) -> dict[str, Any]:
    response = fetch_text(url, accept="application/json", headers_extra=headers_extra)
    if not response["ok"]:
        return {"ok": False, "status": response.get("status"), "error": response.get("error"), "url": url}
    try:
        payload = json.loads(response["text"])
    except json.JSONDecodeError as exc:
        return {"ok": False, "status": response.get("status"), "error": str(exc), "url": url}
    return {"ok": True, "status": response.get("status"), "url": response.get("url") or url, "payload": payload}


def fetch_json_post(url: str, payload: dict[str, Any], *, headers_extra: dict[str, str] | None = None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    response = fetch_text(
        url,
        accept="application/json",
        headers_extra={"Content-Type": "application/json", **(headers_extra or {})},
        method="POST",
        data=body,
    )
    if not response["ok"]:
        return {"ok": False, "status": response.get("status"), "error": response.get("error"), "url": url}
    try:
        parsed = json.loads(response["text"])
    except json.JSONDecodeError as exc:
        return {"ok": False, "status": response.get("status"), "error": str(exc), "url": url}
    return {"ok": True, "status": response.get("status"), "url": response.get("url") or url, "payload": parsed}


def parse_document(text: str, content_type: str) -> tuple[str, str]:
    if "html" in content_type.lower() or "<html" in text[:500].lower():
        parser = HTMLTextExtractor()
        parser.feed(text)
        return parser.title, parser.text
    return "", normalize_ws(text)


def keyword_pattern(keywords: list[str]) -> re.Pattern[str]:
    escaped = [re.escape(item) for item in keywords if item.strip()]
    return re.compile("|".join(escaped), re.IGNORECASE) if escaped else re.compile("seedance", re.IGNORECASE)


def extract_snippets(text: str, keywords: list[str], max_chars: int) -> list[str]:
    pattern = keyword_pattern(keywords)
    seen: set[str] = set()
    snippets: list[str] = []
    for match in pattern.finditer(text):
        start = max(0, match.start() - max_chars // 2)
        end = min(len(text), match.end() + max_chars // 2)
        snippet = normalize_ws(text[start:end])
        if len(snippet) > max_chars:
            snippet = snippet[: max_chars - 1].rstrip() + "..."
        key = stable_id(snippet.lower())
        if key in seen:
            continue
        seen.add(key)
        snippets.append(snippet)
        if len(snippets) >= 8:
            break
    return snippets


def risk_flags(text: str, risk_terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in risk_terms if term.lower() in lowered]


def score_snippet(snippet: str, keywords: list[str], trust: str) -> int:
    lowered = snippet.lower()
    score = 0
    for keyword in keywords:
        if keyword.lower() in lowered:
            score += 2
    if any(term in lowered for term in ["camera", "shot", "timeline", "duration", "reference"]):
        score += 4
    if "official" in trust or "primary" in trust:
        score += 3
    if len(snippet) > 180:
        score += 1
    return score


def scan_web(source: dict[str, Any], config: dict[str, Any], token: str | None) -> list[dict[str, Any]]:
    response = fetch_text(source["url"], token=token)
    keywords = config.get("keywords") or DEFAULT_KEYWORDS
    max_chars = int(config.get("policy", {}).get("max_snippet_chars", 700))
    title, body = parse_document(response.get("text", ""), response.get("content_type", ""))
    snippets = extract_snippets(body, keywords, max_chars) if response["ok"] else []
    return [
        {
            "kind": "source_scan",
            "source_id": source["id"],
            "source_type": source["type"],
            "trust": source.get("trust", "unknown"),
            "url": response.get("url") or source["url"],
            "status": response.get("status"),
            "ok": response["ok"],
            "title": title,
            "error": response.get("error"),
            "snippets": snippets,
            "risk_flags": risk_flags(" ".join(snippets), config.get("risk_terms", [])),
        }
    ]


def github_api_json(path: str, token: str | None) -> dict[str, Any]:
    url = "https://api.github.com" + path
    response = fetch_text(url, token=token, accept="application/vnd.github+json")
    if not response["ok"]:
        return {"ok": False, "status": response.get("status"), "error": response.get("error"), "url": url}
    try:
        payload = json.loads(response["text"])
    except json.JSONDecodeError as exc:
        return {"ok": False, "status": response.get("status"), "error": str(exc), "url": url}
    return {"ok": True, "status": response.get("status"), "url": url, "payload": payload}


def scan_github_repo(source: dict[str, Any], config: dict[str, Any], token: str | None) -> list[dict[str, Any]]:
    repo = source["repo"]
    repo_meta = github_api_json(f"/repos/{repo}", token)
    readme_url = f"https://api.github.com/repos/{repo}/readme"
    readme = fetch_text(readme_url, token=token, accept="application/vnd.github.raw")
    keywords = config.get("keywords") or DEFAULT_KEYWORDS
    max_chars = int(config.get("policy", {}).get("max_snippet_chars", 700))
    title = repo
    if repo_meta.get("ok"):
        payload = repo_meta["payload"]
        title = payload.get("full_name") or repo
        repo_text = " ".join(
            str(payload.get(key) or "")
            for key in ["full_name", "description", "topics", "language", "pushed_at", "html_url"]
        )
    else:
        repo_text = ""
    readme_title, readme_body = parse_document(readme.get("text", ""), readme.get("content_type", "text/plain"))
    combined = normalize_ws(repo_text + " " + readme_body)
    snippets = extract_snippets(combined, keywords, max_chars) if combined else []
    return [
        {
            "kind": "source_scan",
            "source_id": source["id"],
            "source_type": source["type"],
            "trust": source.get("trust", "unknown"),
            "url": f"https://github.com/{repo}",
            "status": readme.get("status") or repo_meta.get("status"),
            "ok": bool(repo_meta.get("ok") or readme.get("ok")),
            "title": readme_title or title,
            "error": repo_meta.get("error") if not repo_meta.get("ok") else readme.get("error"),
            "snippets": snippets,
            "risk_flags": risk_flags(combined, config.get("risk_terms", [])),
        }
    ]


def scan_github_search(source: dict[str, Any], config: dict[str, Any], token: str | None) -> list[dict[str, Any]]:
    query = source["query"]
    limit = int(source.get("limit", 10))
    qs = parse.urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": min(limit, 30)})
    result = github_api_json(f"/search/repositories?{qs}", token)
    rows: list[dict[str, Any]] = []
    if not result.get("ok"):
        return [
            {
                "kind": "source_scan",
                "source_id": source["id"],
                "source_type": source["type"],
                "trust": source.get("trust", "discovery"),
                "url": result.get("url"),
                "status": result.get("status"),
                "ok": False,
                "title": "GitHub search failed",
                "error": result.get("error"),
                "snippets": [],
                "risk_flags": [],
            }
        ]
    keywords = config.get("keywords") or DEFAULT_KEYWORDS
    max_chars = int(config.get("policy", {}).get("max_snippet_chars", 700))
    for item in result["payload"].get("items", [])[:limit]:
        text = normalize_ws(
            " ".join(
                str(item.get(key) or "")
                for key in ["full_name", "description", "language", "topics", "pushed_at", "html_url"]
            )
        )
        matched_filter = source_text_matches(source, text)
        snippets = extract_snippets(text, keywords, max_chars) or ([text] if text else [])
        row = {
            "kind": "source_scan",
            "source_id": source["id"],
            "source_type": source["type"],
            "trust": source.get("trust", "discovery"),
            "url": item.get("html_url"),
            "status": 200,
            "ok": matched_filter,
            "filter_miss": not matched_filter,
            "title": item.get("full_name"),
            "updated_at": item.get("pushed_at"),
            "stars": item.get("stargazers_count"),
            "snippets": snippets[:2],
            "risk_flags": risk_flags(text, config.get("risk_terms", [])),
        }
        if not matched_filter:
            row["error"] = "Result did not match source include filter."
        rows.append(row)
    return rows


def source_queries(source: dict[str, Any]) -> list[str]:
    if source.get("queries"):
        return [str(query) for query in source["queries"] if str(query).strip()]
    if source.get("query"):
        return [str(source["query"])]
    return []


def source_text_matches(source: dict[str, Any], text: str) -> bool:
    lowered = text.lower()
    must_include = [str(term).lower() for term in source.get("must_include", []) if str(term).strip()]
    must_include_any = [str(term).lower() for term in source.get("must_include_any", []) if str(term).strip()]
    if must_include and not all(term in lowered for term in must_include):
        return False
    if must_include_any and not any(term in lowered for term in must_include_any):
        return False
    return True


def missing_secret_scan(source: dict[str, Any], secret_name: str) -> list[dict[str, Any]]:
    return [
        {
            "kind": "source_scan",
            "source_id": source["id"],
            "source_type": source["type"],
            "trust": source.get("trust", "optional"),
            "url": source.get("url") or source.get("repo") or source.get("query") or source.get("id"),
            "status": None,
            "ok": False,
            "missing_secret": True,
            "title": "missing optional API key",
            "error": f"Set GitHub Actions secret {secret_name} to enable this source.",
            "snippets": [],
            "risk_flags": [],
        }
    ]


def result_scan(
    source: dict[str, Any],
    *,
    provider: str,
    query: str,
    title: str | None,
    url: str | None,
    text: str,
    status: int | None = 200,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_text = normalize_ws(text)
    match_text = " ".join([title or "", url or "", clean_text])
    matched_filter = source_text_matches(source, match_text)
    row = {
        "kind": "source_scan",
        "source_id": source["id"],
        "source_type": source["type"],
        "provider": provider,
        "trust": source.get("trust", "discovery"),
        "query": query,
        "url": url,
        "status": status,
        "ok": bool(url or clean_text) and matched_filter,
        "title": title or url or query,
        "filter_miss": not matched_filter,
        "snippets": [clean_text] if clean_text else [],
        "risk_flags": risk_flags(clean_text, source.get("risk_terms") or DEFAULT_RISK_TERMS),
    }
    if not matched_filter:
        row["error"] = "Result did not match source include filter."
    if extra:
        row.update(extra)
    return row


def provider_error_scan(source: dict[str, Any], provider: str, query: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "source_scan",
        "source_id": source["id"],
        "source_type": source["type"],
        "provider": provider,
        "trust": source.get("trust", "discovery"),
        "query": query,
        "url": result.get("url"),
        "status": result.get("status"),
        "ok": False,
        "title": f"{provider} search failed",
        "error": result.get("error"),
        "snippets": [],
        "risk_flags": [],
    }


def scan_brave_search(source: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    secret_name = source.get("required_secret", "BRAVE_SEARCH_API_KEY")
    api_key = os.environ.get(secret_name)
    if not api_key:
        return missing_secret_scan(source, secret_name)
    rows: list[dict[str, Any]] = []
    limit = int(source.get("limit", 10))
    for query in source_queries(source):
        qs = parse.urlencode(
            {
                "q": query,
                "count": min(limit, 20),
                "country": source.get("country", "us"),
                "search_lang": source.get("search_lang", "en"),
            }
        )
        result = fetch_json_get(
            f"https://api.search.brave.com/res/v1/web/search?{qs}",
            headers_extra={"X-Subscription-Token": api_key},
        )
        if not result.get("ok"):
            rows.append(provider_error_scan(source, "brave", query, result))
            continue
        payload = result["payload"]
        for item in payload.get("web", {}).get("results", [])[:limit]:
            text = " ".join(
                [
                    str(item.get("title") or ""),
                    str(item.get("description") or ""),
                    " ".join(str(s) for s in item.get("extra_snippets") or []),
                ]
            )
            rows.append(
                result_scan(
                    source,
                    provider="brave",
                    query=query,
                    title=item.get("title"),
                    url=item.get("url"),
                    text=text,
                    status=result.get("status"),
                    extra={"age": item.get("age")},
                )
            )
    return rows


def scan_tavily_search(source: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    secret_name = source.get("required_secret", "TAVILY_API_KEY")
    api_key = os.environ.get(secret_name)
    if not api_key:
        return missing_secret_scan(source, secret_name)
    rows: list[dict[str, Any]] = []
    limit = int(source.get("limit", 8))
    for query in source_queries(source):
        payload = {
            "query": query,
            "search_depth": source.get("search_depth", "basic"),
            "max_results": min(limit, 20),
            "include_answer": False,
            "include_raw_content": False,
            "topic": source.get("topic", "general"),
        }
        result = fetch_json_post(
            "https://api.tavily.com/search",
            payload,
            headers_extra={"Authorization": f"Bearer {api_key}"},
        )
        if not result.get("ok"):
            rows.append(provider_error_scan(source, "tavily", query, result))
            continue
        for item in result["payload"].get("results", [])[:limit]:
            text = " ".join([str(item.get("title") or ""), str(item.get("content") or "")])
            rows.append(
                result_scan(
                    source,
                    provider="tavily",
                    query=query,
                    title=item.get("title"),
                    url=item.get("url"),
                    text=text,
                    status=result.get("status"),
                    extra={"score": item.get("score")},
                )
            )
    return rows


def scan_exa_search(source: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    secret_name = source.get("required_secret", "EXA_API_KEY")
    api_key = os.environ.get(secret_name)
    if not api_key:
        return missing_secret_scan(source, secret_name)
    rows: list[dict[str, Any]] = []
    limit = int(source.get("limit", 8))
    for query in source_queries(source):
        payload = {
            "query": query,
            "type": source.get("search_type", "auto"),
            "numResults": min(limit, 25),
            "contents": {"highlights": True},
        }
        result = fetch_json_post("https://api.exa.ai/search", payload, headers_extra={"x-api-key": api_key})
        if not result.get("ok"):
            rows.append(provider_error_scan(source, "exa", query, result))
            continue
        for item in result["payload"].get("results", [])[:limit]:
            highlights = " ".join(str(value) for value in item.get("highlights") or [])
            text = " ".join([str(item.get("title") or ""), str(item.get("text") or ""), highlights])
            rows.append(
                result_scan(
                    source,
                    provider="exa",
                    query=query,
                    title=item.get("title"),
                    url=item.get("url"),
                    text=text,
                    status=result.get("status"),
                    extra={"published_date": item.get("publishedDate")},
                )
            )
    return rows


def scan_serpapi_search(source: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    secret_name = source.get("required_secret", "SERPAPI_API_KEY")
    api_key = os.environ.get(secret_name)
    if not api_key:
        return missing_secret_scan(source, secret_name)
    rows: list[dict[str, Any]] = []
    limit = int(source.get("limit", 8))
    for query in source_queries(source):
        qs = parse.urlencode({"engine": source.get("engine", "google"), "q": query, "api_key": api_key, "num": limit})
        result = fetch_json_get(f"https://serpapi.com/search.json?{qs}")
        if not result.get("ok"):
            rows.append(provider_error_scan(source, "serpapi", query, result))
            continue
        for item in result["payload"].get("organic_results", [])[:limit]:
            text = " ".join([str(item.get("title") or ""), str(item.get("snippet") or "")])
            rows.append(
                result_scan(
                    source,
                    provider="serpapi",
                    query=query,
                    title=item.get("title"),
                    url=item.get("link"),
                    text=text,
                    status=result.get("status"),
                    extra={"position": item.get("position")},
                )
            )
    return rows


def scan_youtube_search(source: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    secret_name = source.get("required_secret", "YOUTUBE_API_KEY")
    api_key = os.environ.get(secret_name)
    if not api_key:
        return missing_secret_scan(source, secret_name)
    rows: list[dict[str, Any]] = []
    limit = int(source.get("limit", 5))
    for query in source_queries(source):
        qs = parse.urlencode(
            {
                "part": "snippet",
                "q": query,
                "type": source.get("result_type", "video"),
                "order": source.get("order", "date"),
                "maxResults": min(limit, 50),
                "key": api_key,
            }
        )
        result = fetch_json_get(f"https://www.googleapis.com/youtube/v3/search?{qs}")
        if not result.get("ok"):
            rows.append(provider_error_scan(source, "youtube", query, result))
            continue
        for item in result["payload"].get("items", [])[:limit]:
            snippet = item.get("snippet") or {}
            video_id = (item.get("id") or {}).get("videoId")
            url = f"https://www.youtube.com/watch?v={video_id}" if video_id else None
            text = " ".join(
                [
                    str(snippet.get("title") or ""),
                    str(snippet.get("description") or ""),
                    str(snippet.get("channelTitle") or ""),
                ]
            )
            rows.append(
                result_scan(
                    source,
                    provider="youtube",
                    query=query,
                    title=snippet.get("title"),
                    url=url,
                    text=text,
                    status=result.get("status"),
                    extra={"published_at": snippet.get("publishedAt"), "channel": snippet.get("channelTitle")},
                )
            )
    return rows


def scan_huggingface_search(source: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    limit = int(source.get("limit", 10))
    repo_types = source.get("repo_types") or ["models", "datasets", "spaces"]
    for query in source_queries(source):
        for repo_type in repo_types:
            qs = parse.urlencode({"search": query, "limit": min(limit, 50), "full": "true"})
            result = fetch_json_get(f"https://huggingface.co/api/{repo_type}?{qs}")
            if not result.get("ok"):
                rows.append(provider_error_scan(source, f"huggingface_{repo_type}", query, result))
                continue
            payload = result.get("payload") or []
            for item in payload[:limit]:
                repo_id = item.get("modelId") or item.get("id") or item.get("datasetId")
                text = " ".join(
                    [
                        str(repo_id or ""),
                        str(item.get("pipeline_tag") or ""),
                        " ".join(str(tag) for tag in item.get("tags") or []),
                    ]
                )
                rows.append(
                    result_scan(
                        source,
                        provider=f"huggingface_{repo_type}",
                        query=query,
                        title=repo_id,
                        url=f"https://huggingface.co/{repo_id}" if repo_id else None,
                        text=text,
                        status=result.get("status"),
                        extra={"repo_type": repo_type, "downloads": item.get("downloads"), "likes": item.get("likes")},
                    )
                )
    return rows


def scan_arxiv_search(source: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    limit = int(source.get("limit", 5))
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for index, query in enumerate(source_queries(source)):
        qs = parse.urlencode(
            {
                "search_query": query,
                "start": 0,
                "max_results": min(limit, 20),
                "sortBy": source.get("sort_by", "submittedDate"),
                "sortOrder": source.get("sort_order", "descending"),
            }
        )
        result = fetch_text(f"https://export.arxiv.org/api/query?{qs}", accept="application/atom+xml")
        if not result.get("ok"):
            rows.append(provider_error_scan(source, "arxiv", query, result))
            continue
        try:
            root = ET.fromstring(result.get("text", ""))
        except ET.ParseError as exc:
            rows.append(provider_error_scan(source, "arxiv", query, {"error": str(exc), "status": result.get("status")}))
            continue
        for entry in root.findall("atom:entry", ns):
            title = normalize_ws(entry.findtext("atom:title", default="", namespaces=ns))
            url = normalize_ws(entry.findtext("atom:id", default="", namespaces=ns))
            summary = normalize_ws(entry.findtext("atom:summary", default="", namespaces=ns))
            rows.append(
                result_scan(
                    source,
                    provider="arxiv",
                    query=query,
                    title=title,
                    url=url,
                    text=f"{title} {summary}",
                    status=result.get("status"),
                    extra={
                        "published_at": normalize_ws(entry.findtext("atom:published", default="", namespaces=ns)),
                        "updated_at": normalize_ws(entry.findtext("atom:updated", default="", namespaces=ns)),
                    },
                )
            )
        if index < len(source_queries(source)) - 1:
            time.sleep(float(source.get("delay_seconds", 3)))
    return rows


def scan_stackexchange_search(source: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    limit = int(source.get("limit", 8))
    sites = source.get("sites") or ["stackoverflow"]
    key = os.environ.get(source.get("optional_secret", "STACKAPPS_KEY"), "")
    for query in source_queries(source):
        for site in sites:
            params = {
                "order": "desc",
                "sort": "activity",
                "q": query,
                "site": site,
                "pagesize": min(limit, 100),
                "filter": "default",
            }
            if key:
                params["key"] = key
            result = fetch_json_get(f"https://api.stackexchange.com/2.3/search/advanced?{parse.urlencode(params)}")
            if not result.get("ok"):
                rows.append(provider_error_scan(source, f"stackexchange_{site}", query, result))
                continue
            for item in result["payload"].get("items", [])[:limit]:
                text = " ".join([str(item.get("title") or ""), " ".join(str(tag) for tag in item.get("tags") or [])])
                rows.append(
                    result_scan(
                        source,
                        provider=f"stackexchange_{site}",
                        query=query,
                        title=item.get("title"),
                        url=item.get("link"),
                        text=text,
                        status=result.get("status"),
                        extra={"site": site, "score": item.get("score"), "answer_count": item.get("answer_count")},
                    )
                )
    return rows


def scan_rss_feed(source: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    urls = source.get("urls") or ([source["url"]] if source.get("url") else [])
    limit = int(source.get("limit", 20))
    for feed_url in urls:
        result = fetch_text(feed_url, accept="application/rss+xml,application/atom+xml,text/xml")
        if not result.get("ok"):
            rows.append(provider_error_scan(source, "rss", feed_url, result))
            continue
        try:
            root = ET.fromstring(result.get("text", ""))
        except ET.ParseError as exc:
            rows.append(provider_error_scan(source, "rss", feed_url, {"error": str(exc), "status": result.get("status")}))
            continue
        entries = list(root.findall(".//item")) + list(root.findall(".//{http://www.w3.org/2005/Atom}entry"))
        for entry in entries[:limit]:
            title = normalize_ws(entry.findtext("title") or entry.findtext("{http://www.w3.org/2005/Atom}title") or "")
            link = normalize_ws(entry.findtext("link") or entry.findtext("{http://www.w3.org/2005/Atom}id") or feed_url)
            description = normalize_ws(
                entry.findtext("description") or entry.findtext("summary") or entry.findtext("{http://www.w3.org/2005/Atom}summary") or ""
            )
            rows.append(
                result_scan(
                    source,
                    provider="rss",
                    query=feed_url,
                    title=title,
                    url=link,
                    text=f"{title} {description}",
                    status=result.get("status"),
                )
            )
    return rows


def scan_source(source: dict[str, Any], config: dict[str, Any], token: str | None) -> list[dict[str, Any]]:
    if not source.get("enabled", True):
        return [
            {
                "kind": "source_scan",
                "source_id": source["id"],
                "source_type": source["type"],
                "trust": source.get("trust", "disabled"),
                "url": source.get("url") or source.get("repo") or source.get("query"),
                "status": None,
                "ok": False,
                "disabled": True,
                "title": "disabled",
                "error": source.get("notes", "disabled"),
                "snippets": [],
                "risk_flags": [],
            }
        ]
    source_type = source["type"]
    if source_type == "web":
        return scan_web(source, config, token)
    if source_type == "github_repo":
        return scan_github_repo(source, config, token)
    if source_type == "github_search":
        return scan_github_search(source, config, token)
    if source_type == "brave_search":
        return scan_brave_search(source, config)
    if source_type == "tavily_search":
        return scan_tavily_search(source, config)
    if source_type == "exa_search":
        return scan_exa_search(source, config)
    if source_type == "serpapi_search":
        return scan_serpapi_search(source, config)
    if source_type == "youtube_search":
        return scan_youtube_search(source, config)
    if source_type == "huggingface_search":
        return scan_huggingface_search(source, config)
    if source_type == "arxiv_search":
        return scan_arxiv_search(source, config)
    if source_type == "stackexchange_search":
        return scan_stackexchange_search(source, config)
    if source_type == "rss_feed":
        return scan_rss_feed(source, config)
    return [
        {
            "kind": "source_scan",
            "source_id": source["id"],
            "source_type": source_type,
            "trust": source.get("trust", "unknown"),
            "url": source.get("url"),
            "status": None,
            "ok": False,
            "title": "unsupported source type",
            "error": f"Unsupported source type: {source_type}",
            "snippets": [],
            "risk_flags": [],
        }
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def load_existing_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.exists():
        return ids
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("id"):
                ids.add(str(payload["id"]))
    return ids


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_existing_ids(path)
    new_rows = [row for row in rows if row.get("id") not in existing]
    if not new_rows:
        return 0
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        for row in new_rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(new_rows)


def build_candidates(scans: list[dict[str, Any]], config: dict[str, Any], run_date: str) -> list[dict[str, Any]]:
    keywords = config.get("keywords") or DEFAULT_KEYWORDS
    candidates: list[dict[str, Any]] = []
    for scan in scans:
        if not scan.get("ok") or scan.get("risk_flags"):
            continue
        for snippet in scan.get("snippets") or []:
            score = score_snippet(snippet, keywords, str(scan.get("trust", "")))
            if score <= 0:
                continue
            candidates.append(
                {
                    "id": stable_id(str(scan.get("url", "")), snippet),
                    "date_found": run_date,
                    "status": "candidate",
                    "source_id": scan.get("source_id"),
                    "source_type": scan.get("source_type"),
                    "trust": scan.get("trust"),
                    "source_url": scan.get("url"),
                    "title": scan.get("title"),
                    "score": score,
                    "snippet": snippet,
                    "review_note": "Promote manually only after license/provenance check and Seedance quality-gate rewrite.",
                }
            )
    candidates.sort(key=lambda item: (-int(item["score"]), str(item["source_id"])))
    return candidates


def write_report(scans: list[dict[str, Any]], candidates: list[dict[str, Any]], run_date: str, appended_count: int) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    ok_count = sum(1 for scan in scans if scan.get("ok"))
    risky_count = sum(1 for scan in scans if scan.get("risk_flags"))
    disabled_count = sum(1 for scan in scans if scan.get("disabled"))

    report_lines = [
        f"# Seedance Prompt Scout - {run_date}",
        "",
        "## Summary",
        "",
        f"- Sources scanned: {len(scans)}",
        f"- OK sources/items: {ok_count}",
        f"- Disabled sources/items: {disabled_count}",
        f"- Risk-flagged sources/items: {risky_count}",
        f"- Candidate snippets this run: {len(candidates)}",
        f"- Newly appended candidates: {appended_count}",
        "",
        "## Top Candidates",
        "",
    ]
    for item in candidates[:20]:
        report_lines.extend(
            [
                f"### {item['title'] or item['source_id']}",
                "",
                f"- Score: {item['score']}",
                f"- Source: {item['source_url']}",
                f"- Trust: {item['trust']}",
                "",
                "> " + str(item["snippet"]).replace("\n", " ")[:900],
                "",
            ]
        )
    report_lines.extend(["## Source Status", ""])
    for scan in scans:
        flags = ", ".join(scan.get("risk_flags") or [])
        report_lines.append(
            f"- `{scan.get('source_id')}` ok={scan.get('ok')} status={scan.get('status')} "
            f"disabled={bool(scan.get('disabled'))} risk=[{flags}] url={scan.get('url')}"
        )
    (REPORTS_DIR / f"{run_date}_seedance_prompt_scout.md").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8", newline="\n"
    )

    prompt_lines = [
        f"# Candidate Prompt Index - {run_date}",
        "",
        "These are raw research candidates, not approved best prompts.",
        "",
    ]
    for item in candidates[:50]:
        prompt_lines.extend(
            [
                f"## {item['title'] or item['source_id']}",
                "",
                f"- Score: {item['score']}",
                f"- Source: {item['source_url']}",
                f"- Status: {item['status']}",
                "",
                str(item["snippet"]),
                "",
            ]
        )
    (PROMPTS_DIR / f"{run_date}_candidate_index.md").write_text(
        "\n".join(prompt_lines) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Load config and print planned sources without network.")
    args = parser.parse_args()

    config = load_config()
    enabled_sources = [src for src in config.get("sources", []) if src.get("enabled", True)]
    if args.dry_run:
        print(f"Config OK: {len(config.get('sources', []))} sources, {len(enabled_sources)} enabled")
        for source in config.get("sources", []):
            state = "enabled" if source.get("enabled", True) else "disabled"
            print(f"- {source['id']} ({source['type']}, {state})")
        return 0

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    run_date = dt.datetime.now(dt.UTC).date().isoformat()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    scans: list[dict[str, Any]] = []
    for source in config.get("sources", []):
        scans.extend(scan_source(source, config, token))

    for scan in scans:
        scan["run_date"] = run_date
        scan["id"] = stable_id(str(scan.get("source_id")), str(scan.get("url")), run_date)

    candidates = build_candidates(scans, config, run_date)
    write_jsonl(DATA_DIR / f"{run_date}_sources.jsonl", scans)
    appended_count = append_jsonl(DATA_DIR / "candidate_prompts.jsonl", candidates)
    write_report(scans, candidates, run_date, appended_count)
    print(f"Seedance prompt scout complete: {len(scans)} scans, {len(candidates)} candidates, {appended_count} appended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
