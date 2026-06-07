import datetime
import re
import time
import random
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import streamlit as st
from urllib.parse import urlparse
from duckduckgo_search import DDGS  # The new Unblockable Search Engine

st.set_page_config(page_title="Kenya Job Hub: Screenshot & Share", layout="wide")

st.title("📌 Kenya Job Deep Scanner (Pro)")
st.markdown("Actively bypassing aggregators using **DuckDuckGo AI Search** to find the original hiring company's direct application portal.")

JOB_FEEDS = [
    "https://jobwebkenya.com/feed/",
    "https://reliefweb.int/updates.rss?search=location.name:Kenya%20AND%20format.name:Job",
    "https://unjobs.org/rss/countries/ken",
    "https://kenya2711.rssing.com/chan-30179697/latest.xml",
    "https://www.myjobmag.co.ke/jobs-by-date.xml"
]

KENYAN_CITIES = [
    "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika", "Malindi", "Kitale", 
    "Garissa", "Kakamega", "Nyeri", "Machakos", "Naivasha", "Meru", "Kiambu", "Kericho"
]

SCAM_KEYWORDS = [
    r"registration fee", r"booking fee", r"medical fee", r"processing fee",
    r"training fee", r"uniform fee", r"send money", r"mpesa", r"m-pesa",
    r"deposit", r"bribe", r"pay to work"
]

def analyze_scam_risk(title, description):
    score = 0
    text = (title + " " + description).lower()
    for pattern in SCAM_KEYWORDS:
        if re.search(pattern, text):
            score += 60
    if score >= 60:
        return "❌ HIGH RISK SCAM - Asks for money upfront."
    elif "yahoo.com" in text or "gmail.com" in text:
        return "⚠️ SUSPICIOUS - Uses a free email address."
    else:
        return "✅ LEGITIMATE - No obvious scam markers detected."

def extract_domain(url):
    try:
        domain = urlparse(url).netloc
        return domain.replace("www.", "")
    except:
        return "External Website"

def hunt_for_original_portal(company, job_title, fallback_link):
    """
    Uses DuckDuckGo to aggressively bypass aggregators and find the true company portal.
    """
    if company in ["Various", "See details", "Unknown", "Confidential"]:
        return fallback_link
        
    query = f'"{company}" "{job_title}" application kenya careers'
    
    # The list of sites we want to IGNORE so we get the real company
    blacklist = ["jobwebkenya", "myjobmag", "fuzu", "brightermonday", "glassdoor", "linkedin", "jiji", "pigiame", "postmyjob", "reliefweb", "unjobs"]
    
    try:
        with DDGS() as ddgs:
            # Get top 5 search results
            results = [r for r in ddgs.text(query, max_results=5)]
            for res in results:
                url = res['href']
                # If the search result is NOT a known aggregator, we found the official site!
                if not any(bad_site in url.lower() for bad_site in blacklist):
                    return url
        return fallback_link 
    except Exception:
        return fallback_link

