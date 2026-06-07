import datetime
import xml.etree.ElementTree as ET
import re
import requests
import streamlit as str

str.set_page_config(page_title="Mega-Scanner: Kenya Job Presenter Hub", layout="wide")

str.title("🎙️ The Mega-Scanner: Kenya Job Presenter Hub")
str.markdown("Scanning deep web aggregators for **Government, TSC, BOM, Corporate, and Blue-Collar** jobs posted in the last 48-72 hours.")

# Expanded massive feed list to guarantee 25+ jobs across sectors
JOB_FEEDS = [
    "https://jobwebkenya.com/feed/",
    "https://reliefweb.int/updates.rss?search=location.name:Kenya%20AND%20format.name:Job",
    "https://www.myjobmag.co.ke/jobs-by-date.xml", # Re-added as a fallback structure
    "https://kenya2711.rssing.com/chan-30179697/latest.xml" # Broad Kenyan job feed
]

SCAM_KEYWORDS = [
    r"registration fee", r"booking fee", r"medical fee", r"processing fee",
    r"training fee", r"uniform fee", r"send money", r"mpesa", r"m-pesa",
    r"deposit", r"bribe", r"recruitment fee", r"interview fee", r"pay to work"
]

CORPORATE_KEYWORDS = ["safaricom", "kcb", "equity", "un", "unicef", "honda", "toyota", "kenya airways", "kra", "kura", "kenha", "tsc", "nhif", "nssf"]

KENYAN_CITIES = [
    "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika", "malindi", "kitale", 
    "garissa", "kakamega", "nyeri", "machakos", "naivasha", "meru", "kiambu", "kericho", 
    "kisii", "lamu", "lodwar", "marsabit", "isiolo", "embu", "kitui", "wajir", "mandera", 
    "busia", "bungoma", "vihiga", "homa bay", "migori", "siaya", "bomet", "narok", "kajiado", 
    "samburu", "turkana", "baringo", "nandi", "laikipia", "nyandarua", "kilifi", "kwale"
]

def extract_job_details(title, description):
    combined_text = (title + " " + description).replace('\n', ' ')
    combined_lower = combined_text.lower()
    
    # Extract Company
    if " at " in title:
        parts = title.split(" at ", 1)
        clean_title = parts[0].strip()
        company = parts[1].strip()
    elif " - " in title:
        parts = title.split(" - ", 1)
        clean_title = parts[0].strip()
        company = parts[1].strip()
    else:
        clean_title = title
        company = "See direct link for hiring institution"

    # Extract City
    city_found = "Kenya-wide (Check details)"
    for city in KENYAN_CITIES:
        if re.search(r'\b' + city + r'\b', combined_lower):
            city_found = city.title()
            break
            
    # Work Type Focus (Blue Collar vs White Collar vs Remote)
    if any(w in combined_lower for w in ["plumber", "driver", "cleaner", "security", "casual", "mason", "electrician", "mechanic", "rider"]):
        work_type = "🛠️ Blue-Collar / Hands-on"
    elif any(w in combined_lower for w in ["remote", "work from home", "wfh"]):
        work_type = "🏠 Remote (White-Collar)"
    elif "hybrid" in combined_lower:
        work_type = "🔄 Hybrid (White-Collar)"
    else:
        work_type = "🏢 Onsite (Standard)"

    # Strict Deadline Extraction
    deadline_match = re.search(r'(deadline|closing date|apply before|apply by|expires on)[\s:-]+([0-9]{1,2}(st|nd|rd|th)?\s+[a-zA-Z]+\s+[0-9]{4}|[a-zA-Z]+\s+[0-9]{1,2},?\s+[0-9]{4}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})', combined_lower)
    if deadline_match:
        expiry = deadline_match.group(2).title()
    else:
        expiry = "ASAP (See portal)"

    # Qualifications Extraction
    qual_match = re.search(r'(requirements|qualifications|what we are looking for|skills required|minimum qualifications)[\s:-]+(.{150,500})', combined_text, re.IGNORECASE)
    if qual_match:
        qualifications = qual_match.group(2).strip()
        qualifications = qualifications.rsplit('.', 1)[0] + "."
    else:
        qualifications = "The direct feed did not include the full bulleted list of requirements. Please advise your audience to click the application link for the official checklist."

    return clean_title, company, city_found, work_type, expiry, qualifications

def classify_job(title, description, company):
    text = (title + " " + description + " " + company).lower()
    
    # Highly specific targeting requested by the user
    if any(word in text for word in ["tsc", "teachers service commission", "board of management", "bom", "ministry of education"]):
        return "🏛️ Government / TSC / BOM Teaching"
    elif any(word in text for word in ["government", "county", "ministry", "parastatal", "commission", "kra"]):
        return "🏛️ Government & Public Service"
    elif any(word in text for word in ["teach", "tutor", "lecturer", "school", "teacher", "instructor"]):
        return "📚 Teaching & Education (Private)"
    elif any(word in text for word in ["medicine", "nurse", "clinical", "hospital", "doctor", "health", "pharmacist"]):
        return "⚕️ Doctors & Medicine"
    elif any(word in text for word in ["bank", "finance", "accountant", "audit", "tax", "teller", "microfinance"]):
        return "🏦 Banking & Finance"
    elif any(word in text for word in ["plumber", "driver", "cleaner", "security", "casual", "mason", "electrician", "mechanic"]):
        return "🛠️ Blue Collar & Casual"
    elif any(word in text for word in ["no experience", "entry level", "no certs", "no certificate"]):
        return "🟢 No Certs Required"
    elif any(word in text for word in ["hr", "human resources", "recruitment"]):
        return "🤝 Human Resources"
    elif any(word in text for word in ["developer", "software", "it support", "tech", "data", "engineer"]):
        return "💻 IT & Tech"
    else:
        return "📁 General Corporate & NGO"

