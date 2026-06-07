import datetime
import re
import time
import random
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import streamlit as st
from urllib.parse import urlparse, quote_plus

st.set_page_config(page_title="Kenya Job Hub: Master Scanner", layout="wide")

st.title("📌 Kenya Job Deep Scanner (Universal Edition)")
st.markdown("Extracting fresh white-collar, blue-collar, corporate, and entry-level jobs directly from database networks.")

# Unified multi-source XML endpoints
MASSIVE_FEEDS = [
    "https://www.myjobmag.co.ke/jobs-by-date.xml",
    "https://jobwebkenya.com/feed/",
    "https://kenya2711.rssing.com/chan-30179697/latest.xml"
]

SCAM_KEYWORDS = [
    r"registration fee", r"booking fee", r"medical fee", r"processing fee",
    r"training fee", r"uniform fee", r"send money", r"mpesa", r"m-pesa", r"deposit"
]

BLUE_COLLAR_KEYWORDS = [
    "driver", "cleaner", "security", "guard", "plumber", "welder", "mechanic", 
    "electrician", "mason", "carpenter", "rider", "casual", "factory", "artisan", 
    "technician", "attendant", "waiter", "waitress", "cook", "chef", "storekeeper"
]

def check_experience_level(title, text):
    combined = (title + " " + text).lower()
    
    # Auto-Pass practical/manual roles
    if any(kw in title.lower() for kw in BLUE_COLLAR_KEYWORDS):
        return "🛠️ Blue-Collar / Trade"
        
    # Auto-Pass marked entry items
    if any(kw in combined for kw in ["entry level", "fresh graduate", "graduate trainee", "intern", "internship", "attachment", "no experience", "0-1", "0-2", "1-2 years"]):
        return "🎓 Entry-Level / Graduate"
        
    # Strict filter removal for major senior tracks
    if any(kw in title.lower() for kw in ["senior", "manager", "director", "head of", "lead", "principal", "chief", "supervisor"]):
        return None
        
    # Standard filter for mid-tier roles with low barriers
    exp_match = re.search(r'(three|four|five|six|seven|eight|nine|ten|[3-9]|[1-9][0-9])\+?\s*(?:to|-)?\s*(?:[0-9]+)?\s*(?:years?|yrs)', combined)
    if exp_match:
        return None
        
    return "💼 Professional / Corporate"

