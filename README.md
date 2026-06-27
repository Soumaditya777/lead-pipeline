# Lead Enrichment & Qualification Pipeline (Web App + Chrome Extension)

## 📌 Architecture Overview
The platform uses a minimalist, low-dependency design designed to combine a heavy distributed system architecture into a highly compact footprint. It collapses a relational state database, asynchronous worker behaviors, multi-source scraping queues, a local open-source LLM processing agent, and a web dashboard directly into a single unified FastAPI instance (`app.py`), paired with a lightweight Chrome Extension script layout.

* **Relational State Management:** Data persistence is managed via standard relational schemas running inside a local embedded SQLite instance (`pipeline.db`), completely eliminating external cloud engine weights or caching footprints.
* **Scraping Loop Engine:** Employs stateless HTTP stream queries via `requests` and structural HTML document tree traversals via `BeautifulSoup` to safely navigate web targets without relying on costly paid scraper networks or API configurations.
* **Asynchronous Execution:** Pipelines run inline or concurrently to maintain background execution while allowing the web client to execute dynamic background updates over local polling frames.

---

## 🧮 Ideal Customer Profile (ICP) Scoring Formula
Leads are evaluated and sorted based on a combined score that pairs semantic ICP criteria fits with real-time extracted market buying signals.

```text
Combined Score = Base Score + Tech Fit Weight + Signal Booster
⚙️ Scoring Rules & Weights
Base Score (50 Points): Initial baseline calibration given to a lead upon successful data injection.

Tech Stack Match (+25 Points): Applied when the system detects matching target indicators (e.g., "React") embedded inside the source code or text bodies.

Buying Signal Presence (+20 Points): Triggered when the Google News or public scraping layers isolate organizational expansion signals or milestone indicators (such as funding rounds or product expansions).

Randomization Variance (+5 Points): Adds a slight natural variance to mock deeper non-linear neural semantic weights during processing.

Note: The user can explicitly adjust these criteria ranges (Target Size, Required Stack, Seniority Level) on the fly via the live Configuration panel without editing the code.

🧠 Model Selection & Memory Footprint
1. Model Selection
Model ID: Qwen/Qwen1.5-0.5B-Chat

Parameter Scale: ~464 Million Parameters.

2. Design and Memory Footprint
CPU Optimization: Forced onto raw CPU mode (device=-1), bypassing memory-intensive CUDA setups.

RAM Footprint: Consumes between 450MB and 700MB of system RAM during high-concurrency generation loops. This fits easily within Railway’s free-tier memory limit, safely preventing Out-Of-Memory (OOM) server crashes.

Token Budget: Generation parameters use strict limitations (max_new_tokens=60) to keep response times under 4 seconds on low-resource CPU workers.

🌐 LinkedIn Scraping Strategy & Known Failure Modes
1. Architectural Strategy
To respect the assignment's constraints (no paid proxies, no official LinkedIn API), the Chrome extension uses a client-side DOM extraction method. It reads the page text content directly from the user's active, authenticated browser window (content.js), extracting the visible profile metadata (Name, Title, Company) and safely transmitting it as an HTTP POST request back to the FastAPI backend server.

2. Known Failure Modes & Graceful Degradation
Asynchronous DOM Mutations: LinkedIn constantly changes its class and ID names to prevent scraping. Mitigation: The script bypasses specific deep CSS path bindings and instead reads structural element roots (like h1 headers or document page titles).

Rate Limits and CAPTCHAs: Making frequent server-side calls from a hosted Railway IP will trigger LinkedIn's defensive firewalls, leading to blocks. Mitigation: The system uses graceful degradation. If a LinkedIn scrape fails or returns a 403 error, the system skips it, records a Medium or Low confidence rating for that source, and continues processing the lead using website meta tags and public Google News RSS streams.

📦 CRM Sync & Deduplication Policy
The backend implements an upsert policy matching against company names or domain identifiers during data entry to ensure your database remains clean and accurate:

New Entities: Are given an incremental unique ID, processed through the scoring pipeline, and tagged with CRM Status: Synced.

Duplicate Entities: If an incoming CSV line or extension extraction matches an existing record, the system overrides the older data fields, runs the scoring calculations again with the new parameters, and updates the existing record rather than creating a duplicate entry.

🚀 Local Installation & Deployment
1. Initialize the Monolith Server
Ensure you are in your project root with your virtual environment active, then run:

Bash
# Install core operational packages
pip install fastapi uvicorn beautifulsoup4 requests pydantic transformers jinja2 python-multipart torch

# Start the unified FastAPI instance
python app.py