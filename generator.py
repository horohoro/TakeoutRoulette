"""
TakeoutRoulette HTML Dashboard Generator
Compiles restaurants database into a self-contained, standalone static web application.
Supports AES-256-GCM encryption with PBKDF2 for GitHub Pages publication.
"""
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from config import BASE_DIR, DATA_DIR, INDEX_HTML, DEFAULT_STATION

TEMPLATE_PATH = BASE_DIR / "template" / "index.html"

def generate_dashboard(
    restaurants_file: Optional[Path] = None,
    output_file: Optional[Path] = None,
    passphrase: Optional[str] = None
) -> Path:
    if restaurants_file is None:
        restaurants_file = DATA_DIR / "restaurants.json"
    if output_file is None:
        output_file = INDEX_HTML

    if not restaurants_file.exists():
        print(f"[Generator] Warning: {restaurants_file} does not exist yet. Using empty dataset.")
        payload = {
            "station": DEFAULT_STATION,
            "count": 0,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S JST"),
            "restaurants": []
        }
    else:
        payload = json.loads(restaurants_file.read_text(encoding="utf-8"))

    # Check for encryption passphrase
    if passphrase is None:
        from crypto import load_passphrase_from_env
        passphrase = load_passphrase_from_env()

    restaurants_list = payload.get("restaurants", [])
    restaurants_json = json.dumps(restaurants_list, ensure_ascii=False)
    station_json = json.dumps(payload.get("station", DEFAULT_STATION), ensure_ascii=False)
    generated_at_str = payload.get("generated_at", time.strftime("%Y-%m-%d %H:%M:%S JST"))
    total_count_str = str(len(restaurants_list))

    encrypted_payload_str = "null"
    if passphrase:
        from crypto import encrypt_payload
        full_payload = {
            "station": payload.get("station", DEFAULT_STATION),
            "restaurants": restaurants_list
        }
        enc_dict = encrypt_payload(json.dumps(full_payload, ensure_ascii=False), passphrase)
        encrypted_payload_str = json.dumps(enc_dict)
        # Empty out plain JSON so zero restaurant or station info is in plaintext
        restaurants_json = "[]"
        station_json = "{}"
        print(f"[Generator] Encrypted database with AES-256-GCM + PBKDF2 ({len(restaurants_list)} restaurants).")
    else:
        print("[Generator] Generating unencrypted dashboard (no passphrase configured).")

    template_content = TEMPLATE_PATH.read_text(encoding="utf-8")

    rendered = template_content.replace("/*__RESTAURANTS_DATA__*/[]", restaurants_json)
    rendered = rendered.replace("/*__ENCRYPTED_PAYLOAD__*/null", encrypted_payload_str)
    rendered = rendered.replace("/*__STATION_DATA__*/{}", station_json)
    rendered = rendered.replace("__GENERATED_AT__", generated_at_str)
    rendered = rendered.replace("__TOTAL_COUNT__", total_count_str)

    output_file.write_text(rendered, encoding="utf-8")
    print(f"[Generator] Successfully compiled standalone dashboard to: {output_file}")
    return output_file

if __name__ == "__main__":
    generate_dashboard()

