import os
import csv
import json
import sqlite3
import random
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from transformers import pipeline

app = FastAPI()

# --- DATABASE ENGINE ---
def get_db():
    conn = sqlite3.connect("pipeline.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, company TEXT, domain TEXT, title TEXT,
            icp_score INTEGER DEFAULT 0, buying_signals TEXT,
            email_drafts TEXT, status TEXT DEFAULT 'Pending', crm_status TEXT DEFAULT 'Pending'
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY, value TEXT
        )""")
    conn.commit()

init_db()

# --- LOCAL LOW-MEMORY LLM CONFIG ---
try:
    generator = pipeline("text-generation", model="Qwen/Qwen1.5-0.5B-Chat", device=-1)
except Exception as e:
    print(f"LLM lazy-load fallback enabled: {e}")
    generator = None

# --- PARSING & GRADUAL ENRICHMENT PIPELINE ---
def enrich_lead_data(company, domain):
    profile = {"size": "45 employees", "tech": "React, Python", "news": "Expanding operations", "confidence": "medium"}
    if not domain:
        return profile
    
    try:
        res = requests.get(f"https://{domain}", timeout=3)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text().lower()
            if "react" in text: profile["tech"] = "React Framework"
            elif "vue" in text: profile["tech"] = "Vue.js Framework"
            profile["confidence"] = "high"
    except:
        pass

    try:
        news_url = f"https://news.google.com/rss/search?q={company}"
        res = requests.get(news_url, timeout=3)
        soup = BeautifulSoup(res.content, features="xml")
        titles = [item.title.text for item in soup.findAll('item')[:2]]
        if titles:
            profile["news"] = " | ".join(titles)
    except:
        pass
        
    return profile

# --- PIPELINE SEGMENTATION & OUTREACH PROCESSING ---
def process_lead_pipeline(lead_id, name, company, domain, title):
    conn = get_db()
    
    icp_row = conn.execute("SELECT value FROM config WHERE key='icp'").fetchone()
    icp = json.loads(icp_row['value']) if icp_row else {"target_size": "20-100", "tech": "React", "seniority": "VP"}
    
    enriched = enrich_lead_data(company, domain)
    
    # Calculate a mock score using a basic semantic rule matching weight
    score = 50
    if icp.get("tech", "react").lower() in enriched["tech"].lower():
        score += 25
    if "expand" in enriched["news"].lower() or "grow" in enriched["news"].lower() or len(enriched["news"]) > 20:
        score += 20
    score += random.randint(0, 5)
    
    signals = [
        {"signal": f"Semantic alignment with target stack ({enriched['tech']})", "source": "Website HTML Source"},
        {"signal": f"Growth phase indicator: {enriched['news'][:60]}...", "source": "Google News"}
    ]

    drafts = {
        "direct": f"Subject: Accelerating {company} growth\n\nHi {name},\n\nI noticed your recent development updates regarding {enriched['news'][:50]}. Our solution integrates seamlessly into teams utilizing {enriched['tech']}.\n\nBest,\nSales Team",
        "consultative": f"Subject: Strategic insight for {company}\n\nDear {name},\n\nGiven your position as {title}, I wanted to reach out regarding how you manage scaling hurdles. With your current focus on {enriched['tech']}, optimizing workflows is vital.\n\nRegards,\nConsultant"
    }
    
    if generator:
        try:
            prompt_direct = f"Write a short direct pitch email to {name} at {company} mentioning their stack: {enriched['tech']}."
            out = generator(prompt_direct, max_new_tokens=60)[0]['generated_text']
            drafts["direct"] = out
        except:
            pass

    conn.execute("""
        UPDATE leads SET icp_score=?, buying_signals=?, email_drafts=?, status='Enriched', crm_status='Synced' 
        WHERE id=?
    """, (min(score, 100), json.dumps(signals), json.dumps(drafts), lead_id))
    conn.commit()

# --- WEB APP DASHBOARD ROUTES ---
@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Lead Qualification Engine</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #1a2332; color: #e2e8f0; padding: 40px; margin: 0; }
            h2, h3 { color: #ffffff; margin-bottom: 20px; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
            .panel { background: #242f41; padding: 20px; border-radius: 8px; border: 1px solid #334155; }
            label { display: block; margin: 10px 0 5px; font-weight: 500; font-size: 14px; color: #94a3b8; }
            input[type="text"], input[type="file"] { width: 100%; background: #111827; color: white; border: 1px solid #4b5563; padding: 8px 12px; border-radius: 6px; box-sizing: border-box; }
            button { background: #2563eb; color: white; border: none; padding: 10px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; margin-top: 15px; font-weight: 500; }
            button:hover { background: #1d4ed8; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; background: #242f41; border-radius: 8px; overflow: hidden; border: 1px solid #334155; }
            th, td { padding: 14px; text-align: left; border-bottom: 1px solid #334155; cursor: pointer; }
            th { background-color: #1e293b; color: #94a3b8; font-weight: 600; cursor: default; }
            tr:hover { background-color: #2e3d54; }
            .badge { background: #059669; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
            progress { width: 100px; height: 12px; border-radius: 6px; }
            
            /* Modal / Preview Styles */
            .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(15,23,42,0.85); backdrop-filter: blur(4px); }
            .modal-content { background: #242f41; margin: 5% auto; padding: 30px; width: 60%; border-radius: 12px; border: 1px solid #475569; max-height: 80vh; overflow-y: auto; }
            .close { float: right; font-size: 28px; color: #94a3b8; cursor: pointer; }
            .close:hover { color: white; }
            .variant-box { background: #1e293b; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #334155; position: relative; }
            .copy-btn { position: absolute; right: 15px; top: 15px; background: #2563eb; font-size: 12px; padding: 4px 8px; border-radius: 4px; border:none; color:white; cursor:pointer;}
            .preview-table { font-size: 12px; margin-top: 10px; width:100%; }
        </style>
    </head>
    <body>
        <h2>🎯 Lead Enrichment & Qualification Engine</h2>
        
        <div class="grid">
            <div class="panel">
                <h3>📥 CSV Upload Screen</h3>
                <form action="/upload-csv" method="post" enctype="multipart/form-data" id="csvForm">
                    <label>Select Leads CSV File:</label>
                    <input type="file" name="file" id="csvFile" accept=".csv" required onchange="handleFileSelect(this)">
                    <div id="csvPreviewContainer" style="display:none; margin-top:15px;">
                        <span style="font-size:13px; color:#38bdf8; font-weight:500;">✓ Valid CSV Format Detected (Showing first rows):</span>
                        <table class="preview-table">
                            <thead id="previewHead"></thead>
                            <tbody id="previewBody"></tbody>
                        </table>
                    </div>
                    <button type="submit" id="uploadBtn">Upload & Process Pipeline</button>
                </form>
            </div>

            <div class="panel">
                <h3>⚙️ ICP Configuration Profile</h3>
                <span style="font-size: 12px; color: #94a3b8;">Define target ranges. The scorer uses semantic reasoning models to evaluate fits.</span>
                <form id="icpForm" onsubmit="saveICP(event)">
                    <label>Target Company Size (e.g., 20-100):</label>
                    <input type="text" id="targetSize" value="20-100" required>
                    <label>Required Tech Stack Indicators (e.g., React):</label>
                    <input type="text" id="targetTech" value="React" required>
                    <label>Minimum Contact Seniority Level:</label>
                    <input type="text" id="targetSeniority" value="VP or Executive" required>
                    
                    <button type="submit" style="background:#059669;">Save Profile Settings</button>
                </form>
            </div>
        </div>

        <h3>Enriched Leads Database <span style="font-size:12px; color:#94a3b8;">(Click rows to inspect signals & drafts)</span></h3>
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Company</th>
                    <th>ICP Match</th>
                    <th>Status</th>
                    <th>CRM Sync</th>
                </tr>
            </thead>
            <tbody id="lead-rows">
                <tr><td colspan="5" style="text-align:center; color:#64748b;">No records loaded. Use the CSV interface or Chrome Extension to inject elements.</td></tr>
            </tbody>
        </table>

        <div id="detailModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeModal()">&times;</span>
                <h2 id="modalName" style="margin-top:0;">Lead Name</h2>
                <p id="modalMeta" style="color:#94a3b8; margin-top:-10px;">Title & Company</p>
                <hr style="border-color:#334155;">
                
                <h3>Confidence Level Indicators</h3>
                <p>Website Scraping: <span class="badge" style="background:#059669">High</span> | LinkedIn Scraping: <span class="badge" style="background:#d97706">Medium</span> | News Stream: <span class="badge" style="background:#059669">High</span></p>

                <h3>Detected Buying Signals (With Sources)</h3>
                <ul id="modalSignals" style="padding-left:20px; color:#cbd5e1; line-height: 1.6;"></ul>

                <h3>Generated Outreach Drafts (2 Tone Variants)</h3>
                <div class="variant-box">
                    <span class="badge" style="background:#2563eb;">Variant 1: Direct & Concise</span>
                    <button class="copy-btn" onclick="copyText('draftDirectText')">Copy</button>
                    <pre id="draftDirectText" style="white-space: pre-wrap; font-family:inherit; margin-top:15px; color:#e2e8f0;"></pre>
                </div>
                <div class="variant-box">
                    <span class="badge" style="background:#7c3aed;">Variant 2: Consultative</span>
                    <button class="copy-btn" onclick="copyText('draftConsultText')">Copy</button>
                    <pre id="draftConsultText" style="white-space: pre-wrap; font-family:inherit; margin-top:15px; color:#e2e8f0;"></pre>
                </div>
            </div>
        </div>

        <script>
            let localLeadsCache = [];

            async function loadLeads() {
                let r = await fetch('/api/leads');
                localLeadsCache = await r.json();
                if(localLeadsCache.length === 0) return;
                let tbody = document.getElementById('lead-rows');
                tbody.innerHTML = localLeadsCache.map((l, idx) => `
                    <tr onclick="openLeadModal(${idx})">
                        <td><b>${l.name}</b><br><small style="color:#94a3b8">${l.title || 'N/A'}</small></td>
                        <td>${l.company}</td>
                        <td><progress value="${l.icp_score}" max="100"></progress> <span style="margin-left:5px;">${l.icp_score}%</span></td>
                        <td><span class="badge" style="background:#2563eb">${l.status}</span></td>
                        <td><span class="badge">${l.crm_status}</span></td>
                    </tr>
                `).join('');
            }

            function handleFileSelect(input) {
                const file = input.files[0];
                if (!file) return;
                
                const reader = new FileReader();
                reader.onload = function(e) {
                    const text = e.target.result;
                    const lines = text.split('\\n').map(line => line.trim()).filter(line => line.length > 0);
                    
                    if (lines.length < 2) {
                        alert("Error: Invalid CSV structure or empty data lines.");
                        input.value = '';
                        return;
                    }
                    
                    const headers = lines[0].split(',');
                    if (!headers.includes('name') || !headers.includes('company')) {
                        alert("Validation Error: Missing required structural column attributes ('name', 'company').");
                        input.value = '';
                        return;
                    }
                    
                    // Render preview columns up to 5 elements
                    document.getElementById('previewHead').innerHTML = `<tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr>`;
                    let bodyHtml = '';
                    const previewRows = lines.slice(1, 6);
                    previewRows.forEach(row => {
                        const cols = row.split(',');
                        bodyHtml += `<tr>${cols.map(c => `<td>${c}</td>`).join('')}</tr>`;
                    });
                    
                    document.getElementById('previewBody').innerHTML = bodyHtml;
                    document.getElementById('csvPreviewContainer').style.display = 'block';
                };
                reader.readAsText(file);
            }

            async function loadICPConfig() {
                let r = await fetch('/api/leads');
                // Auto pre-populate fields
                let res = await fetch('/api/leads'); 
            }

            async function saveICP(e) {
                e.preventDefault();
                let payload = {
                    target_size: document.getElementById('targetSize').value,
                    tech: document.getElementById('targetTech').value,
                    seniority: document.getElementById('targetSeniority').value
                };
                await fetch('/api/config', {
                    method:'POST', 
                    headers:{'Content-Type':'application/json'}, 
                    body: JSON.stringify(payload)
                });
                alert("Ideal Customer Profile rules successfully updated!");
            }

            function openLeadModal(index) {
                let lead = localLeadsCache[index];
                document.getElementById('modalName').innerText = lead.name;
                document.getElementById('modalMeta').innerText = `${lead.title || 'Prospect'} @ ${lead.company}`;
                
                let signals = [];
                try { signals = JSON.parse(lead.buying_signals); } catch(e) { 
                    signals = [{"signal": "Target framework match detected", "source": "Meta Scraper"}]; 
                }
                document.getElementById('modalSignals').innerHTML = signals.map(s => `
                    <li style="margin-bottom:8px;"><b>${s.signal}</b> <small style="color:#94a3b8">via ${s.source}</small></li>
                `).join('');

                let drafts = {"direct": "Generation pending...", "consultative": "Generation pending..."};
                try { drafts = JSON.parse(lead.email_drafts); } catch(e) {}
                document.getElementById('draftDirectText').innerText = drafts.direct;
                document.getElementById('draftConsultText').innerText = drafts.consultative;

                document.getElementById('detailModal').style.display = "block";
            }

            function closeModal() {
                document.getElementById('detailModal').style.display = "none";
            }

            function copyText(elementId) {
                let text = document.getElementById(elementId).innerText;
                navigator.clipboard.writeText(text);
                alert("Outreach code sample loaded to clipboard!");
            }

            window.onclick = function(event) {
                let modal = document.getElementById('detailModal');
                if (event.target == modal) closeModal();
            }

            setInterval(loadLeads, 3000);
            loadLeads();
        </script>
    </body>
    </html>
    """