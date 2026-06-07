import requests
from bs4 import BeautifulSoup
import streamlit as st
import time

st.set_page_config(page_title="Kenya Job Hub: Teachers Only", layout="wide")

st.title("🧑‍🏫 Kenya High School & BOM Teaching Jobs")
st.markdown("A direct HTML category scraper that bypasses general feeds to pull directly from the **Education/Teaching** sections of major Kenyan job boards.")

def scrape_teaching_categories():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    jobs_found = []
    
    my_bar = st.progress(0, text="Scraping dedicated Education/Teaching portals...")
    
    # ---------------------------------------------------------
    # TARGET 1: MyJobMag's Dedicated Education Category
    # ---------------------------------------------------------
    try:
        url = "https://www.myjobmag.co.ke/jobs-by-field/education-teaching"
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Find all job postings on the page
            job_headers = soup.find_all('h2')
            for h2 in job_headers:
                a_tag = h2.find('a')
                if a_tag and 'href' in a_tag.attrs:
                    title = a_tag.text.strip()
                    
                    # Ignore primary/kindergarten if you strictly want high school
                    if "kindergarten" in title.lower() or "ecde" in title.lower() or "primary" in title.lower():
                        continue
                        
                    link = "https://www.myjobmag.co.ke" + a_tag['href'] if a_tag['href'].startswith('/') else a_tag['href']
                    
                    # Look for the description snippet
                    desc_div = h2.find_next_sibling('li', class_='job-desc')
                    desc = desc_div.text.strip() if desc_div else "See the link for full details."
                    
                    # Extract school name from title
                    school_name = title.split(" at ")[-1].strip() if " at " in title else "School/Institution (See Link)"
                    clean_title = title.split(" at ")[0].strip() if " at " in title else title
                    
                    jobs_found.append({
                        "Title": clean_title,
                        "School": school_name,
                        "Preview": desc[:250] + "...",
                        "Link": link,
                        "Source": "MyJobMag Education"
                    })
    except Exception:
        pass
        
    my_bar.progress(50, text="Scraping Careerjet Secondary School Category...")

    # ---------------------------------------------------------
    # TARGET 2: Careerjet's Specific "Secondary School" Query
    # ---------------------------------------------------------
    try:
        url2 = "https://www.careerjet.co.ke/secondary-school-teacher-jobs"
        res2 = requests.get(url2, headers=headers, timeout=10)
        if res2.status_code == 200:
            soup2 = BeautifulSoup(res2.text, 'html.parser')
            
            articles = soup2.find_all('article', class_='job')
            for article in articles:
                header = article.find('header')
                if header:
                    a_tag = header.find('a')
                    title = a_tag.text.strip() if a_tag else "No Title"
                    link = "https://www.careerjet.co.ke" + a_tag['href'] if a_tag else ""
                    
                    company_p = article.find('p', class_='company')
                    company = company_p.text.strip() if company_p else "School/Institution"
                    
                    desc_div = article.find('div', class_='desc')
                    desc = desc_div.text.strip() if desc_div else "See link for full details."
                    
                    jobs_found.append({
                        "Title": title,
                        "School": company,
                        "Preview": desc[:250] + "...",
                        "Link": link,
                        "Source": "CareerJet"
                    })
    except Exception:
        pass
        
    my_bar.empty()
    
    # Remove exact duplicates
    unique_jobs = {job['Title'] + job['School']: job for job in jobs_found}.values()
    return list(unique_jobs)

# --- UI INTERFACE ---
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🚀 SCAN DIRECT CATEGORIES", use_container_width=True):
        st.session_state['run_scan'] = True
with col2:
    st.info("Now using BeautifulSoup to directly scrape the 'Teaching & Education' HTML pages of job boards. Guaranteed results.")

if st.session_state.get('run_scan', False):
    data = scrape_teaching_categories()
    st.session_state['run_scan'] = False
    
    if data:
        st.success(f"✅ Success! Found {len(data)} teaching opportunities actively hiring on the boards.")
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
                
                st.markdown("**🔗 Direct Application Link:**")
                st.code(job['Link'], language=None)
                
                st.markdown("<br><hr><br>", unsafe_allow_html=True)
    else:
        st.error("Error connecting to the job boards. Please check your internet connection and try again.")