def deep_scrape_job_page(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
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

        if not qualifications_text or len(qualifications_text) < 20:
            qualifications_text = "• Standard professional requirements apply.\n• (See the direct official application link below for the full checklist)."

        return qualifications_text
    except:
        return None

def fetch_and_scrape_jobs():
    headers = {"User-Agent": "Mozilla/5.0"}
    links_to_scrape = []
    
    random.shuffle(JOB_FEEDS)
    
    for url in JOB_FEEDS:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                items = root.findall('.//item')
                random.shuffle(items)
                
                for item in items[:10]:
                    title = item.find('title').text or "No Title"
                    link = item.find('link').text or ""
                    desc = item.find('description').text or ""
                    desc_clean = re.sub('<[^<]+?>', '', desc).strip()
                    
                    company = title.split(" at ")[1].strip() if " at " in title else "Unknown"
                    clean_title = title.split(" at ")[0].strip() if " at " in title else title
                    
                    city_found = "Kenya-wide"
                    for city in KENYAN_CITIES:
                        if re.search(r'\b' + city.lower() + r'\b', (title+" "+desc_clean).lower()):
                            city_found = city
                            break
                            
                    deadline_match = re.search(r'(deadline|closing date)[\s:-]+([0-9]{1,2}(st|nd|rd|th)?\s+[a-zA-Z]+\s+[0-9]{4})', desc_clean.lower())
                    expiry = deadline_match.group(2).title() if deadline_match else "ASAP"
                    
                    safety_status = analyze_scam_risk(title, desc_clean)
                    
                    links_to_scrape.append({
                        "Clean Title": clean_title,
                        "Company": company,
                        "City": city_found,
                        "Expiry": expiry,
                        "Aggregator Link": link,
                        "Safety": safety_status
                    })
        except:
            pass

    unique_jobs = {job['Clean Title']: job for job in links_to_scrape}.values()
    final_list = list(unique_jobs)
    random.shuffle(final_list)
    final_list = final_list[:25] 

    jobs_found = []
    my_bar = st.progress(0, text="Deep Scraping & Hunting for Official Portals (This will take 3 mins)...")
    
    for idx, job in enumerate(final_list):
        my_bar.progress(int(((idx + 1) / len(final_list)) * 100), text=f"Hunting {idx+1}/{len(final_list)}: {job['Company']}...")
        
        # 1. Scrape the aggregator for the bullets
        quals = deep_scrape_job_page(job['Aggregator Link'])
        job['Qualifications'] = quals if quals else "• Please view the direct portal below for the full required checklist."
        
        # 2. actively hunt DuckDuckGo for the REAL link (Bypassing Google's blocks)
        real_link = hunt_for_original_portal(job['Company'], job['Clean Title'], job['Aggregator Link'])
        
        job['Direct Link'] = real_link
        job['Source Domain'] = extract_domain(real_link)
        
        jobs_found.append(job)
        time.sleep(1) # Delay so DuckDuckGo doesn't block the bot
        
    my_bar.empty() 
    return jobs_found

# --- UI FOR SCREENSHOTS & SHARING ---
colA, colB = st.columns([1, 3])
with colA:
    if st.button("🔄 FETCH & HUNT OFFICIAL LINKS", use_container_width=True):
        st.session_state['run_scan'] = True
        
with colB:
    st.info("The bot uses DuckDuckGo AI search to aggressively bypass aggregators and find the original company websites.")

if st.session_state.get('run_scan', False):
    data = fetch_and_scrape_jobs()
    st.session_state['run_scan'] = False 
    
    if data:
        st.success(f"✅ Deep Search & Hunt Complete. Showing {len(data)} randomized jobs.")
        st.markdown("---")
        
        for job in data:
            with st.container():
                st.markdown(f"## 📌 {job['Clean Title']}")
                st.markdown(f"### 🏢 **{job['Company']}**")
                
                # Check if the bot successfully bypassed the aggregator
                if "jobwebkenya" in job['Source Domain'] or "myjobmag" in job['Source Domain'] or "unjobs" in job['Source Domain']:
                    source_display = f"`{job['Source Domain']}` (Aggregator Used)"
                else:
                    source_display = f"🌟 **`{job['Source Domain']}` (OFFICIAL COMPANY PORTAL)**"

                st.markdown(f"**📍 Location:** {job['City']} &nbsp; | &nbsp; **⏳ Deadline:** {job['Expiry']} &nbsp; | &nbsp; **🌐 Source:** {source_display}")
                
                if "✅" in job['Safety']:
                    st.success(f"**Security Scan:** {job['Safety']}")
                else:
                    st.error(f"**Security Scan:** {job['Safety']}")
                
                st.markdown("#### 🎓 Required Qualifications:")
                st.info(job["Qualifications"])
                
                st.markdown("**🔗 Copy this direct link to share with your audience:**")
                st.code(job['Direct Link'], language=None)
                
                st.markdown("<br><hr><br>", unsafe_allow_html=True)
