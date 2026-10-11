"""
Tabelog Scraper & Parser for Takeout-Supporting Restaurants
Extracts ratings, menus, genres, distances, addresses, contacts, and opening hours.
"""
import re
import json
import urllib.parse
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from scrapers.base import scraper_instance
from enrichers.hours_parser import parse_opening_hours
from enrichers.geo import compute_distance_info

# Common cuisine genre mappings into standard categories
CUISINE_CATEGORY_MAP = {
    'bento': ['弁当', '仕出し', '惣菜', 'デリカテッセン', 'テイクアウト'],
    'ramen_noodles': ['ラーメン', 'つけ麺', '油そば', 'うどん', 'そば', '中華麺'],
    'meat_bbq': ['焼肉', 'ホルモン', 'ステーキ', 'ハンバーグ', '牛丼', '肉料理'],
    'yakitori_izakaya': ['居酒屋', '焼き鳥', '串焼き', '鳥料理', 'もつ鍋', 'おでん', 'バル'],
    'curry': ['カレー', 'インドカレー', '欧風カレー', 'スープカレー', 'ネパール料理'],
    'chinese': ['中華料理', '飲茶・点心', '餃子', '台湾料理', '四川料理'],
    'japanese': ['日本料理', '和食', 'うなぎ', '割烹', '海鮮', '天ぷら', '郷土料理'],
    'sushi': ['寿司', '回転寿司', '海鮮丼'],
    'western_italian': ['イタリアン', 'パスタ', 'ピザ', 'フレンチ', 'ハンバーガー', '洋食', 'カフェ', 'パン']
}

def parse_budget_bounds(budget_str: str) -> tuple[Optional[int], Optional[int]]:
    """Parses Tabelog budget strings like '～￥999', '￥1,000～￥1,999' into integer (min, max)."""
    if not budget_str or budget_str == "-":
        return None, None
    s = budget_str.replace(",", "").replace("￥", "").replace("円", "").strip()
    m1 = re.match(r"^[～~](\d+)$", s)
    if m1:
        return 0, int(m1.group(1))
    m2 = re.match(r"^(\d+)[～~](\d+)$", s)
    if m2:
        return int(m2.group(1)), int(m2.group(2))
    m3 = re.match(r"^(\d+)[～~]?$", s)
    if m3:
        return int(m3.group(1)), None
    return None, None

def categorize_genres(raw_genres: List[str]) -> List[str]:
    """Classifies granular Japanese cuisine genres into primary categories."""
    categories = set()
    for genre in raw_genres:
        matched = False
        for cat, keywords in CUISINE_CATEGORY_MAP.items():
            if any(k in genre for k in keywords):
                categories.add(cat)
                matched = True
        if not matched:
            categories.add('other')
    return sorted(list(categories))

