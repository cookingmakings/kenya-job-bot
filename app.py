import datetime
import xml.etree.ElementTree as ET
import re
import requests
import streamlit as str  # Standard alias is st, using str carefully here

# Configure the page
str.set_page_config(page_title="Kenya Job Screener & Scam Detector", layout="wide")

str.title("🇰🇪 Kenya Job Screener & Scam Detector")
str.markdown("This app scans job aggregator networks for openings posted in the last 48 hours, categorizes them, and filters out high-risk scams.")

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
                        
                        jobs_found.append({
                            "Title": title,
                            "Category": category,
                            "Status": status,
                            "Red Flags": ", ".join(reasons) if reasons else "None",
                            "Date Posted": pub_date.strftime("%Y-%m-%d %H:%M"),
                            "Link": link
                        })
        except Exception as e:
            pass
    return jobs_found

# Streamlit Interface Controls
if str.button("🔄 Scan the Web Now"):
    with str.spinner("Fetching data from online networks..."):
        data = fetch_and_parse_feeds()
        if data:
            str.success(f"Successfully processed {len(data)} live jobs from the last 48 hours!")
            
            # Sidebar layout filters
            categories = list(set([j["Category"] for j in data]))
            selected_cat = str.multiselect("Filter by Category", options=categories, default=categories)
            
            statuses = list(set([j["Status"] for j in data]))
            selected_status = str.multiselect("Filter by Safety Status", options=statuses, default=statuses)
            
            # Filter rows
            filtered_data = [j for j in data if j["Category"] in selected_cat and j["Status"] in selected_status]
            
            # Display results
            for job in filtered_data:
                with str.container():
                    str.subheader(job["Title"])
                    str.write(f"**Category:** {job['Category']} | **Posted:** {job['Date Posted']}")
                    str.write(f"**Verification Status:** {job['Status']}")
                    if job['Red Flags'] != "None":
                        str.warning(f"Warning Details: {job['Red Flags']}")
                    str.markdown(f"[Click Here to View Application Link]({job['Link']})")
                    str.markdown("---")
        else:
            str.info("No jobs found in the last 48 hours. Try refreshing later.")