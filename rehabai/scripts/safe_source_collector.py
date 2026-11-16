"""Bounded public-source collector for the RehabAI corpus.

The collector is not a crawler: it fetches one explicitly supplied URL. It
blocks local/private targets, validates redirects and MIME types, caps response
size, sanitizes HTML without executing JavaScript, and records provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_ai" / "raw"
CACHE = ROOT / "data_ai" / ".cache"
ALLOWED_DOMAINS = {"rehab", "software", "nutrition", "conversation", "safety"}
ALLOWED_MIME = {"text/html", "text/plain", "application/xhtml+xml"}
MAX_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 15
MAX_REDIRECTS = 3
USER_AGENT = "RehabAIResearchBot"


class CollectionError(RuntimeError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail); self.code = code


def validate_public_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise CollectionError("NEEDS_VERIFICATION", "Only credential-free HTTP/HTTPS URLs are accepted")
    host = parsed.hostname.casefold().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise CollectionError("NEEDS_VERIFICATION", "Local hosts are blocked")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise CollectionError("PROVIDER_UNAVAILABLE", f"DNS resolution failed: {exc}") from exc
    if not addresses:
        raise CollectionError("PROVIDER_UNAVAILABLE", "Host did not resolve")
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%")[0])
        if not ip.is_global:
            raise CollectionError("NEEDS_VERIFICATION", f"Non-public address is blocked: {ip}")
    return urllib.parse.urlunsplit(parsed)


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__(); self.count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        self.count += 1
        if self.count > MAX_REDIRECTS:
            raise CollectionError("PROVIDER_UNAVAILABLE", "Redirect limit exceeded")
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class TextExtractor(HTMLParser):
    SKIP = {"script", "style", "nav", "footer", "form", "noscript", "svg"}
    def __init__(self):
        super().__init__(); self.depth = 0; self.parts: list[str] = []
    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        if tag.casefold() in self.SKIP: self.depth += 1
    def handle_endtag(self, tag):  # noqa: ANN001
        if tag.casefold() in self.SKIP and self.depth: self.depth -= 1
    def handle_data(self, data: str):
        if not self.depth and data.strip(): self.parts.append(data.strip())


def sanitize(body: bytes, mime: str, charset: str | None) -> str:
    try: text = body.decode(charset or "utf-8", errors="replace")
    except LookupError: text = body.decode("utf-8", errors="replace")
    if mime in {"text/html", "application/xhtml+xml"}:
        parser = TextExtractor()
        try: parser.feed(text)
        except Exception as exc: raise CollectionError("PARSE_FAILED", str(exc)) from exc
        text = "\n".join(parser.parts)
    text = unescape(text).replace("\x00", "")
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", text)).strip()


def check_robots(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    robots_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))
    validate_public_url(robots_url)
    opener = urllib.request.build_opener(SafeRedirectHandler())
    request = urllib.request.Request(robots_url, headers={"User-Agent": f"{USER_AGENT}/1.0"})
    parser = urllib.robotparser.RobotFileParser(); parser.set_url(robots_url)
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            if response.headers.get_content_type().casefold() not in {"text/plain", "text/html"}:
                raise CollectionError("NEEDS_VERIFICATION", "robots.txt has an unsupported MIME type")
            body = response.read(256 * 1024 + 1)
            if len(body) > 256 * 1024:
                raise CollectionError("NEEDS_VERIFICATION", "robots.txt exceeds size limit")
            parser.parse(body.decode(response.headers.get_content_charset() or "utf-8", errors="replace").splitlines())
    except urllib.error.HTTPError as exc:
        if exc.code in {404, 410}:
            return
        raise CollectionError("NEEDS_VERIFICATION", f"robots.txt check failed: HTTP {exc.code}") from exc
    except CollectionError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise CollectionError("NEEDS_VERIFICATION", f"robots.txt could not be verified: {exc}") from exc
    if not parser.can_fetch(USER_AGENT, url):
        raise CollectionError("NEEDS_VERIFICATION", "robots.txt does not allow this URL")


def fetch(url: str) -> tuple[str, str, str]:
    url = validate_public_url(url)
    cache_key = hashlib.sha256(url.encode()).hexdigest()
    cache_path = CACHE / f"{cache_key}.json"
    if cache_path.exists():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        return cached["text"], cached["mime"], cached["final_url"]
    check_robots(url)
    time.sleep(1)  # conservative per-host delay; this collector fetches one URL only
    opener = urllib.request.build_opener(SafeRedirectHandler())
    request = urllib.request.Request(url, headers={"User-Agent": f"{USER_AGENT}/1.0 (+bounded single-source fetch)"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
                final_url = validate_public_url(response.geturl())
                mime = response.headers.get_content_type().casefold()
                if mime not in ALLOWED_MIME: raise CollectionError("PARSE_FAILED", f"Unsupported MIME: {mime}")
                if int(response.headers.get("Content-Length", "0") or 0) > MAX_BYTES: raise CollectionError("PARSE_FAILED", "Response exceeds size limit")
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES: raise CollectionError("PARSE_FAILED", "Response exceeds size limit")
                text = sanitize(body, mime, response.headers.get_content_charset())
                if not text: raise CollectionError("PARSE_FAILED", "No usable text")
                CACHE.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps({"text": text, "mime": mime, "final_url": final_url}, ensure_ascii=False), encoding="utf-8")
                return text, mime, final_url
        except CollectionError: raise
        except (TimeoutError, socket.timeout) as exc: last_error = exc; code = "FETCH_TIMEOUT"
        except (urllib.error.URLError, OSError) as exc: last_error = exc; code = "PROVIDER_UNAVAILABLE"
        if attempt < 2: time.sleep(2 ** attempt)
    raise CollectionError(code, str(last_error))


def collect(args: argparse.Namespace) -> dict:
    if args.domain not in ALLOWED_DOMAINS: raise CollectionError("NEEDS_VERIFICATION", "Unsupported domain")
    license_value = args.license.strip()
    status = "NEEDS_VERIFICATION" if license_value.casefold() in {"", "unknown", "unclear"} else "VERIFIED"
    text, mime, final_url = fetch(args.url)
    source_id = "SRC_" + hashlib.sha256(final_url.encode()).hexdigest()[:12].upper()
    target = RAW / args.domain / f"{source_id}.txt"; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    metadata = {"source_id": source_id, "domain": args.domain, "title": args.title, "publisher": args.publisher, "authors": [], "year": None, "url": final_url, "doi": args.doi or None, "license": license_value or "unknown", "access_type": args.access_type, "retrieved_at": datetime.now(timezone.utc).isoformat(), "trust_tier": args.trust_tier, "status": status, "mime": mime, "content_hash": hashlib.sha256(text.encode()).hexdigest(), "review_status": "RAW"}
    metadata_path = target.with_suffix(".metadata.json"); metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True); parser.add_argument("--domain", required=True, choices=sorted(ALLOWED_DOMAINS))
    parser.add_argument("--title", required=True); parser.add_argument("--publisher", required=True); parser.add_argument("--license", default="unknown")
    parser.add_argument("--access-type", default="public_page", choices=["public_page", "open_access", "abstract_only"]); parser.add_argument("--trust-tier", default="B", choices=["A", "B", "C"]); parser.add_argument("--doi", default="")
    args = parser.parse_args()
    try: print(json.dumps(collect(args), ensure_ascii=False, indent=2)); return 0
    except CollectionError as exc: print(json.dumps({"status": exc.code, "detail": str(exc)}, ensure_ascii=False)); return 2


if __name__ == "__main__":
    raise SystemExit(main())
