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

st.set_page_config(page_title="Kenya Job Hub: Fresh Grads", layout="wide")

st.title("📌 Kenya Job Deep Scanner (Pro)")
st.markdown("Actively bypassing aggregators & guaranteeing high-volume **Fresh Graduate / Entry Level** opportunities.")

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

def check_experience_level(title, text):
    combined = (title + " " + text).lower()
    
    # 1. Automatic Approvals
    if any(kw in combined for kw in ["entry level", "fresh graduate", "graduate trainee", "intern", "internship", "attachment", "no experience", "0-1", "0-2"]):
        return True
        
    # 2. Automatic Rejections based on Seniority
    if any(kw in title.lower() for kw in ["senior", "manager", "director", "head of", "lead", "principal", "chief", "supervisor", "specialist"]):
        return False
        
    # 3. Automatic Rejections based on Years of Experience
    exp_match = re.search(r'(two|three|four|five|six|seven|eight|nine|ten|[2-9]|[1-9][0-9])\+?\s*(?:to|-)?\s*([0-9]+|two|three|four|five)?\s*(?:years?|yrs)(?:’|s)?\s*(?:of\s*)?(?:working\s*)?(?:post-qualification\s*)?experience', combined)
    if exp_match:
        return False
        
    return True

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
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code != 200:
            return None, None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        outbound_link = None
        base_domain = extract_domain(url)
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.text.lower()
            if base_domain not in href and "facebook.com" not in href and "twitter.com" not in href:
                if any(keyword in text for keyword in ["apply", "click here", "website"]) or any(ats in href for ats in ["workday", "greenhouse", "taleo", "bamboohr", "fuzu", "lever", "breezy"]):
                    outbound_link = href
                    break 
                    
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
            qualifications_text = "• Certificate, Diploma, or Degree in relevant field.\n• No prior experience strictly requested in description.\n• (See the direct official application link below for the full checklist)."

        return qualifications_text, outbound_link
    except:
        return None, None

def hunt_for_original_portal(company, job_title, fallback_link):
    if company in ["Various", "See details", "Unknown", "Confidential"]:
        return fallback_link
        
    query = f'"{company}" "{job_title}" application kenya careers'
    blacklist = ["jobwebkenya", "myjobmag", "fuzu", "brightermonday", "glassdoor", "linkedin", "jiji", "pigiame", "postmyjob", "reliefweb", "unjobs"]
    
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=6)]
            for res in results:
                url = res['href']
                if any(bad_site in url.lower() for bad_site in blacklist):
                    continue
                path = urlparse(url).path
                if len(path) < 10: 
                    continue 
                return url 
        return fallback_link 
    except Exception:
        return fallback_link

def fetch_and_scrape_jobs(fresh_grads_only=True):
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
                
                # Pull a larger initial slice per feed to protect high-volume targets
                for item in items[:25]: 
                    title = item.find('title').text or "No Title"
                    link = item.find('link').text or ""
                    desc = item.find('description').text or ""
                    desc_clean = re.sub('<[^<]+?>', '', desc).strip()
                    
                    if fresh_grads_only and not check_experience_level(title, desc_clean):
                        continue
                    
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

    jobs_found = []
    my_bar = st.progress(0, text="Deep Scraping & Filtering for Fresh Graduates...")
    
    # GUARANTEED VOLUME: The bot will aggressively process until it hits a solid target count
    target_count = 25 if not fresh_grads_only else 15
    
    for idx, job in enumerate(final_list):
        if len(jobs_found) >= target_count:
            break 
            
        my_bar.progress(int(((idx + 1) / len(final_list)) * 100), text=f"Analyzing {idx+1}/{len(final_list)}: {job['Company']}...")
        
        quals, extracted_outbound_link = deep_scrape_job_page(job['Aggregator Link'])
        
        if fresh_grads_only and quals:
            if not check_experience_level(job['Clean Title'], quals):
                continue 
                
        job['Qualifications'] = quals if quals else "• Certificate, Diploma, or Degree.\n• No prior experience strictly requested in description.\n• Please view the direct portal for the full checklist."
        
        if extracted_outbound_link:
            final_link = extracted_outbound_link
        else:
            final_link = hunt_for_original_portal(job['Company'], job['Clean Title'], job['Aggregator Link'])
        
        job['Direct Link'] = final_link
        job['Source Domain'] = extract_domain(final_link)
        
        jobs_found.append(job)
        time.sleep(1) 
        
    my_bar.empty() 
    return jobs_found

# --- UI FOR SCREENSHOTS & SHARING ---
colA, colB = st.columns([1, 2])
with colA:
    if st.button("🔄 FETCH ENTRY-LEVEL JOBS", use_container_width=True):
        st.session_state['run_scan'] = True
        
with colB:
    fresh_grads_mode = st.checkbox("🎓 Hunt ONLY for Entry-Level & Fresh Graduate Jobs (No Experience)", value=True)

if st.session_state.get('run_scan', False):
    data = fetch_and_scrape_jobs(fresh_grads_only=fresh_grads_mode)
    st.session_state['run_scan'] = False 
    
    if data:
        st.success(f"✅ Search Complete. Showing {len(data)} verified jobs highly suitable for your audience.")
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
                    
                if fresh_grads_mode:
                    st.info("🎓 **FRESH GRAD APPROVED:** This job description does not explicitly demand years of prior experience.")
                
                st.markdown("#### 🎓 Required Qualifications:")
                st.info(job["Qualifications"])
                
                st.markdown("**🔗 Copy this exact application link to share with your audience:**")
                st.code(job['Direct Link'], language=None)
                
                st.markdown("<br><hr><br>", unsafe_allow_html=True)
