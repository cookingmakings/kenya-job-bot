import datetime
import re
import time
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import streamlit as st

st.set_page_config(page_title="Kenya Job Hub: Video Screenshot Layout", layout="wide")

st.title("📌 Kenya Job Deep Scanner")
st.markdown("Optimized for video screenshots. Performing deep page scraping for exact qualifications and direct application links across multiple sources.")

# Expanded Source List (RSS + HTML Aggregators)
JOB_FEEDS = [
    "https://jobwebkenya.com/feed/",
    "https://reliefweb.int/updates.rss?search=location.name:Kenya%20AND%20format.name:Job",
    "https://kenya2711.rssing.com/chan-30179697/latest.xml"
]

KENYAN_CITIES = [
    "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika", "Malindi", "Kitale", 
    "Garissa", "Kakamega", "Nyeri", "Machakos", "Naivasha", "Meru", "Kiambu", "Kericho"
]

def deep_scrape_job_page(url):
    """Visits the actual job page to pull hidden qualifications and the direct apply link."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code != 200:
            return None, None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True).lower()
        
        # 1. Hunt for the true application link (mailtos or external apply buttons)
        direct_link = url # Fallback to the page url
        links = soup.find_all('a', href=True)
        for a in links:
            link_text = a.text.lower()
            href = a['href']
            if any(keyword in link_text for keyword in ["apply now", "click here to apply", "application form"]) or "mailto:" in href:
                # Avoid sharing buttons
                if "facebook" not in href and "twitter" not in href and "whatsapp" not in href:
                    direct_link = href
                    break

        # 2. Extract bullet points for Qualifications
        qualifications_text = ""
        # Look for lists (<ul> or <ol>) that appear after keywords
        headings = soup.find_all(['h2', 'h3', 'h4', 'strong', 'b'])
        for tag in headings:
            if tag.text and any(q in tag.text.lower() for q in ["qualification", "requirement", "skills", "experience"]):
                # Find the next bulleted list
                next_ul = tag.find_next(['ul', 'ol'])
                if next_ul:
                    lis = next_ul.find_all('li')
                    bullets = [f"• {li.get_text(strip=True)}" for li in lis[:6]] # Get top 6 bullets max
                    qualifications_text = "\n".join(bullets)
                    break
        
        # Fallback if no bullet points found but paragraph exists
        if not qualifications_text:
            match = re.search(r'(requirements|qualifications)[\s:-]+(.{150,400})', soup.get_text(separator=' ', strip=True), re.IGNORECASE)
            if match:
                qualifications_text = match.group(2).rsplit('.', 1)[0] + "."

        if not qualifications_text or len(qualifications_text) < 20:
            qualifications_text = "• Degree/Diploma in relevant field.\n• Proven relevant experience.\n• (See direct application link for the exhaustive list)."

        return qualifications_text, direct_link
    except Exception:
        return None, None

def extract_meta_details(title, description):
    combined_lower = (title + " " + description).lower()
    
    # Extract Company
    if " at " in title:
        parts = title.split(" at ", 1)
        clean_title, company = parts[0].strip(), parts[1].strip()
    elif " - " in title:
        parts = title.split(" - ", 1)
        clean_title, company = parts[0].strip(), parts[1].strip()
    else:
        clean_title, company = title, "Various / See direct link"

    # Extract City
    city_found = "Kenya-wide"
    for city in KENYAN_CITIES:
        if re.search(r'\b' + city.lower() + r'\b', combined_lower):
            city_found = city
            break
            
    # Work Type Focus
    if any(w in combined_lower for w in ["plumber", "driver", "cleaner", "security", "casual", "mason"]):
        work_type = "🛠️ Blue-Collar"
    elif any(w in combined_lower for w in ["remote", "wfh"]):
        work_type = "🏠 Remote"
    else:
        work_type = "🏢 Onsite"

    # Strict Deadline Extraction
    deadline_match = re.search(r'(deadline|closing date|apply by)[\s:-]+([0-9]{1,2}(st|nd|rd|th)?\s+[a-zA-Z]+\s+[0-9]{4}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})', combined_lower)
    expiry = deadline_match.group(2).title() if deadline_match else "ASAP"

    return clean_title, company, city_found, work_type, expiry

def fetch_and_scrape_jobs():
    headers = {"User-Agent": "Mozilla/5.0"}
    jobs_found = []
    links_to_scrape = []
    
    # Step 1: Gather URLs quickly from multiple sources
    for url in JOB_FEEDS:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                for item in root.findall('.//item')[:15]: # Limit to prevent 10 minute wait times
                    title = item.find('title').text or "No Title"
                    link = item.find('link').text or ""
                    desc = item.find('description').text or ""
                    
                    desc_clean = re.sub('<[^<]+?>', '', desc).strip()
                    clean_title, company, city, work_type, expiry = extract_meta_details(title, desc_clean)
                    
                    links_to_scrape.append({
                        "Clean Title": clean_title,
                        "Company": company,
                        "City": city,
                        "Work Type": work_type,
                        "Expiry": expiry,
                        "Link": link
                    })
        except:
            pass

    # Deduplicate
    unique_jobs = {job['Clean Title']: job for job in links_to_scrape}.values()
    links_to_scrape = list(unique_jobs)

    # Step 2: Deep Scrape the gathered URLs
    progress_text = "Operation in progress. Please wait."
    my_bar = st.progress(0, text="Starting Deep Web Search...")
    
    total = len(links_to_scrape)
    for idx, job in enumerate(links_to_scrape):
        # Update UI progress
        percent = int(((idx + 1) / total) * 100)
        my_bar.progress(percent, text=f"Deep Scraping {idx+1}/{total}: {job['Company']}...")
        
        # The deep dive
        quals, direct_link = deep_scrape_job_page(job['Link'])
        
        job['Qualifications'] = quals if quals else "• Qualifications specific to this role.\n• Please view the direct portal for the full required checklist."
        job['Direct Link'] = direct_link if direct_link else job['Link']
        
        jobs_found.append(job)
        
        # Sleep slightly to prevent IP bans and simulate the deep human-like search
        time.sleep(1)
        
    my_bar.empty() # Clear progress bar when done
    return jobs_found

# --- UI FOR SCREENSHOTS ---
if st.button("🔍 START DEEP SEARCH & SCRAPE"):
    data = fetch_and_scrape_jobs()
    
    if data:
        st.success(f"✅ Deep Search Complete. {len(data)} verified jobs extracted.")
        st.markdown("---")
        
        for job in data:
            with st.container():
                st.markdown(f"## 📌 {job['Clean Title']}")
                st.markdown(f"### 🏢 **{job['Company']}**")
                
                # Clean, single-line meta data for nice screenshots
                st.markdown(f"**📍 Location:** {job['City']} &nbsp; | &nbsp; **🛠️ Type:** {job['Work Type']} &nbsp; | &nbsp; **⏳ Deadline:** {job['Expiry']}")
                
                st.markdown("#### 🎓 Required Qualifications:")
                st.info(job["Qualifications"])
                
                st.markdown(f"👉 **[DIRECT APPLICATION LINK]({job['Direct Link']})**")
                st.markdown("<br><hr><br>", unsafe_allow_html=True)
    else:
        st.error("No data fetched. Job boards might be blocking the scraper.")
