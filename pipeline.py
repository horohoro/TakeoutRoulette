"""
TakeoutRoulette Pipeline
Fetches, deduplicates, enriches, and stores restaurants supporting takeout.
"""
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from config import DATA_DIR, DEFAULT_STATION, STATION_PRESETS
from scrapers.tabelog import TabelogScraper

class Pipeline:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.scraper = TabelogScraper()

    def run_hunt(
        self,
        station_id: Optional[str] = None,
        pages: int = 5,
        enrich_all: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Runs the discovery and enrichment pipeline for the designated station.
        """
        if station_id is None:
            station_id = DEFAULT_STATION["id"]
        station_conf = STATION_PRESETS.get(station_id, DEFAULT_STATION)
        print(f"\n==========================================")
        print(f"🎯 HUNTING TAKEOUT SPOTS FOR: {station_conf['name']}")
        print(f"Pages to crawl: {pages} | Enrich details: {enrich_all}")
        print(f"==========================================\n")

        all_candidates: Dict[str, Dict[str, Any]] = {}

        # 1. Fetch top-rated takeout spots (SrtT=rt)
        for p in range(1, pages + 1):
            items = self.scraper.scrape_station_page(station_conf, page=p, sort="rt")
            for item in items:
                r_id = item["id"]
                if r_id not in all_candidates:
                    all_candidates[r_id] = item

        # 2. Fetch popular/high-review takeout spots (SrtT=rvcn) for everyday gems
        for p in range(1, 3):
            items_pop = self.scraper.scrape_station_page(station_conf, page=p, sort="rvcn")
            for item in items_pop:
                r_id = item["id"]
                if r_id not in all_candidates:
                    all_candidates[r_id] = item

        print(f"\n[Pipeline] Discovered {len(all_candidates)} unique takeout restaurants.")

        # 3. Enrich with detailed opening hours, addresses, coordinates
        enriched_list = []
        candidates_list = list(all_candidates.values())
        
        for idx, item in enumerate(candidates_list, 1):
            print(f"[{idx}/{len(candidates_list)}] Enriching: {item['name']} ({item['url']})")
            if enrich_all:
                try:
                    enriched = self.scraper.enrich_restaurant_details(item, station_conf)
                except Exception as e:
                    print(f"  Warning: failed to enrich {item['name']}: {e}")
                    enriched = item
            else:
                enriched = item

            # Filter out places beyond 1,200m from station (comfort walking limit)
            dist_m = enriched.get("distance_meters")
            if dist_m and dist_m > 1200:
                print(f"  Skipping {enriched['name']}: {dist_m}m is too far (>1200m)")
                continue

            enriched_list.append(enriched)

        # Sort by rating descending
        enriched_list.sort(key=lambda x: (x.get("rating") or 0.0, -x.get("distance_meters", 9999)), reverse=True)

        # Save to JSON
        station_slug = station_conf.get("id", "station")
        out_file = self.data_dir / f"restaurants_{station_slug}.json"
        main_file = self.data_dir / "restaurants.json"

        payload = {
            "station": station_conf,
            "count": len(enriched_list),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S JST"),
            "restaurants": enriched_list
        }

        out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        main_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\n✅ Successfully saved {len(enriched_list)} restaurants to:")
        print(f"  - {out_file}")
        print(f"  - {main_file}")

        return enriched_list
