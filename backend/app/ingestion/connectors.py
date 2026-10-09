from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from html import unescape
import re
import httpx
from urllib.parse import urlparse
from dataclasses import dataclass, field
from typing import Protocol

class NewsProvider(Protocol):
    name: str
    async def fetch(self) -> list[dict]: ...

@dataclass
class ProviderStatus:
    name: str
    configured: bool = False
    last_success: str | None = None
    last_attempt: str | None = None
    last_error: str | None = None
    articles_ingested: int = 0
    source_status: str = "NOT_CONFIGURED"

PROVIDER_STATUS: dict[str, ProviderStatus] = {}

class GDELTProvider:
    name = "GDELT"
    def __init__(self, fetcher=None): self.fetcher=fetcher or fetch_gdelt
    async def fetch(self): return await self.fetcher()

class RSSProvider:
    def __init__(self, name: str, url: str, fetcher=None): self.name, self.url, self.fetcher = name, url, fetcher or fetch_rss
    async def fetch(self): return await self.fetcher(self.url, source_name=self.name)

class DemoProvider:
    name = "DemoProvider"
    async def fetch(self): return fetch_sample_social()

def record_provider_result(name: str, configured: bool, count: int = 0, error: str | None = None):
    from datetime import datetime, timezone
    status = PROVIDER_STATUS.setdefault(name, ProviderStatus(name))
    status.configured = configured
    status.last_attempt = datetime.now(timezone.utc).isoformat()
    status.last_error = error
    status.articles_ingested = count
    status.source_status = "FAILED" if error else ("LIVE" if configured else "NOT_CONFIGURED")
    if configured and not error:
        status.last_success = datetime.now(timezone.utc).isoformat()

async def fetch_gdelt(limit=25):
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {"query":"(\"financial markets\" OR bank OR credit OR stock OR earnings OR bond) sourceCountry:US", "mode":"ArtList", "format":"json", "maxrecords":limit, "sort":"DateDesc"}
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.get(url, params=params); response.raise_for_status(); data = response.json()
    out=[]
    for row in data.get("articles", []):
        out.append({"title":row.get("title", "Untitled"),"text":row.get("title", ""),"source":f"GDELT · {row.get('domain','global news')}","source_url":row.get("url", ""),"published_at":row.get("seendate", "")})
    return out

async def fetch_rss(url, limit=25, source_name=None):
    if not url: return []
    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
        response = await client.get(url); response.raise_for_status()
    root=ET.fromstring(response.text); out=[]
    for item in root.findall(".//item")[:limit]:
        title=item.findtext("title", "Untitled"); desc=item.findtext("description", "")
        source_host=urlparse(url).netloc.lower().removeprefix("www.")
        clean_desc = re.sub(r"<[^>]+>"," ",unescape(desc))
        clean_desc = re.sub(r"\s+"," ",clean_desc).strip()
        out.append({"title":title,"text":f"{title}. {clean_desc}"[:3000],"source":source_name or f"RSS · {source_host or 'configured feed'}","source_url":item.findtext("link", ""),"published_at":item.findtext("pubDate", "")})
    return out

def fetch_sample_social():
    sample_file = Path(__file__).resolve().parents[3] / "data" / "sample_social" / "sample_posts.json"
    posts = json.loads(sample_file.read_text())
    return [{"title": f"Social post · {p['entity']}", "text": p["text"], "source": p["source"], "source_url": "", "published_at": ""} for p in posts]
