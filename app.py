import datetime
import xml.etree.ElementTree as ET
import re
import requests
import streamlit as str

# Configure the page for a clean presentation view
str.set_page_config(page_title="Kenya Job Hub & Presenter Dashboard", layout="wide")

str.title("🎙️ Kenya Job Hub: Presenter Dashboard")
str.markdown("This dashboard extracts, structures, and simplifies fresh Kenyan jobs so they are easy to read and present to your audience. Jobs are under 48 hours old and scanned for scams.")

# Configuration
JOB_FEEDS = [
    "https://jobwebkenya.com/feed/",
    "https://reliefweb.int/updates.rss?search=location.name:Kenya%20AND%20format.name:Job"
]

SCAM_KEYWORDS = [
    r"registration fee", r"booking fee", r"medical fee", r"processing fee",
    r"training fee", r"uniform fee", r"send money", r"mpesa", r"m-pesa",
    r"deposit", r"bribe", r"recruitment fee", r"interview fee"
]
CORPORATE_KEYWORDS = ["safaricom", "kcb", "equity", "un", "unicef", "honda", "toyota", "kenya airways", "kra", "kura", "kenha"]

# Extensive list of Kenyan towns and counties for deep scanning
KENYAN_CITIES = [
    "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika", "malindi", "kitale", 
    "garissa", "kakamega", "nyeri", "machakos", "naivasha", "meru", "kiambu", "kericho", 
    "kisii", "lamu", "lodwar", "marsabit", "isiolo", "embu", "kitui", "wajir", "mandera", 
    "busia", "bungoma", "vihiga", "homa bay", "migori", "siaya", "bomet", "narok", "kajiado", 
    "samburu", "turkana", "baringo", "nandi", "laikipia", "nyandarua", "kilifi", "kwale"
]

def extract_job_details(title, description):
    """Deeply scans the job text to pull out highly specific presenter details."""
    combined_text = (title + " " + description).replace('\n', ' ')
    combined_lower = combined_text.lower()
    
    # 1. Extract Company and Clean Title
    # Job feeds often format titles as "Job Title at Company Name"
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
        company = "See description for hiring company"

    # 2. Extract Specific City/Town
    city_found = "Kenya (Location not explicitly stated)"
    for city in KENYAN_CITIES:
        # Using word boundaries (\b) so "Meru" doesn't trigger inside "Cameron"
        if re.search(r'\b' + city + r'\b', combined_lower):
            city_found = city.title()
            break
            
    # 3. Work Setup
    if any(w in combined_lower for w in ["remote", "work from home", "wfh", "virtual"]):
        work_type = "🏠 Remote"
    elif "hybrid" in combined_lower:
        work_type = "🔄 Hybrid"
    else:
        work_type = "🏢 Onsite"

    # 4. Extract Deadline / Expiry Date
    # Scans for dates appearing near keywords like "Deadline", "Closing", "Apply by"
    deadline_match = re.search(r'(deadline|closing date|apply before|apply by|expires on)[\s:-]+([0-9]{1,2}(st|nd|rd|th)?\s+[a-zA-Z]+\s+[0-9]{4}|[a-zA-Z]+\s+[0-9]{1,2},?\s+[0-9]{4}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})', combined_lower)
    if deadline_match:
        # Extract just the date part and capitalize it nicely
        expiry = deadline_match.group(2).title()
    else:
        expiry = "ASAP (No specific deadline found in text)"

    # 5. Extract Qualifications Block
    # Look for the word 'requirements' or 'qualifications' and capture the next 300 characters
    qual_match = re.search(r'(requirements|qualifications|what we are looking for|skills required)[\s:-]+(.{100,400})', combined_text, re.IGNORECASE)
    if qual_match:
        qualifications = qual_match.group(2).strip()
        # Clean up any broken sentences at the end
        qualifications = qualifications.rsplit('.', 1)[0] + "."
    else:
        qualifications = "The specific qualifications list was not included in the feed summary. Please check the direct application link for the full breakdown."

    return clean_title, company, city_found, work_type, expiry, qualifications

