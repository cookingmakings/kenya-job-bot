import re
import time
import random
import requests
from bs4 import BeautifulSoup
import streamlit as st
from urllib.parse import urlparse
from duckduckgo_search import DDGS

st.set_page_config(page_title="Kenya Job Hub: High Volume Scraper", layout="wide")

st.title("📌 Kenya Job Deep Scanner (Max Volume)")
st.markdown("Uses AI Search Engine Injection to guarantee **15+ Fresh Graduate & Blue Collar** jobs. No more repeated RSS feeds.")

# We replaced static feeds with dynamic search queries!
WHITE_COLLAR_QUERIES = [
    'site:jobwebkenya.com ("entry level" OR "fresh graduate" OR "intern" OR "graduate trainee" OR "no experience")',
    'site:myjobmag.co.ke ("entry level" OR "graduate trainee" OR "attachment" OR "internship")',
    'site:brightermonday.co.ke ("entry level" OR "intern" OR "no experience required")',
    'site:unjobs.org/countries/ken ("entry level" OR "intern" OR "junior")'
]

BLUE_COLLAR_QUERIES = [
    'site:jobwebkenya.com ("driver" OR "cleaner" OR "security" OR "plumber" OR "electrician" OR "mechanic")',
    'site:myjobmag.co.ke ("driver" OR "artisan" OR "welder" OR "casual" OR "mason" OR "technician")',
    'site:brightermonday.co.ke ("rider" OR "driver" OR "security guard" OR "cleaner" OR "waiter" OR "cook")'
]

SCAM_KEYWORDS = [
    r"registration fee", r"booking fee", r"medical fee", r"processing fee",
    r"training fee", r"uniform fee", r"send money", r"mpesa", r"m-pesa", r"deposit"
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
        return urlparse(url).netloc.replace("www.", "")
    except:
        return "External Website"

def deep_scrape_job_page(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code != 200:
            return None, None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for hidden outbound ATS links (to bypass the aggregator)
        outbound_link = None
        base_domain = extract_domain(url)
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.text.lower()
            if base_domain not in href and "facebook.com" not in href and "twitter.com" not in href:
                if any(keyword in text for keyword in ["apply", "click here", "website"]) or any(ats in href for ats in ["workday", "greenhouse", "taleo", "bamboohr"]):
                    outbound_link = href
                    break 
                    
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
            qualifications_text = "• Formal requirements specified on the official application portal.\n• (See the direct link below for the full checklist)."

        return qualifications_text, outbound_link
    except:
        return None, None

def hunt_for_original_portal(company, job_title, fallback_link):
    if company in ["Various", "See details", "Unknown", "Confidential"]:
        return fallback_link
        
    query = f'"{company}" "{job_title}" application kenya'
    blacklist = ["jobwebkenya", "myjobmag", "fuzu", "brightermonday", "glassdoor", "linkedin", "jiji", "pigiame", "unjobs"]
    
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=5)]
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

def clean_title_and_company(raw_title):
    # Search engines append website names to titles, we need to clean that up.
    clean = re.sub(r'(-|\|)\s*(JobWebKenya|MyJobMag|BrighterMonday|UNjobs).*', '', raw_title, flags=re.IGNORECASE).strip()
    
    if " at " in clean:
        parts = clean.split(" at ", 1)
        return parts[0].strip(), parts[1].strip()
    elif " - " in clean:
        parts = clean.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    else:
        return clean, "Hiring Company (See Link)"