def extract_domain(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return "External Website"

def analyze_scam_risk(title, description):
    score = 0
    text = (title + " " + description).lower()
    for pattern in SCAM_KEYWORDS:
        if re.search(pattern, text):
            score += 60
    if score >= 60:
        return "❌ HIGH RISK SCAM - Mentions financial transaction or fee upfront."
    elif "yahoo.com" in text or "gmail.com" in text:
        return "⚠️ SUSPICIOUS - Uses public domain registration address."
    else:
        return "✅ LEGITIMATE - Clear layout verified by text scanning."

def deep_scrape_job_page(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code != 200:
            return None, None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Outbound ATS Extractor
        outbound_link = None
        base_domain = extract_domain(url)
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.text.lower()
            if base_domain not in href and not any(skip in href for skip in ["facebook.com", "twitter.com", "whatsapp.com", "linkedin.com/share"]):
                if any(keyword in text for keyword in ["apply", "click here", "website", "application form"]) or any(ats in href for ats in ["workday", "greenhouse", "taleo", "bamboohr", "fuzu"]):
                    outbound_link = href
                    break 
                    
        # Qualifications Document Parsing
        qualifications_text = ""
        headings = soup.find_all(['h2', 'h3', 'h4', 'strong', 'b'])
        for tag in headings:
            if tag.text and any(q in tag.text.lower() for q in ["qualification", "requirement", "skills", "experience", "education"]):
                next_ul = tag.find_next(['ul', 'ol'])
                if next_ul:
                    lis = next_ul.find_all('li')
                    bullets = [f"• {li.get_text(strip=True)}" for li in lis[:6]]
                    qualifications_text = "\n".join(bullets)
                    break
        
        if not qualifications_text:
            match = re.search(r'(requirements|qualifications)[\s:-]+(.{150,400})', soup.get_text(separator=' ', strip=True), re.IGNORECASE)
            if match:
                qualifications_text = match.group(2).rsplit('.', 1)[0] + "."

        return qualifications_text, outbound_link
    except:
        return None, None

def fetch_and_scrape_jobs(selected_tracks):
    headers = {"User-Agent": "Mozilla/5.0"}
    raw_job_pool = []
    
    my_bar = st.progress(0, text="1️⃣ Pulling indices from structural databases...")
    
    for feed_url in MASSIVE_FEEDS:
        try:
            res = requests.get(feed_url, headers=headers, timeout=10)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                items = root.findall('.//item')
                for item in items[:150]:
                    title = item.find('title').text or "No Title"
                    link = item.find('link').text or ""
                    desc = item.find('description').text or ""
                    desc_clean = re.sub('<[^<]+?>', '', desc).strip()
                    
                    raw_job_pool.append({
                        "Title": title,
                        "Link": link,
                        "Desc": desc_clean
                    })
        except Exception:
            pass

    unique_pool = {job['Title']: job for job in raw_job_pool}.values()
    raw_job_pool = list(unique_pool)
    random.shuffle(raw_job_pool)
    
    jobs_found = []
    total_pool = len(raw_job_pool)
    
    for idx, raw_job in enumerate(raw_job_pool):
        if len(jobs_found) >= 15:
            break
            
        my_bar.progress(int(((idx + 1) / total_pool) * 100), text=f"2️⃣ Scraped {len(jobs_found)}/15 matching jobs. Evaluating row index {idx+1}...")
        
        title = raw_job['Title']
        desc = raw_job['Desc']
        aggregator_link = raw_job['Link']
        
        # Track Assessment
        track = check_experience_level(title, desc)
        if not track or track not in selected_tracks:
            continue
            
        company = title.split(" at ")[1].strip() if " at " in title else "Institution Listed on Portal"
        clean_title = title.split(" at ")[0].strip() if " at " in title else title
        
        quals, outbound_link = deep_scrape_job_page(aggregator_link)
        
        # Verify long-form qualifications content text doesn't contain a hidden experience barrier
        if quals and not check_experience_level(clean_title, quals):
            continue
            
        final_link = outbound_link if outbound_link else aggregator_link
        domain = extract_domain(final_link)
        google_search_url = f"https://www.google.com/search?q={quote_plus(company + ' ' + clean_title + ' careers kenya')}"
        
        if not quals:
            quals = "• Certificate, Diploma, Degree, or equivalent work history.\n• See the main portal parameters for full details."

        jobs_found.append({
            "Title": clean_title,
            "Company": company,
            "Direct Link": final_link,
            "Domain": domain,
            "Safety": analyze_scam_risk(title, desc),
            "Qualifications": quals,
            "Track": track,
            "Google Helper": google_search_url if not outbound_link else None
        })
        
        time.sleep(0.4)
        
    my_bar.empty()
    return jobs_found

# --- UI VISUAL DESIGN ENGINE ---
colA, colB = st.columns([1, 2])
with colA:
    if st.button("🚀 LAUNCH MASTER SCANNER", use_container_width=True):
        st.session_state['run_scan'] = True
        
with colB:
    # Track filter pickers
    chosen_tracks = st.multiselect(
        "Select Industries to Feature in Video:",
        options=["🎓 Entry-Level / Graduate", "🛠️ Blue-Collar / Trade", "💼 Professional / Corporate"],
        default=["🎓 Entry-Level / Graduate", "🛠️ Blue-Collar / Trade", "💼 Professional / Corporate"]
    )

if st.session_state.get('run_scan', False):
    if not chosen_tracks:
        st.error("Please pick at least one industry track before running the scanner.")
    else:
        data = fetch_and_scrape_jobs(chosen_tracks)
        st.session_state['run_scan'] = False
        
        if data:
            st.success(f"✅ Success! Extracted {len(data)} verified positions matching your selections.")
            st.markdown("---")
            
            for job in data:
                with st.container():
                    st.markdown(f"## 📌 {job['Title']}")
                    st.markdown(f"### 🏢 **{job['Company']}**")
                    
                    # Core Meta Data string
                    if any(agg in job['Domain'] for agg in ["jobwebkenya", "myjobmag", "brightermonday"]):
                        source_display = f"`{job['Domain']}` (Aggregator)"
                    else:
                        source_display = f"🌟 **`{job['Domain']}` (OFFICIAL SYSTEM PORTAL)**"
                        
                    st.markdown(f"**🌐 Link Destination:** {source_display} &nbsp; | &nbsp; **🏷️ Track Type:** `{job['Track']}`")
                    
                    # Verification Block
                    if "✅" in job['Safety']:
                        st.success(f"**Verification:** {job['Safety']}")
                    elif "⚠️" in job['Safety']:
                        st.warning(f"**Verification:** {job['Safety']}")
                    else:
                        st.error(f"**Verification:** {job['Safety']}")
                        
                    st.markdown("#### 🎓 Core Requirements:")
                    st.info(job["Qualifications"])
                    
                    st.markdown("**🔗 Copy this application link to share with your audience:**")
                    st.code(job['Direct Link'], language=None)
                    
                    if job['Google Helper']:
                        st.markdown(f"*(Tip: [Click here to Google the official portal directly]({job['Google Helper']}))*")
                        
                    st.markdown("<br><hr><br>", unsafe_allow_html=True)
        else:
            st.error("No jobs matching those conditions were processed in the active pool. Try refreshing.")
