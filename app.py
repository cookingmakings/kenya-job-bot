import re
import requests
import xml.etree.ElementTree as ET
import streamlit as st

st.set_page_config(page_title="Kenya Job Hub: Teachers Only", layout="wide")

st.title("🧑‍🏫 Kenya High School & BOM Teaching Jobs")
st.markdown("A lightning-fast scanner dedicated exclusively to finding teaching opportunities in Kenyan secondary schools.")

# We use the fastest, most reliable XML feeds. No search engines to block us.
FEEDS = [
    "https://www.myjobmag.co.ke/jobs-by-date.xml",
    "https://jobwebkenya.com/feed/"
]

# The magic words for Kenyan teaching jobs
TEACHING_KEYWORDS = [
    "teacher", "teaching", "tsc", "bom", "board of management", 
    "secondary school", "high school", "tutor", "instructor", "educator",
    "mathematics", "physics", "biology", "chemistry", "kiswahili"
]

def fetch_teaching_jobs():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    jobs_found = []
    
    my_bar = st.progress(0, text="Scanning live feeds for teaching jobs...")
    
    for feed_url in FEEDS:
        try:
            res = requests.get(feed_url, headers=headers, timeout=10)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                items = root.findall('.//item')
                
                for item in items[:200]: # Scan the last 200 jobs per feed
                    title = item.find('title').text or ""
                    link = item.find('link').text or ""
                    desc = item.find('description').text or ""
                    
                    combined_text = (title + " " + desc).lower()
                    
                    # STRICT FILTER: Is it a teaching job?
                    if any(kw in combined_text for kw in TEACHING_KEYWORDS):
                        # Filter out primary/kindergarten if you strictly want high school/secondary, 
                        # but keeping it broad ensures we don't miss BOM posts.
                        if "kindergarten" in combined_text or "ecde" in combined_text:
                            continue 
                            
                        # Clean up the title and extract the school name
                        clean_title = title.split(" at ")[0].strip() if " at " in title else title
                        school_name = title.split(" at ")[1].strip() if " at " in title else "School/Institution (See link)"
                        
                        # Clean up HTML tags from the description snippet
                        desc_clean = re.sub('<[^<]+?>', '', desc).strip()
                        preview = desc_clean[:250] + "..." if len(desc_clean) > 250 else desc_clean
                        
                        jobs_found.append({
                            "Title": clean_title,
                            "School": school_name,
                            "Preview": preview,
                            "Link": link
                        })
        except Exception as e:
            pass
            
    my_bar.empty()
    
    # Remove duplicates
    unique_jobs = {job['Title'] + job['School']: job for job in jobs_found}.values()
    return list(unique_jobs)

# --- UI INTERFACE ---
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🚀 SCAN FOR TEACHING JOBS", use_container_width=True):
        st.session_state['run_scan'] = True
with col2:
    st.info("Click to instantly scan for recent BOM, TSC, and High School teacher vacancies.")

if st.session_state.get('run_scan', False):
    data = fetch_teaching_jobs()
    st.session_state['run_scan'] = False
    
    if data:
        st.success(f"✅ Found {len(data)} teaching opportunities currently hiring!")
        st.markdown("---")
        
        for job in data:
            with st.container():
                st.markdown(f"## 📌 {job['Title']}")
                st.markdown(f"### 🏫 **Hiring Institution: {job['School']}**")
                
                # Tag it if it's a BOM or TSC job for easy viewing
                if "bom" in job['Title'].lower() or "board of management" in job['Title'].lower():
                    st.info("🏫 **BOM TEACHER POSTING**")
                elif "tsc" in job['Title'].lower():
                    st.success("🏛️ **TSC POSTING**")
                
                st.markdown("#### 📄 Job Preview:")
                st.write(f"*{job['Preview']}*")
                
                st.markdown("**🔗 Application Link:**")
                st.code(job['Link'], language=None)
                
                st.markdown("<br><hr><br>", unsafe_allow_html=True)
    else:
        st.warning("No new high school teaching jobs found in the feeds right now. Try again tomorrow!")