class TabelogScraper:
    def __init__(self, scraper=None):
        self.scraper = scraper or scraper_instance

    def scrape_station_page(
        self,
        station_conf: Dict[str, Any],
        page: int = 1,
        sort: str = "rt"  # 'rt' = rating, 'trend' = popular, 'rvcn' = review count
    ) -> List[Dict[str, Any]]:
        """
        Scrapes a single page of takeout results for a given station.
        """
        area_path = station_conf.get("tabelog_area_path", "tokyo/A1314/A131402/R6076")
        url = f"https://tabelog.com/{area_path}/rstLst/{page}/?takeout=1&SrtT={sort}"

        print(f"[Tabelog] Fetching search page {page} ({sort}): {url}")
        html = self.scraper.get(url, use_cache=True)
        if not html:
            print(f"[Tabelog] Warning: No content received for page {page}")
            return []

        soup = BeautifulSoup(html, "html.parser")
        items = soup.select(".list-rst")
        restaurants = []

        for item in items:
            name_el = item.select_one(".list-rst__rst-name-target")
            if not name_el:
                continue

            r_name = name_el.get_text(strip=True)
            r_url = name_el.get("href", "")
            r_id = item.get("data-rst-id", "")
            if not r_id:
                id_match = re.search(r'/(\d+)/?$', r_url)
                r_id = id_match.group(1) if id_match else r_name

            # Rating
            rating_el = item.select_one(".c-rating__val")
            rating = None
            if rating_el:
                try:
                    val = rating_el.get_text(strip=True)
                    if val != "-" and val != "":
                        rating = float(val)
                except ValueError:
                    rating = None

            # Station distance & Genres
            area_genre_el = item.select_one(".list-rst__area-genre")
            raw_genres = []
            parsed_distance_m = None
            if area_genre_el:
                txt = area_genre_el.get_text(strip=True)
                st_name_ja = station_conf.get('name_ja', '')
                dist_m = re.search(rf"{re.escape(st_name_ja)}\s*(\d+)m", txt) if st_name_ja else None
                if not dist_m:
                    dist_m = re.search(r'(\d+)m', txt)
                if dist_m:
                    parsed_distance_m = int(dist_m.group(1))

                parts = txt.split("/")
                if len(parts) > 1:
                    raw_genres = [g.strip() for g in parts[1].split("、") if g.strip()]

            # Budget
            budgets = item.select(".c-rating-v3__val")
            budget_dinner = budgets[0].get_text(strip=True) if len(budgets) > 0 else ""
            budget_lunch = budgets[1].get_text(strip=True) if len(budgets) > 1 else ""
            d_min, d_max = parse_budget_bounds(budget_dinner)
            l_min, l_max = parse_budget_bounds(budget_lunch)

            # Image
            img_el = item.select_one("img.c-img, img[data-original], .list-rst__image img")
            img_url = ""
            if img_el:
                img_url = img_el.get("data-original") or img_el.get("src") or ""
                if img_url.startswith("data:"):
                    img_url = ""

            restaurants.append({
                "id": str(r_id),
                "name": r_name,
                "url": r_url,
                "rating": rating or 3.0,
                "rating_display": f"{rating:.2f}" if rating else "---",
                "genres": raw_genres,
                "categories": categorize_genres(raw_genres),
                "parsed_distance_m": parsed_distance_m,
                "budget_dinner": budget_dinner,
                "budget_dinner_min": d_min,
                "budget_dinner_max": d_max,
                "budget_lunch": budget_lunch,
                "budget_lunch_min": l_min,
                "budget_lunch_max": l_max,
                "image_url": img_url,
                "takeout": True
            })

        print(f"[Tabelog] Parsed {len(restaurants)} restaurants from page {page}")
        return restaurants

    def enrich_restaurant_details(
        self,
        restaurant: Dict[str, Any],
        station_conf: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fetches the individual restaurant detail page to extract exact lat/lng,
        opening hours, phone, address, and takeout services.
        """
        r_url = restaurant.get("url")
        if not r_url:
            return restaurant

        html = self.scraper.get(r_url, use_cache=True)
        if not html:
            return restaurant

        soup = BeautifulSoup(html, "html.parser")

        # 1. JSON-LD for Geo coordinates, address, phone
        lat = None
        lng = None
        phone = None
        address = ""
        cuisine_ld = None

        for s in soup.find_all("script", type="application/ld+json"):
            try:
                ld = json.loads(s.string)
                if isinstance(ld, dict) and ld.get("@type") in ["Restaurant", "FoodEstablishment", "LocalBusiness"]:
                    geo = ld.get("geo")
                    if isinstance(geo, dict):
                        lat = float(geo.get("latitude", 0)) or None
                        lng = float(geo.get("longitude", 0)) or None
                    phone = ld.get("telephone")
                    cuisine_ld = ld.get("servesCuisine")
                    if ld.get("image") and not restaurant.get("image_url"):
                        restaurant["image_url"] = ld.get("image")
                    addr = ld.get("address")
                    if isinstance(addr, dict):
                        address = f"{addr.get('addressRegion', '')}{addr.get('addressLocality', '')}{addr.get('streetAddress', '')}"
            except Exception:
                pass

        # 2. Parse info table for hours, access, services, website
        table_rows = soup.select(".rstinfo-table tr")
        hours_raw = ""
        holiday_raw = ""
        access_raw = ""
        services_raw = ""
        website = ""
        official_sns = []
        payment_raw = ""

        for row in table_rows:
            th = row.select_one("th")
            td = row.select_one("td")
            if not th or not td:
                continue
            h_text = th.get_text(strip=True)
            t_text = td.get_text("\n", strip=True)

            if "営業時間" in h_text:
                hours_raw = t_text
            elif "定休日" in h_text:
                holiday_raw = t_text
            elif "交通手段" in h_text:
                access_raw = t_text
            elif "住所" in h_text and not address:
                address = td.get_text(" ", strip=True).replace("大きな地図を見る", "").replace("周辺のお店を探す", "").strip()
            elif "サービス" in h_text:
                services_raw = t_text
            elif "支払い方法" in h_text:
                payment_raw = t_text
            elif "ホームページ" in h_text or "オフィシャル" in h_text:
                a_tag = td.select_one("a[href]")
                if a_tag and a_tag.get("href"):
                    website = a_tag["href"]
            elif "公式アカウント" in h_text or "公式" in h_text:
                for a in td.select("a[href]"):
                    href = a["href"]
                    if not href.startswith("http"):
                        continue
                    sns_type = "website"
                    label = "Official Link"
                    if "instagram.com" in href:
                        sns_type = "instagram"
                        label = "Instagram"
                    elif "x.com" in href or "twitter.com" in href:
                        sns_type = "x"
                        label = "X (Twitter)"
                    elif "facebook.com" in href:
                        sns_type = "facebook"
                        label = "Facebook"
                    elif "line.me" in href:
                        sns_type = "line"
                        label = "LINE"
                    elif "tiktok.com" in href:
                        sns_type = "tiktok"
                        label = "TikTok"
                    elif "youtube.com" in href:
                        sns_type = "youtube"
                        label = "YouTube"
                    official_sns.append({"type": sns_type, "label": label, "url": href})

        # Parse schedule
        schedule = parse_opening_hours(hours_raw, holiday_raw)

        # Distance calculation
        dist_info = compute_distance_info(
            origin_lat=station_conf["lat"],
            origin_lng=station_conf["lng"],
            target_lat=lat,
            target_lng=lng,
            fallback_distance_meters=restaurant.get("parsed_distance_m")
        )

        station_name_ja = station_conf.get("name_ja", "")
        search_suffix = f" {station_name_ja}" if station_name_ja else ""
        name_encoded = urllib.parse.quote(f"{restaurant['name']}{search_suffix}")
        # Append station name to Uber Eats query to prioritize local branch
        ubereats_query = urllib.parse.quote(f"{restaurant['name']}{search_suffix}")
        d_min = restaurant.get("budget_dinner_min")
        d_max = restaurant.get("budget_dinner_max")
        l_min = restaurant.get("budget_lunch_min")
        l_max = restaurant.get("budget_lunch_max")
        if d_min is None and d_max is None and restaurant.get("budget_dinner"):
            d_min, d_max = parse_budget_bounds(restaurant.get("budget_dinner"))
        if l_min is None and l_max is None and restaurant.get("budget_lunch"):
            l_min, l_max = parse_budget_bounds(restaurant.get("budget_lunch"))

        restaurant.update({
            "lat": lat,
            "lng": lng,
            "address": address,
            "phone": phone or "",
            "access_raw": access_raw,
            "website": website,
            "official_sns": official_sns,
            "budget_dinner_min": d_min,
            "budget_dinner_max": d_max,
            "budget_lunch_min": l_min,
            "budget_lunch_max": l_max,
            "payment_methods": payment_raw,
            "hours_raw": hours_raw,
            "holiday_raw": holiday_raw,
            "schedule": schedule["days"],
            "is_24h": schedule["is_24h"],
            "distance_meters": dist_info["distance_meters"],
            "walking_minutes": dist_info["walking_minutes"],
            "station_origin": station_conf["name"],
            # Quick external links (English interface for Google Maps & Uber Eats)
            "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={name_encoded}&hl=en",
            "google_maps_dir": f"https://www.google.com/maps/dir/?api=1&origin={station_conf['lat']},{station_conf['lng']}&destination={lat or station_conf['lat']},{lng or station_conf['lng']}&travelmode=walking&hl=en",
            "ubereats_url": f"https://www.ubereats.com/jp-en/search?q={ubereats_query}",
            "tabelog_url": r_url
        })

        return restaurant