def classify_job(title, description):
    text = (title + " " + description).lower()
    if any(word in text for word in ["no experience", "entry level", "no certs", "no certificate", "cleaner", "messenger", "casual"]):
        return "🟢 No Certs Required"
    elif any(word in text for word in ["teach", "tutor", "lecturer", "school", "teacher", "education"]):
        return "📚 Teaching & Education"
    elif any(word in text for word in ["medicine", "nurse", "clinical", "hospital", "doctor", "health"]):
        return "⚕️ Medicine & Healthcare"
    elif any(word in text for word in ["hr", "human resources", "recruitment"]):
        return "🤝 Human Resources"
    elif any(word in text for word in ["developer", "software", "it support", "tech", "data", "engineer"]):
        return "💻 IT & Tech"
    elif any(word in text for word in ["finance", "accountant", "audit", "tax", "bank"]):
        return "📊 Finance"
    elif any(word in text for word in ["sales", "marketing", "digital marketing", "customer service"]):
        return "📈 Sales & Marketing"
    else:
        return "📁 General / Other"

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
                reasons.append(f"Suspicious free email ({found_email}) for corporate job")

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
    two_days_ago = now - datetime.timedelta(days=2)

    for url in JOB_FEEDS:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue
            root = ET.fromstring(response.content)
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

                    if pub_date >= two_days_ago:
                        status, reasons = analyze_scam_risk(raw_title, desc_clean)
                        category = classify_job(raw_title, desc_clean)
                        
                        # Use the new deep extraction function
                        clean_title, company, city, work_type, expiry, qualifications = extract_job_details(raw_title, desc_clean)
                        
                        # Create an easy-to-read "Presenter Summary"
                        summary = f"This is an opening for a **{clean_title}** position, and they are currently being hired by **{company}**."

                        jobs_found.append({
                            "Clean Title": clean_title,
                            "Company": company,
                            "Category": category,
                            "Status": status,
                            "Red Flags": ", ".join(reasons) if reasons else "None",
                            "Day Posted": pub_date.strftime("%A (%B %d)"),  # e.g., "Tuesday (June 06)"
                            "Link": link,
                            "Work Type": work_type,
                            "City": city,
                            "Expiry": expiry,
                            "Summary": summary,
                            "Qualifications": qualifications
                        })
        except Exception:
            pass
    return jobs_found

# --- Dashboard UI Layout ---
if str.button("🔄 Scan the Web for Fresh Jobs"):
    with str.spinner("Pulling the latest applications and preparing presenter scripts..."):
        data = fetch_and_parse_feeds()
        if data:
            str.success(f"Successfully processed {len(data)} live jobs posted in the last 48 hours!")
            
            # Simple, clean filters for the presenter
            categories = list(set([j["Category"] for j in data]))
            selected_cat = str.multiselect("Filter by Job Category", options=categories, default=categories)
            
            filtered_data = [j for j in data if j["Category"] in selected_cat]
            
            str.markdown("---")
            
            # Render structured, script-like job cards
            for job in filtered_data:
                with str.container():
                    # Big, bold headers that are easy to read
                    str.markdown(f"## {job['Clean Title']}")
                    str.markdown(f"### 🏢 Hiring Company: {job['Company']}")
                    
                    # 4-Column breakdown for quick glancing
                    col1, col2, col3, col4 = str.columns(4)
                    with col1:
                        str.write(f"**📍 Location:** {job['City']}")
                    with col2:
                        str.write(f"**📅 Posted On:** {job['Day Posted']}")
                    with col3:
                        str.write(f"**⏳ Application Deadline:** {job['Expiry']}")
                    with col4:
                        str.write(f"**🛡️ Security:** {job['Status']}")
                        
                    if job['Red Flags'] != "None":
                        str.error(f"🚩 Verification Flags: {job['Red Flags']}")
                    
                    # The Presenter's Script section
                    str.markdown("#### 🗣️ Presenter Summary")
                    str.write(job["Summary"])
                    
                    str.markdown("#### 🎓 Qualifications Required")
                    # Using a blockquote styling to make it visually distinct for reading
                    str.info(job["Qualifications"])
                    
                    # Clear, direct call-to-action link
                    str.markdown(f"👉 **[Click Here for the Direct Application Link]({job['Link']})**")
                    str.markdown("---")
        else:
            str.info("No new jobs found in the last 48 hours. Try running the scan again later!")