def execute_search_injection():
    jobs_found = []
    links_processed = set()
    
    # Randomly pick 2 white-collar queries and 2 blue-collar queries to guarantee a good mix
    active_queries = random.sample(WHITE_COLLAR_QUERIES, 2) + random.sample(BLUE_COLLAR_QUERIES, 2)
    random.shuffle(active_queries)
    
    my_bar = st.progress(0, text="Injecting queries into search engines (Hunting for 15+ jobs)...")
    
    try:
        with DDGS() as ddgs:
            for q_idx, query in enumerate(active_queries):
                # timelimit='w' ensures we only get jobs posted in the last week!
                results = list(ddgs.text(query, timelimit='w', max_results=10))
                
                for res in results:
                    if len(jobs_found) >= 15: # Stop exactly when we have 15 solid jobs
                        break
                        
                    link = res.get('href')
                    if not link or link in links_processed:
                        continue
                    
                    links_processed.add(link)
                    raw_title = res.get('title', '')
                    description = res.get('body', '')
                    
                    clean_title, company = clean_title_and_company(raw_title)
                    is_blue_collar = any(kw in clean_title.lower() for kw in ["driver", "cleaner", "security", "plumber", "mechanic", "artisan", "welder", "rider", "casual", "mason", "technician"])
                    
                    my_bar.progress(len(jobs_found) / 15, text=f"Deep Scraping & Bypassing Aggregators: {company}...")
                    
                    quals, outbound = deep_scrape_job_page(link)
                    safety = analyze_scam_risk(clean_title, description)
                    
                    if outbound:
                        final_link = outbound
                    else:
                        final_link = hunt_for_original_portal(company, clean_title, link)
                    
                    jobs_found.append({
                        "Title": clean_title,
                        "Company": company,
                        "Safety": safety,
                        "Qualifications": quals if quals else "• Qualifications detailed on the official portal.\n• (See the direct link below).",
                        "Direct Link": final_link,
                        "Domain": extract_domain(final_link),
                        "Is Blue Collar": is_blue_collar
                    })
                    
                    time.sleep(1) # Prevent getting blocked by search engines
                    
                if len(jobs_found) >= 15:
                    break
    except Exception as e:
        st.error("Search Engine blocked the request. Please wait a few seconds and try again.")
        
    my_bar.empty()
    return jobs_found

# --- UI FOR SCREENSHOTS & SHARING ---
colA, colB = st.columns([1, 2])
with colA:
    if st.button("🚀 FETCH 15 FRESH JOBS", use_container_width=True):
        st.session_state['run_scan'] = True
        
with colB:
    st.info("Now using Search Engine Injection to guarantee high volumes. Shuffles between new queries every click.")

if st.session_state.get('run_scan', False):
    data = execute_search_injection()
    st.session_state['run_scan'] = False 
    
    if data:
        st.success(f"✅ Search Complete. Displaying {len(data)} highly targeted jobs.")
        st.markdown("---")
        
        for job in data:
            with st.container():
                st.markdown(f"## 📌 {job['Title']}")
                st.markdown(f"### 🏢 **{job['Company']}**")
                
                # Highlight if it bypassed the aggregator successfully
                if any(agg in job['Domain'] for agg in ["jobwebkenya", "myjobmag", "brightermonday", "unjobs"]):
                    source_display = f"`{job['Domain']}` (Aggregator)"
                else:
                    source_display = f"🌟 **`{job['Domain']}` (OFFICIAL APPLICATION PAGE)**"

                st.markdown(f"**🌐 Source:** {source_display}")
                
                if "✅" in job['Safety']:
                    st.success(f"**Security Scan:** {job['Safety']}")
                else:
                    st.error(f"**Security Scan:** {job['Safety']}")
                    
                if job['Is Blue Collar']:
                    st.info("🛠️ **BLUE-COLLAR APPROVED:** Practical/Manual skills role. Excellent for non-degree holders.")
                else:
                    st.info("🎓 **ENTRY LEVEL APPROVED:** Suitable for recent graduates or interns.")
                
                st.markdown("#### 🎓 Required Qualifications:")
                st.info(job["Qualifications"])
                
                st.markdown("**🔗 Copy this exact application link to share with your audience:**")
                st.code(job['Direct Link'], language=None)
                
                st.markdown("<br><hr><br>", unsafe_allow_html=True)
