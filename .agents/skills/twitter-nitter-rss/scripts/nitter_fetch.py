#!/usr/bin/env python3
"""Fetch and normalize attack-alert candidates from keyless Nitter RSS feeds.

Scripts fetch and normalize evidence only. The agent makes the final
protocol/chain/confidence judgment from the normalized candidates.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

STATE_FILE = Path("./twitter-events/state.json")
DEFAULT_INSTANCES = ("https://nitter.net",)
USER_AGENT = "Mozilla/5.0 (compatible; tx2poc-nitter-rss/1.0)"
ACCEPT = "application/rss+xml, application/xml, text/xml"
DC_CREATOR = "{http://purl.org/dc/elements/1.1/}creator"

TX_HASH_RE = re.compile(r"\b0x[0-9a-fA-F]{64}\b")
EXPLORER_TX_RE = re.compile(r"https?://[^\s\"'<>]*?/tx/(0x[0-9a-fA-F]{64})", re.IGNORECASE)
HREF_RE = re.compile(r'href="(https?://[^"]+)"', re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")

ATTACK_KEYWORDS = (
    "exploit",
    "hack",
    "drain",
    "attacker",
    "attack",
    "stolen",
    "theft",
    "flash loan",
    "flashloan",
    "reentrancy",
    "oracle manipulation",
    "price manipulation",
    "suspicious",
    "rug",
    "bridge",
    "compromise",
    "loss",
    "incident",
    "vulnerab",
)

# Explorer host -> chain hint. Used only as a fallback; explicit text wins.
EXPLORER_CHAIN = {
    "etherscan.io": "ethereum",
    "bscscan.com": "bsc",
    "polygonscan.com": "polygon",
    "arbiscan.io": "arbitrum",
    "basescan.org": "base",
    "optimistic.etherscan.io": "optimism",
    "snowtrace.io": "avalanche",
    "snowscan.xyz": "avalanche",
    "ftmscan.com": "fantom",
    "gnosisscan.io": "gnosis",
    "solscan.io": "solana",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def parse_time(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_pubdate(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def html_to_text(value: str | None) -> str:
    if not value:
        return ""
    text = TAG_RE.sub(" ", value)
    text = html.unescape(text)
    return WHITESPACE_RE.sub(" ", text).strip()


def extract_links(description: str | None) -> list[str]:
    if not description:
        return []
    seen: list[str] = []
    for link in HREF_RE.findall(description):
        clean = html.unescape(link)
        if clean not in seen:
            seen.append(clean)
    return seen


def extract_tx_hashes(text: str, links: list[str]) -> list[str]:
    found: list[str] = []
    for source in (text, *links):
        for match in TX_HASH_RE.findall(source or ""):
            normalized = match.lower()
            if normalized not in found:
                found.append(normalized)
    for url in links:
        for match in EXPLORER_TX_RE.findall(url):
            normalized = match.lower()
            if normalized not in found:
                found.append(normalized)
    return found


def detect_keywords(text: str) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in ATTACK_KEYWORDS if keyword in lowered]


def chain_hint(links: list[str]) -> str:
    for url in links:
        for host, chain in EXPLORER_CHAIN.items():
            if host in url:
                return chain
    return "unknown"


def canonical_tweet_url(link: str | None) -> str | None:
    if not link:
        return None
    cleaned = link.split("#", 1)[0]
    match = re.search(r"https?://[^/]+(/.+/status/\d+)", cleaned)
    if match:
        return "https://x.com" + match.group(1)
    return cleaned


def http_get(url: str, timeout: int = 25) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": ACCEPT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def feed_path(handle: str, with_replies: bool) -> str:
    handle = handle.lstrip("@")
    return f"/{handle}/with_replies/rss" if with_replies else f"/{handle}/rss"


def parse_feed(xml_bytes: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        def text(tag: str) -> str | None:
            element = item.find(tag)
            return element.text if element is not None else None

        items.append(
            {
                "title": text("title"),
                "link": text("link"),
                "pubDate": text("pubDate"),
                "creator": text(DC_CREATOR),
                "description": text("description"),
            }
        )
    return items


def fetch_account(
    instances: list[str], handle: str, with_replies: bool
) -> tuple[list[dict[str, Any]], str]:
    errors: list[str] = []
    for instance in instances:
        url = instance.rstrip("/") + feed_path(handle, with_replies)
        try:
            return parse_feed(http_get(url)), instance
        except (RuntimeError, ET.ParseError) as exc:
            errors.append(f"{instance}: {exc}")
    raise RuntimeError(f"All Nitter instances failed for @{handle}: {'; '.join(errors)}")


def normalize_item(account: str, item: dict[str, Any]) -> dict[str, Any]:
    description = item.get("description")
    text = html_to_text(item.get("title")) or html_to_text(description)
    body_text = html_to_text(description)
    combined = f"{text} {body_text}".strip()
    links = extract_links(description)
    external_links = [link for link in links if "nitter" not in link and "/status/" not in link]
    tx_hashes = extract_tx_hashes(combined, links)
    keywords = detect_keywords(combined)
    return {
        "account": account.lstrip("@"),
        "author": (item.get("creator") or "").lstrip("@") or account.lstrip("@"),
        "tweet_url": canonical_tweet_url(item.get("link")),
        "posted_at": format_time(parse_pubdate(item.get("pubDate"))) if parse_pubdate(item.get("pubDate")) else None,
        "text": combined,
        "tx_hashes": tx_hashes,
        "links": external_links,
        "chain_hint": chain_hint(links),
        "matched_keywords": keywords,
    }


def in_window(posted: datetime | None, since: datetime, until: datetime) -> bool:
    return posted is not None and since < posted <= until


def is_candidate(normalized: dict[str, Any], keep_all: bool) -> bool:
    if keep_all:
        return True
    return bool(normalized["tx_hashes"]) or bool(normalized["matched_keywords"])


def scan(
    accounts: list[str],
    instances: list[str],
    since: datetime,
    until: datetime,
    with_replies: bool,
    keep_all: bool,
) -> dict[str, Any]:
    alerts: list[dict[str, Any]] = []
    sources: dict[str, str] = {}
    failures: dict[str, str] = {}
    for account in accounts:
        try:
            items, instance = fetch_account(instances, account, with_replies)
        except RuntimeError as exc:
            failures[account.lstrip("@")] = str(exc)
            continue
        sources[account.lstrip("@")] = instance
        for item in items:
            posted = parse_pubdate(item.get("pubDate"))
            if not in_window(posted, since, until):
                continue
            normalized = normalize_item(account, item)
            if is_candidate(normalized, keep_all):
                alerts.append(normalized)
    alerts.sort(key=lambda alert: alert.get("posted_at") or "")
    return {
        "window": {"since": format_time(since), "until": format_time(until)},
        "accounts": [account.lstrip("@") for account in accounts],
        "instances_used": sources,
        "failures": failures,
        "alert_count": len(alerts),
        "alerts": alerts,
    }


def load_state() -> dict[str, Any]:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def resolve_list(cli_value: str | None, state_key: str, default: tuple[str, ...]) -> list[str]:
    if cli_value:
        return [token.strip() for token in cli_value.split(",") if token.strip()]
    state_value = load_state().get(state_key)
    if isinstance(state_value, list) and state_value:
        return [str(token).strip() for token in state_value if str(token).strip()]
    return list(default)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch attack-alert candidates from Nitter RSS.")
    parser.add_argument("--since", required=True, help="last_check_time (ISO 8601). Keep posts strictly after this.")
    parser.add_argument("--until", required=True, help="check_started_at (ISO 8601). Keep posts up to and including this.")
    parser.add_argument("--accounts", help="Comma-separated handles. Defaults to state.json accounts[].")
    parser.add_argument("--instances", help="Comma-separated Nitter base URLs (failover order). Defaults to state.json nitter_instances[] or nitter.net.")
    parser.add_argument("--with-replies", action="store_true", help="Use the with_replies feed to capture self-threads.")
    parser.add_argument("--all", action="store_true", help="Keep every in-window post, not just attack candidates.")
    args = parser.parse_args()

    accounts = resolve_list(args.accounts, "accounts", ())
    if not accounts:
        print("No accounts configured. Pass --accounts or set accounts[] in twitter-events/state.json.", file=sys.stderr)
        return 2
    if any(account.lstrip("@") in {"foo", "bar", "example"} for account in accounts):
        print("Placeholder accounts detected. Ask the user which accounts to monitor.", file=sys.stderr)
        return 2

    instances = resolve_list(args.instances, "nitter_instances", DEFAULT_INSTANCES)
    result = scan(
        accounts=accounts,
        instances=instances,
        since=parse_time(args.since),
        until=parse_time(args.until),
        with_replies=args.with_replies,
        keep_all=args.all,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result.get("failures") else 0


if __name__ == "__main__":
    raise SystemExit(main())
