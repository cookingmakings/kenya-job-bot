import datetime
import re
import time
import random
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import streamlit as st
from urllib.parse import urlparse
from duckduckgo_search import DDGS

st.set_page_config(page_title="Kenya Job Hub: Screenshot & Share", layout="wide")

st.title("📌 Kenya Job Deep Scanner (Pro)")
st.markdown("Actively bypassing aggregators using **Deep-Link Verification** and ATS (Applicant Tracking System) extraction.")

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

def deep_scrape_job_page(url):
    """
    Scrapes for qualifications AND forcefully extracts hidden outbound application links.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code != 200:
            return None, None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Forcefully hunt for the hidden OUTBOUND link
        outbound_link = None
        base_domain = extract_domain(url)
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.text.lower()
            
            # If the link leaves the aggregator site
            if base_domain not in href and "facebook.com" not in href and "twitter.com" not in href and "whatsapp.com" not in href:
                # Check if it looks like an application portal or button
                if any(keyword in text for keyword in ["apply", "click here", "website"]) or any(ats in href for ats in ["workday", "greenhouse", "taleo", "bamboohr", "fuzu", "lever", "breezy"]):
                    outbound_link = href
                    break # Found the real portal!
                    
        # 2. Scrape Qualifications
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

        return qualifications_text, outbound_link
    except:
        return None, None

def hunt_for_original_portal(company, job_title, fallback_link):
    """
    Uses DuckDuckGo but enforces the 'No Homepages' rule.
    """
    if company in ["Various", "See details", "Unknown", "Confidential"]:
        return fallback_link
        
    query = f'"{company}" "{job_title}" application kenya careers'
    blacklist = ["jobwebkenya", "myjobmag", "fuzu", "brightermonday", "glassdoor", "linkedin", "jiji", "pigiame", "postmyjob", "reliefweb", "unjobs"]
    
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=6)]
            for res in results:
                url = res['href']
                
                # 1. Ignore aggregators
                if any(bad_site in url.lower() for bad_site in blacklist):
                    continue
                    
                # 2. THE NO HOMEPAGES RULE: Check if it's a deep link
                path = urlparse(url).path
                # If the URL path is too short (e.g., just "/" or "/home"), it's a homepage. Reject it.
                if len(path) < 10:
                    continue 
                    
                return url # It's an official deep link!
        return fallback_link 
    except Exception:
        return fallback_link

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
    my_bar = st.progress(0, text="Deep Scraping & Extracting ATS Links (This takes ~3 mins)...")
    
    for idx, job in enumerate(final_list):
        my_bar.progress(int(((idx + 1) / len(final_list)) * 100), text=f"Scanning {idx+1}/{len(final_list)}: {job['Company']}...")
        
        # 1. Scrape for qualifications AND extract any hidden outbound links
        quals, extracted_outbound_link = deep_scrape_job_page(job['Aggregator Link'])
        job['Qualifications'] = quals if quals else "• Please view the direct portal below for the full required checklist."
        
        # 2. Determine the best link to use
        if extracted_outbound_link:
            # If we successfully ripped the hidden outbound link from the aggregator, use it!
            final_link = extracted_outbound_link
        else:
            # If it's heavily hidden, hunt the web for a deep link (ignoring homepages)
            final_link = hunt_for_original_portal(job['Company'], job['Clean Title'], job['Aggregator Link'])
        
        job['Direct Link'] = final_link
        job['Source Domain'] = extract_domain(final_link)
        
        jobs_found.append(job)
        time.sleep(1) 
        
    my_bar.empty() 
    return jobs_found

# --- UI FOR SCREENSHOTS & SHARING ---
colA, colB = st.columns([1, 3])
with colA:
    if st.button("🔄 FETCH & HUNT OFFICIAL LINKS", use_container_width=True):
        st.session_state['run_scan'] = True
        
with colB:
    st.info("The bot now extracts hidden outbound links and uses Deep-Link Web Hunting to ensure you get exact application pages, not homepages.")

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
                
                if "jobwebkenya" in job['Source Domain'] or "myjobmag" in job['Source Domain'] or "unjobs" in job['Source Domain']:
                    source_display = f"`{job['Source Domain']}` (Aggregator Used)"
                else:
                    source_display = f"🌟 **`{job['Source Domain']}` (OFFICIAL APPLICATION PAGE)**"

                st.markdown(f"**📍 Location:** {job['City']} &nbsp; | &nbsp; **⏳ Deadline:** {job['Expiry']} &nbsp; | &nbsp; **🌐 Source:** {source_display}")
                
                if "✅" in job['Safety']:
                    st.success(f"**Security Scan:** {job['Safety']}")
                else:
                    st.error(f"**Security Scan:** {job['Safety']}")
                
                st.markdown("#### 🎓 Required Qualifications:")
                st.info(job["Qualifications"])
                
                st.markdown("**🔗 Copy this exact application link to share with your audience:**")
                st.code(job['Direct Link'], language=None)
                
                st.markdown("<br><hr><br>", unsafe_allow_html=True)
