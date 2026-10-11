# 🍱 TakeoutRoulette

> **Break the supermarket bento routine!** A 100% serverless, zero-backend static web application to discover and randomly pick **open-now takeout restaurants** within walking distance of your local station in Japan.

Like the **Wildgoosechase** project, TakeoutRoulette runs with **zero server-side runtime dependencies**. The web app is a self-contained static HTML/JS file that works directly in any browser (`file:///` or GitHub Pages) while persisting your order history and bookmarks in local storage with cross-device JSON and QR code synchronization.

---

### 🌐 Live Web Application (Encrypted Vault)
👉 **[Open Live TakeoutRoulette on GitHub Pages](https://horohoro.github.io/TakeoutRoulette/)**

> **Privacy & Security**: The live database is end-to-end encrypted with **AES-256-GCM** using PBKDF2 (150,000 iterations). Enter your master passphrase to unlock the app and spin the roulette. Zero unencrypted restaurant, location, or station data is exposed in the public repository.

---

## 🎯 Background & Motivation

Tired of eating the same prepared bentos every night from local supermarkets or convenience stores after work?

Most Japanese station neighborhoods are packed with hidden culinary gems that offer takeout or pickup orders—from famous ramen and tonkatsu to gourmet burgers, authentic curries, Italian pasta, and bento specialties.

TakeoutRoulette solves dinner indecision by picking a spot based on:

1. **Takeout-verified**: Every spot is verified for takeout availability using Tabelog's official takeout index (`takeout=1`).
2. **Open right now**: Dynamically evaluates the current real-time clock against day-of-week operating hours, late-night shifts (past midnight), and last order calls.
3. **No repeats (unless allowed)**: Spots you've already ordered from are saved to your local history and skipped by default to encourage trying new food (toggleable if you want repeat visits).
4. **Distance weighting**: Closer to the station = higher probability of being picked.
5. **Rating weighting**: Higher Tabelog rating = higher probability of being picked.
6. **Night budget filter**: Focuses on realistic dinner takeout budgets (under ¥4,000) while filtering out luxury dine-in kaiseki/omakase venues.

---

## 💡 Data Source Analysis & Practical Findings

| Source | Evaluation & Practical Reality | Implementation Strategy |
| :--- | :--- | :--- |
| **Google Maps / Places API** | Pay-per-call billing with mandatory credit card registration. Web crawling Google Maps triggers strict bot protection / captchas. | ❌ Not used for scraping.<br>👉 **Used as 1-click walking directions link** directly to the chosen restaurant. |
| **Delivery Apps (Uber Eats, Demae-can, etc.)** | Heavy bot mitigation makes regular crawling fragile. Demae-can requires session state. | ❌ Not used for primary scraping.<br>👉 **Used as localized search links** (`Search Uber Eats Pickup`) and direct phone numbers for takeout order calls. |
| **Tabelog (食べログ)** | **The gold standard food aggregator in Japan.** Has an explicit `takeout=1` search parameter, rigorous ratings (⭐ 3.0 to 4.5+), exact opening/closing schedules, day-by-day holiday schedules, phone numbers, official websites (`ホームページ`), official social media (`公式アカウント`: Instagram, X, Facebook), and walking distances. | ✅ **Adopted as primary ingestion engine.** Our polite cached scraper fetches and enriches spots without any API keys or blocking. |

---

## 🚀 Key Features

### 1. 🎰 Dual-Mode Roulette Experience
- **Slot Reel Mode**: Rapidly cycles through contender cards with realistic physical deceleration, locking onto the winner.
- **Canvas Wheel Mode**: Interactive 360° wheel canvas with slices sized proportionally to each restaurant's calculated odds and mathematically aligned top arrow.
- **Synthesized Audio (Web Audio API)**: Zero external audio files required. Generates ticking clicks during spins and celebratory fanfares on winner reveal (with mute toggle).
- **Confetti Explosion**: Full-screen canvas confetti upon landing on the winning restaurant.
- **Odds Transparency Modal**: View the exact calculated percentage odds (e.g. `8.4%`, `5.1%`) for every restaurant currently in the eligible pool.

### 2. 🕒 Real-Time "Open Now" Engine & Time Simulation
- Automatically compares the live clock against daily hours:
  - `🟢 Open Now (Closes at 22:00 / 35m left)`
  - `🌙 Open Late (Overnight past midnight)`
  - `⚪ Closed`
- **Time Simulation Slider**: Test scenarios like: *"If I leave the office at 21:30, what's still open for takeout nearby?"*

### 3. ⚖️ Weighted Probability Selection Algorithm
Each eligible restaurant receives a selection weight $W_i$:

$$W_i = \left( \frac{600}{\max(100, D_i + 100)} \right)^{\beta_{\text{dist}}} \times \left( \max(0.1, R_i - 2.0) \right)^{\beta_{\text{rating}}} \times C_{\text{price}}$$

- $D_i$: Walking distance in meters from the station.
- $R_i$: Tabelog score (e.g. 3.00 to 4.50).
- $\beta_{\text{dist}}, \beta_{\text{rating}}$: Configurable priority weights (Disabled, Balanced, High, Maximum).
- $C_{\text{price}}$: Practical dinner takeout weighting (everyday <¥2,000 gets higher priority).

Each restaurant's final probability $P_i$ is normalized across all eligible contenders:

$$P_i = \frac{W_i}{\sum_{k} W_k} \times 100 \, (\%)$$

### 4. 🗺️ Interactive Map & Custom Landmark Pins
- Interactive OpenStreetMap view with custom pins.
- Station origin pin and supermarket/transit baseline landmarks.
- Walking radius overlay rings: **300m (~4 min)**, **500m (~6 min)**, and **800m (~10 min)**.
- High-rated restaurants (⭐ 3.4+) highlighted with gold badges.

### 5. 📜 Order History & Bento Variety Tracker
- Prevents dinner monotony by tracking your meal history in browser `localStorage`.
- Record personal ratings (★1–5) and custom notes (e.g., *"Crispy karaage, great portion"*).
- Metrics: Total Takeout Orders, Unique Spots Tried, Supermarket Escapes count.

### 6. 📱 Cross-Device Synchronization (Phone ⇔ PC)
- **JSON Export / Import**: Download a `.json` backup file or copy backup text to clipboard with 1 click.
- **Mobile QR Code Transfer**: Display a QR code on your PC screen; scan it with your phone's camera to instantly open TakeoutRoulette on mobile with your saved data.

---

## 🛠️ How to Run

Requirements: Python 3.10+ (if running CLI or server; opening `index.html` directly requires only a browser).

### 1. Launch Local Web Server & Open Browser
```powershell
python run.py serve
```
Opens `http://localhost:8000/index.html` in your default browser.
*(You can also double-click `index.html` directly without starting any server!)*

### 2. View Discovered Restaurants in Terminal
```powershell
python run.py list --limit 20
```

### 3. View Summary Statistics
```powershell
python run.py stats
```

### 4. Discover More Takeout Spots (Data Hunt)
```powershell
python run.py hunt --pages 5
```
> The built-in `PoliteScraper` uses SHA-256 disk caching in `.cache/` and polite delays (1.0–2.2s) to protect server bandwidth. Station parameters can be configured locally in `.env`.

---

## 📂 Project Directory Structure

```
TakeoutRoulette/
├── data/
│   └── restaurants.json         # Normalized takeout restaurants database (gitignored)
├── scrapers/
│   ├── base.py                  # Polite disk-caching HTTP scraper
│   └── tabelog.py               # Tabelog takeout extractor & detail enricher
├── enrichers/
│   ├── hours_parser.py          # Japanese opening hours & overnight shift parser
│   └── geo.py                   # Great-circle distance & 80m/min walking calculator
├── template/
│   └── index.html               # Standalone SPA template (Tailwind, Leaflet, Audio API)
├── config.py                    # Network settings and environment loader
├── crypto.py                    # AES-256-GCM + PBKDF2 encryption engine
├── generator.py                 # HTML compiler injecting encrypted vault into index.html
├── run.py                       # Master CLI entrypoint
├── requirements.txt             # Python dependencies
└── README.md                    # English documentation
```
