from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from core.config import Settings

CROSSREF_API_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 503}
MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 1.0


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _format_date(date_field: dict | None) -> str:
    if not date_field:
        return ""
    parts = date_field.get("date-parts")
    if not parts or not parts[0]:
        return ""
    parts = parts[0]
    year = parts[0] if len(parts) > 0 else None
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    if year is None:
        return ""
    return f"{year:04d}-{month:02d}-{day:02d}"


def _extract_authors(item: dict) -> list[str]:
    authors = []
    for author in item.get("author", []) or []:
        given = author.get("given", "").strip()
        family = author.get("family", "").strip()
        name = f"{given} {family}".strip()
        if name:
            authors.append(name)
    return authors


def _extract_pdf_url(item: dict) -> str:
    for link in item.get("link", []) or []:
        if link.get("content-type") == "application/pdf":
            return link.get("URL", "")
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord.

    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    items = payload.get("message", {}).get("items", []) or []
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        titles = item.get("title") or []
        title = _clean_text(titles[0]) if titles else ""
        abstract = _clean_text(item.get("abstract", ""))

        if not doi or not title or not abstract:
            continue

        categories = [c for c in (item.get("subject") or []) if c]
        published = (
            _format_date(item.get("published"))
            or _format_date(item.get("published-print"))
            or _format_date(item.get("published-online"))
            or _format_date(item.get("created"))
        )
        updated = _format_date(item.get("indexed")) or _format_date(item.get("deposited")) or published

        record = PaperRecord(
            paper_id=doi,
            title=title,
            summary=abstract,
            authors=_extract_authors(item),
            categories=categories,
            primary_category=categories[0] if categories else "",
            published=published,
            updated=updated,
            abs_url=item.get("URL", "") or f"https://doi.org/{doi}",
            pdf_url=_extract_pdf_url(item),
            comment=item.get("container-title", [""])[0] if item.get("container-title") else "",
        )
        records.append(record)

    return records


def _request_with_retry(params: dict) -> requests.Response:
    backoff = INITIAL_BACKOFF_SECONDS
    headers = {"User-Agent": "K4-Day10-Data-Pipeline/1.0 (mailto:krazyrv1402@gmail.com)"}

    for attempt in range(1, MAX_RETRIES + 1):
        response = requests.get(CROSSREF_API_URL, params=params, headers=headers, timeout=30)

        if response.status_code not in RETRYABLE_STATUS_CODES:
            response.raise_for_status()
            return response

        if attempt == MAX_RETRIES:
            response.raise_for_status()

        retry_after = response.headers.get("Retry-After")
        sleep_seconds = float(retry_after) if retry_after else backoff
        time.sleep(sleep_seconds)
        backoff *= 2

    raise RuntimeError("Unreachable: retry loop exhausted without returning or raising.")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref API, luu raw response, parse thanh records.

    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    params = {
        "query.bibliographic": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    response = _request_with_retry(params)
    payload = response.json()

    raw_response_path = settings.paths.raw_api_response
    raw_response_path.parent.mkdir(parents=True, exist_ok=True)
    raw_response_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    records = parse_crossref_payload(payload)

    raw_records_path = settings.paths.raw_records_json
    raw_records_path.parent.mkdir(parents=True, exist_ok=True)
    raw_records_path.write_text(
        json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [PaperRecord(**item) for item in raw]
