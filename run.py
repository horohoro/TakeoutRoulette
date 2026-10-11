#!/usr/bin/env python3
"""
TakeoutRoulette CLI Entry Point
Hunt for takeout spots, inspect candidates, build the static site, and launch local server.
"""
import sys
import argparse
import webbrowser
import http.server
import socketserver
import json
from pathlib import Path
from config import BASE_DIR, DATA_DIR, INDEX_HTML, STATION_PRESETS, DEFAULT_STATION
from pipeline import Pipeline
from generator import generate_dashboard

def cmd_hunt(args):
    station_id = args.station.lower()
    pages = args.pages
    enrich = not args.no_enrich

    pipeline = Pipeline()
    print(f"[CLI] Starting takeout hunt for station: '{station_id}' ({pages} pages)...")
    results = pipeline.run_hunt(station_id=station_id, pages=pages, enrich_all=enrich)
    
    # Auto-rebuild dashboard
    generate_dashboard()
    print(f"\n[CLI] Done! {len(results)} restaurants discovered and indexed.")

def cmd_build(args):
    print("[CLI] Building standalone interactive TakeoutRoulette dashboard...")
    out_file = generate_dashboard()
    print(f"[CLI] Built successfully: {out_file}")

def cmd_serve(args):
    port = args.port
    # Ensure index.html exists
    if not INDEX_HTML.exists():
        generate_dashboard()

    print(f"\n🍱 Serving TakeoutRoulette at http://localhost:{port}")
    print(f"👉 Press Ctrl+C to stop the server\n")
    
    url = f"http://localhost:{port}/index.html"
    try:
        webbrowser.open(url)
    except Exception:
        pass

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[CLI] Server stopped.")

def cmd_list(args):
    data_file = DATA_DIR / "restaurants.json"
    if not data_file.exists():
        print(f"[CLI] No restaurants database found at {data_file}. Run 'python run.py hunt' first.")
        return

    data = json.loads(data_file.read_text(encoding="utf-8"))
    restaurants = data.get("restaurants", [])
    limit = args.limit or len(restaurants)

    station_name = data.get("station", {}).get("name", "Unknown Station")
    print(f"\n🍱 Takeout Restaurants near {station_name} (Top {min(limit, len(restaurants))} of {len(restaurants)}):")
    print("-" * 88)
    print(f"{'#':<3} {'Rating':<7} {'Dist':<8} {'Walk':<7} {'Name':<28} {'Cuisines'}")
    print("-" * 88)

    for idx, r in enumerate(restaurants[:limit], 1):
        rating_str = f"⭐ {r.get('rating', 0):.2f}"
        dist_str = f"{r.get('distance_meters', 0)}m"
        walk_str = f"~{r.get('walking_minutes', 1)}min"
        name_str = r.get("name", "")[:26]
        cuisines_str = " / ".join(r.get("genres", [])[:3])
        print(f"{idx:<3} {rating_str:<7} {dist_str:<8} {walk_str:<7} {name_str:<28} {cuisines_str}")
    print("-" * 88)

def cmd_stats(args):
    data_file = DATA_DIR / "restaurants.json"
    if not data_file.exists():
        print(f"[CLI] No restaurants database found. Run 'python run.py hunt' first.")
        return

    data = json.loads(data_file.read_text(encoding="utf-8"))
    restaurants = data.get("restaurants", [])
    station = data.get("station", {})

    print(f"\n📊 TakeoutRoulette Statistics:")
    print(f"  Station: {station.get('name', 'Local Station')}")
    print(f"  Total Indexed Restaurants: {len(restaurants)}")
    
    # Cuisine breakdown
    cuisine_counts = {}
    for r in restaurants:
        for c in r.get("categories", ["other"]):
            cuisine_counts[c] = cuisine_counts.get(c, 0) + 1

    print("\n  Cuisine Distribution:")
    for cat, cnt in sorted(cuisine_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {cat:<18}: {cnt} spots")

    ratings = [r.get("rating") for r in restaurants if r.get("rating")]
    if ratings:
        avg_rating = sum(ratings) / len(ratings)
        top_rating = max(ratings)
        print(f"\n  Average Tabelog Rating: {avg_rating:.2f} (Max: {top_rating:.2f})")

def main():
    parser = argparse.ArgumentParser(description="TakeoutRoulette - Japan Station Takeout Randomizer & Explorer")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # hunt
    hunt_p = subparsers.add_parser("hunt", help="Crawl and enrich takeout restaurants for a station")
    hunt_p.add_argument("--station", default=DEFAULT_STATION["id"], help="Station identifier preset")
    hunt_p.add_argument("--pages", type=int, default=3, help="Number of search pages to crawl (20 spots/page)")
    hunt_p.add_argument("--no-enrich", action="store_true", help="Skip fetching individual restaurant detail pages")

    # build
    subparsers.add_parser("build", help="Recompile index.html from data/restaurants.json")

    # serve
    serve_p = subparsers.add_parser("serve", help="Run local HTTP server and open browser")
    serve_p.add_argument("--port", type=int, default=8000, help="Port to serve on (default: 8000)")

    # list
    list_p = subparsers.add_parser("list", help="Print table of candidate restaurants in terminal")
    list_p.add_argument("--limit", type=int, default=25, help="Number of items to print")

    # stats
    subparsers.add_parser("stats", help="Display statistics of current dataset")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "hunt": cmd_hunt,
        "build": cmd_build,
        "serve": cmd_serve,
        "list": cmd_list,
        "stats": cmd_stats,
    }

    cmd_map[args.command](args)

if __name__ == "__main__":
    main()
