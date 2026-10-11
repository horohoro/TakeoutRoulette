"""
Polite Web Scraper with Disk Caching, Rate Limiting, and User-Agent Rotation
"""
import time
import random
import hashlib
import requests
from pathlib import Path
from typing import Optional, Dict
from config import CACHE_DIR, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX, HTTP_TIMEOUT, USER_AGENTS

class PoliteScraper:
    def __init__(self, cache_dir: Optional[Path] = None, delay_min: float = REQUEST_DELAY_MIN, delay_max: float = REQUEST_DELAY_MAX):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.session = requests.Session()
        self.last_request_time = 0.0

    def _get_cache_path(self, url: str) -> Path:
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{url_hash}.html"

    def _rate_limit_wait(self):
        elapsed = time.time() - self.last_request_time
        target_delay = random.uniform(self.delay_min, self.delay_max)
        if elapsed < target_delay:
            time.sleep(target_delay - elapsed)

    def get(self, url: str, use_cache: bool = True, max_age_days: int = 14) -> str:
        cache_path = self._get_cache_path(url)
        
        # Check cache
        if use_cache and cache_path.exists():
            mtime = cache_path.stat().st_mtime
            age_days = (time.time() - mtime) / (24 * 3600)
            if age_days < max_age_days:
                return cache_path.read_text(encoding="utf-8", errors="replace")

        # Rate limit before making outgoing HTTP request
        self._rate_limit_wait()

        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }

        retries = 3
        backoff = 3.0
        while retries > 0:
            try:
                resp = self.session.get(url, headers=headers, timeout=HTTP_TIMEOUT)
                self.last_request_time = time.time()
                
                if resp.status_code == 200:
                    text = resp.text
                    cache_path.write_text(text, encoding="utf-8", errors="replace")
                    return text
                elif resp.status_code in (429, 503):
                    print(f"[RateLimit] HTTP {resp.status_code} for {url}. Backing off {backoff:.1f}s...")
                    time.sleep(backoff)
                    backoff *= 2
                    retries -= 1
                else:
                    print(f"[HTTP {resp.status_code}] Failed for {url}")
                    return ""
            except Exception as e:
                print(f"[Scrape Error] {e} on {url}. Retrying...")
                time.sleep(backoff)
                retries -= 1

        return ""

scraper_instance = PoliteScraper()
