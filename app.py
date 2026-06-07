import datetime
import re
import time
import random
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import streamlit as st
from urllib.parse import urlparse

st.set_page_config(page_title="Kenya Job Hub: Screenshot & Share", layout="wide")

st.title("📌 Kenya Job Deep Scanner (Pro)")
st.markdown("Generates fresh, randomized jobs. Includes deep-scraped qualifications, scam detection, and 1-click copyable links.")

# Massively expanded source list for diversity
JOB_FEEDS = [
    "https://jobwebkenya.com/feed/",
    "https://reliefweb.int/updates.rss?search=location.name:Kenya%20AND%20format.name:Job",
    "https://unjobs.org/rss/countries/ken", # UN & NGO Jobs in Kenya
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
    """Brings back the Legitimacy Tracker"""
    score = 0
    text = (title + " " + description).lower()
    
    for pattern in SCAM_KEYWORDS:
        if re.search(pattern, text):
            score += 60
            
    if score >= 60:
        return "❌ HIGH RISK SCAM - Asks for money upfront."
    elif "yahoo.com" in text or "gmail.com" in text:
        return "⚠️ SUSPICIOUS - Uses a free email address for applications."
    else:
        return "✅ LEGITIMATE - No obvious scam markers detected."

def extract_domain(url):
    """Extracts the base website name so you know it's not all from one place."""
    try:
        domain = urlparse(url).netloc
        return domain.replace("www.", "")
    except:
        return "External Website"

def deep_scrape_job_page(url):
    """Visits the job page for qualifications and direct application links."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code != 200:
            return None, None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Hunt for the true application link
        direct_link = url
        for a in soup.find_all('a', href=True):
            link_text = a.text.lower()
            href = a['href']
            if any(keyword in link_text for keyword in ["apply now", "click here", "application form"]) or "mailto:" in href:
                if "facebook" not in href and "twitter" not in href:
                    direct_link = href
                    break

        # 2. Extract bullet points for Qualifications
        qualifications_text = ""
        headings = soup.find_all(['h2', 'h3', 'h4', 'strong', 'b'])
        for tag in headings:
            if tag.text and any(q in tag.text.lower() for q in ["qualification", "requirement", "skills", "experience"]):
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
            qualifications_text = "• Standard professional requirements apply.\n• (See direct application link below for the full checklist)."

        return qualifications_text, direct_link
    except:
        return None, None

def fetch_and_scrape_jobs():
    headers = {"User-Agent": "Mozilla/5.0"}
    links_to_scrape = []
    
    # Randomize the feeds so it starts looking in a different place every time
    random.shuffle(JOB_FEEDS)
    
    for url in JOB_FEEDS:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                items = root.findall('.//item')
                random.shuffle(items) # Shuffle jobs within the feed
                
                for item in items[:10]: # Pick a random subset from each feed
                    title = item.find('title').text or "No Title"
                    link = item.find('link').text or ""
                    desc = item.find('description').text or ""
                    
                    desc_clean = re.sub('<[^<]+?>', '', desc).strip()
                    
                    # Extract basic details
                    company = title.split(" at ")[1].strip() if " at " in title else "See details"
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
                        "Link": link,
                        "Safety": safety_status,
                        "Source Domain": extract_domain(link)
                    })
        except:
            pass

    # Deduplicate and pick exactly 25 random jobs for this session
    unique_jobs = {job['Clean Title']: job for job in links_to_scrape}.values()
    final_list = list(unique_jobs)
    random.shuffle(final_list)
    final_list = final_list[:25] 

    jobs_found = []
    my_bar = st.progress(0, text="Performing Deep Scrape (This takes 2-3 minutes)...")
    
    for idx, job in enumerate(final_list):
        my_bar.progress(int(((idx + 1) / len(final_list)) * 100), text=f"Deep Scraping {idx+1}/{len(final_list)}: {job['Company']}...")
        
        quals, direct_link = deep_scrape_job_page(job['Link'])
        job['Qualifications'] = quals if quals else "• Please view the direct portal for the full required checklist."
        
        # If deep scraper found a better link, use it and update the domain
        job['Direct Link'] = direct_link if direct_link else job['Link']
        job['Source Domain'] = extract_domain(job['Direct Link'])
        
        jobs_found.append(job)
        time.sleep(0.5) # Anti-ban delay
        
    my_bar.empty() 
    return jobs_found

# --- UI FOR SCREENSHOTS & SHARING ---

# The "Search Again" button
colA, colB = st.columns([1, 3])
with colA:
    if st.button("🔄 FETCH NEW BATCH OF JOBS", use_container_width=True):
        st.session_state['run_scan'] = True
        
with colB:
    st.info("Click the button to shuffle sources and pull a brand new batch of 25 jobs.")

if st.session_state.get('run_scan', False):
    data = fetch_and_scrape_jobs()
    st.session_state['run_scan'] = False # Reset so it doesn't loop
    
    if data:
        st.success(f"✅ Deep Search Complete. Showing {len(data)} randomized jobs.")
        st.markdown("---")
        
        for job in data:
            with st.container():
                st.markdown(f"## 📌 {job['Clean Title']}")
                st.markdown(f"### 🏢 **{job['Company']}**")
                
                # Meta Data including the Source Domain
                st.markdown(f"**📍 Location:** {job['City']} &nbsp; | &nbsp; **⏳ Deadline:** {job['Expiry']} &nbsp; | &nbsp; **🌐 Source:** `{job['Source Domain']}`")
                
                # The Legitimacy Box
                if "✅" in job['Safety']:
                    st.success(f"**Security Scan:** {job['Safety']}")
                elif "⚠️" in job['Safety']:
                    st.warning(f"**Security Scan:** {job['Safety']}")
                else:
                    st.error(f"**Security Scan:** {job['Safety']}")
                
                # Qualifications Box
                st.markdown("#### 🎓 Required Qualifications:")
                st.info(job["Qualifications"])
                
                # The Copyable Link Box
                st.markdown("**🔗 Copy this direct link to share with your audience/applicants:**")
                st.code(job['Direct Link'], language=None)
                
                st.markdown("<br><hr><br>", unsafe_allow_html=True)