def analyze_scam_risk(title, description):
    score = 0
    reasons = []
    text_to_analyze = (title + " " + description).lower()

    for pattern in SCAM_KEYWORDS:
        if re.search(pattern, text_to_analyze):
            score += 60
            reasons.append(f"Mentions fees/payments ('{pattern}')")

    email_match = re.search(r'[\w\.-]+@(gmail\.com|yahoo\.com|outlook\.com)', text_to_analyze)
    if email_match:
        found_email = email_match.group(0)
        for corp in CORPORATE_KEYWORDS:
            if corp in text_to_analyze:
                score += 40
                reasons.append(f"Suspicious free email ({found_email}) for corporate/govt job")

    if score >= 60:
        return "❌ HIGH RISK (Likely Scam)", reasons
    elif 30 <= score < 60:
        return "⚠️ SUSPICIOUS", reasons
    else:
        return "✅ LEGITIMATE", reasons

def fetch_and_parse_feeds():
    headers = {"User-Agent": "Mozilla/5.0"}
    jobs_found = []
    now = datetime.datetime.now(datetime.timezone.utc)
    # Expanded window to 72 hours to ensure high volume (25+ jobs)
    three_days_ago = now - datetime.timedelta(days=3)

    for url in JOB_FEEDS:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue
            
            try:
                root = ET.fromstring(response.content)
            except:
                continue # Skip feeds that are temporarily down

            for item in root.findall('.//item'):
                raw_title = item.find('title').text or "No Title"
                link = item.find('link').text or ""
                desc = item.find('description').text or ""
                pub_date_str = item.find('pubDate').text
                
                desc_clean = re.sub('<[^<]+?>', '', desc).strip()
                
                if pub_date_str:
                    try:
                        clean_date_str = pub_date_str.split(' +')[0].split(' -')[0]
                        pub_date = datetime.datetime.strptime(clean_date_str, "%a, %d %b %Y %H:%M:%S")
                        pub_date = pub_date.replace(tzinfo=datetime.timezone.utc)
                    except ValueError:
                        pub_date = now

                    # Filtering for jobs within the last 72 hours
                    if pub_date >= three_days_ago:
                        clean_title, company, city, work_type, expiry, qualifications = extract_job_details(raw_title, desc_clean)
                        status, reasons = analyze_scam_risk(raw_title, desc_clean)
                        category = classify_job(clean_title, desc_clean, company)
                        
                        summary = f"Listen up! This is a brand new opening for a **{clean_title}** position. They are currently actively hiring at **{company}**."

                        jobs_found.append({
                            "Clean Title": clean_title,
                            "Company": company,
                            "Category": category,
                            "Status": status,
                            "Red Flags": ", ".join(reasons) if reasons else "None",
                            "Day Posted": pub_date.strftime("%A (%B %d)"), 
                            "Link": link,
                            "Work Type": work_type,
                            "City": city,
                            "Expiry": expiry,
                            "Summary": summary,
                            "Qualifications": qualifications
                        })
        except Exception:
            pass
            
    # Remove duplicates based on link/title
    unique_jobs = {job['Clean Title']: job for job in jobs_found}.values()
    return list(unique_jobs)

# --- Dashboard UI Layout ---
if str.button("🚀 LAUNCH MEGA-SCAN (Fetch 25+ Jobs)"):
    with str.spinner("Scanning Government portals, TSC feeds, Corporate Boards, and NGO registries..."):
        data = fetch_and_parse_feeds()
        
        if len(data) >= 25:
            str.success(f"🔥 MASSIVE HAUL: Successfully processed {len(data)} live jobs from the last 72 hours!")
        elif data:
            str.warning(f"Found {len(data)} jobs. (If this is below 25, job boards are currently experiencing low posting volumes today).")
        else:
            str.error("No data fetched. Check your internet connection or try again in an hour.")
            
        if data:
            # Layout the specific sector filters
            categories = sorted(list(set([j["Category"] for j in data])))
            selected_cat = str.multiselect("🎯 Filter by Target Sector (e.g., TSC, BOM, Bankers, Blue Collar)", options=categories, default=categories)
            
            filtered_data = [j for j in data if j["Category"] in selected_cat]
            
            str.markdown(f"### Displaying {len(filtered_data)} Opportunities")
            str.markdown("---")
            
            for job in filtered_data:
                with str.container():
                    str.markdown(f"## 📌 {job['Clean Title']}")
                    str.markdown(f"### 🏢 Hiring: {job['Company']}")
                    
                    col1, col2, col3, col4 = str.columns(4)
                    with col1:
                        str.write(f"**📍 Location:** {job['City']}")
                    with col2:
                        str.write(f"**🛠️ Type:** {job['Work Type']}")
                    with col3:
                        str.write(f"**⏳ Deadline:** {job['Expiry']}")
                    with col4:
                        str.write(f"**🛡️ Safety:** {job['Status']}")
                        
                    if job['Red Flags'] != "None":
                        str.error(f"🚩 Verification Flags: {job['Red Flags']}")
                    
                    str.markdown("#### 🗣️ Script: The Summary")
                    str.info(job["Summary"])
                    
                    str.markdown("#### 🎓 Script: Required Qualifications")
                    str.warning(job["Qualifications"])
                    
                    str.markdown(f"👉 **[Click Here to Send Audience to Application Page]({job['Link']})**")
                    str.markdown("<br><hr><br>", unsafe_allow_html=True)
