import socket
import pytest

from scripts.safe_source_collector import CollectionError, sanitize, validate_public_url


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://localhost/test", "ftp://example.com/file"])
def test_collector_rejects_unsafe_schemes_and_hosts(url):
    with pytest.raises(CollectionError): validate_public_url(url)


def test_collector_rejects_private_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))])
    with pytest.raises(CollectionError): validate_public_url("https://example.com/doc")


def test_collector_accepts_only_public_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
    assert validate_public_url("https://example.com/doc") == "https://example.com/doc"


def test_html_sanitizer_removes_scripts_and_navigation():
    html = b"<nav>menu</nav><main><h1>Title</h1><p>Useful text</p><script>steal()</script></main>"
    text = sanitize(html, "text/html", "utf-8")
    assert "Useful text" in text and "steal" not in text and "menu" not in text
