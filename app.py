import datetime
import xml.etree.ElementTree as ET
import re
import requests
import streamlit as str  # Using standard clean wrapper

# Configure the page
str.set_page_config(page_title="Kenya Job Hub & Verification Screener", layout="wide")

str.title("🇰🇪 Kenya Job Hub & Scam Detector")
str.markdown("This live system extracts newly posted jobs in Kenya (under 48 hours old) across aggregator networks, extracts critical application details, and screens them for employment fraud.")

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

def classify_job(title, description):
    text = (title + " " + description).lower()
    if any(word in text for word in ["no experience", "entry level", "no certs", "no certificate", "cleaner", "messenger", "casual"]):
        return "🟢 No Certs Required / Entry Level"
    elif any(word in text for word in ["teach", "tutor", "lecturer", "school", "teacher", "education"]):
        return "📚 Teaching & Education"
    elif any(word in text for word in ["medicine", "nurse", "clinical", "hospital", "doctor", "health", "medical"]):
        return "⚕️ Medicine & Healthcare"
    elif any(word in text for word in ["hr", "human resources", "recruitment"]):
        return "🤝 Human Resources (HR)"
    elif any(word in text for word in ["developer", "software", "it support", "tech", "data", "engineer"]):
        return "💻 IT, Tech & Engineering"
    elif any(word in text for word in ["finance", "accountant", "audit", "tax", "cpa"]):
        return "📊 Finance & Accounting"
    elif any(word in text for word in ["sales", "marketing", "digital marketing"]):
        return "📈 Sales & Marketing"
    else:
        return "📁 General / Other"

def extract_job_details(title, description):
    """Intelligently parses unstructured job text for required fields."""
    combined_text = (title + " " + description).lower()
    
    # 1. Onsite vs Remote vs Hybrid
    if any(w in combined_text for w in ["remote", "work from home", "wfh", "virtual"]):
        work_type = "🏠 Remote"
    elif "hybrid" in combined_text:
        work_type = "🔄 Hybrid"
    else:
        work_type = "🏢 Onsite"
        
    # 2. City or Town Detection
    cities = ["nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika", "malindi", "kitale", "garissa", "kakamega", "nyeri", "machakos", "naivasha", "meru", "kiambu", "kericho", "kisii"]
    city_found = "Not explicit (Likely Nairobi)"
    for city in cities:
        if city in combined_text:
            city_found = city.title()
            break

    # 3. Expiry / Deadline Tracking
    deadline_match = re.search(r'(deadline|closing date|apply before|expires on)[:\s]+([\w\s,.\d/-]+)', combined_text)
    expiry = "See link for deadline details"
    if deadline_match:
        extracted = deadline_match.group(2).strip()
        # Clean up snippet boundaries
        words = extracted.split()[:4]
        if len(words) > 0:
            expiry = " ".join(words).title().strip(",.")

    # 4. Qualifications Extraction
    # Look for common requirement header markers
    qual_regex = r'(requirements|qualifications|key skills|what you need)[:\s]+([^.]+)'
    qual_match = re.search(qual_regex, combined_text)
    if qual_match and len(qual_match.group(2).strip()) > 10:
        qualifications = qual_match.group(2).strip().capitalize() + "."
    else:
        qualifications = "Degree/Diploma or relevant experience in the respective field. See direct link for full checklist."

    return work_type, city_found, expiry, qualifications

def analyze_scam_risk(title, description):
    score = 0
    reasons = []
    text_to_analyze = (title + " " + description).lower()

    for pattern in SCAM_KEYWORDS:
        if re.search(pattern, text_to_analyze):
            score += 60
            reasons.append(f"Asks for money/fees ('{pattern}')")

    email_match = re.search(r'[\w\.-]+@(gmail\.com|yahoo\.com|outlook\.com)', text_to_analyze)
    if email_match:
        found_email = email_match.group(0)
        for corp in CORPORATE_KEYWORDS:
            if corp in text_to_analyze:
                score += 40
                reasons.append(f"Claims major entity but uses free email ({found_email})")

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
                title = item.find('title').text or "No Title"
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
                        status, reasons = analyze_scam_risk(title, desc_clean)
                        category = classify_job(title, desc_clean)
                        work_type, city, expiry, qualifications = extract_job_details(title, desc_clean)
                        
                        # Generate shorter preview description
                        preview_desc = desc_clean[:280] + "..." if len(desc_clean) > 280 else desc_clean

                        jobs_found.append({
                            "Title": title,
                            "Category": category,
                            "Status": status,
                            "Red Flags": ", ".join(reasons) if reasons else "None",
                            "Date Posted": pub_date.strftime("%Y-%m-%d %H:%M"),
                            "Link": link,
                            "Work Type": work_type,
                            "City": city,
                            "Expiry": expiry,
                            "Qualifications": qualifications,
                            "Description": preview_desc
                        })
        except Exception:
            pass
    return jobs_found

# --- UI Interface Layout ---
if str.button("🔄 Scan the Web Now"):
    with str.spinner("Connecting to live aggregator feeds..."):
        data = fetch_and_parse_feeds()
        if data:
            str.success(f"Successfully processed {len(data)} live jobs from the last 48 hours!")
            
            # Setup dynamic data filter pickers
            categories = list(set([j["Category"] for j in data]))
            selected_cat = str.multiselect("Filter by Category", options=categories, default=categories)
            
            statuses = list(set([j["Status"] for j in data]))
            selected_status = str.multiselect("Filter by Safety Status", options=statuses, default=statuses)
            
            filtered_data = [j for j in data if j["Category"] in selected_cat and j["Status"] in selected_status]
            
            str.markdown("### 🎯 Filtered Job Results")
            
            # Render cleanly structured data layouts
            for job in filtered_data:
                with str.container():
                    str.subheader(job["Title"])
                    
                    # Columns for structural meta data
                    col1, col2, col3, col4 = str.columns(4)
                    with col1:
                        str.write(f"**📍 City/Town:** {job['City']}")
                    with col2:
                        str.write(f"**💼 Setup:** {job['Work Type']}")
                    with col3:
                        str.write(f"**📅 Posted:** {job['Date Posted']}")
                    with col4:
                        str.write(f"**⏳ Deadline:** {job['Expiry']}")
                        
                    str.write(f"**🛡️ Security Status:** {job['Status']}")
                    if job['Red Flags'] != "None":
                        str.error(f"🚩 Verification Flags: {job['Red Flags']}")
                    
                    # Core Details Expander blocks
                    with str.expander("📄 View Job Description & Requirements Summary"):
                        str.write("**Job Summary:**")
                        str.write(job["Description"])
                        str.write("**Key Qualifications Found:**")
                        str.write(job["Qualifications"])
                    
                    # Direct Link Layout
                    str.markdown(f"👉 **[Click Here to Open Direct Application Page]({job['Link']})**")
                    str.markdown("---")
        else:
            str.info("No new jobs found in the last 48 hours. Try running the scan again later!")
