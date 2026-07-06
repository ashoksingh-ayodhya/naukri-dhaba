#!/usr/bin/env python3
import os
import re
import glob

CONTENT_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content")

CLEAN_BOARDS = {
    "state bank of india": "State Bank of India (SBI)",
    "sbi": "State Bank of India (SBI)",
    "reserve bank of india": "Reserve Bank of India (RBI)",
    "rbi": "Reserve Bank of India (RBI)",
    "union public service commission": "Union Public Service Commission (UPSC)",
    "upsc": "Union Public Service Commission (UPSC)",
    "staff selection commission": "Staff Selection Commission (SSC)",
    "ssc": "Staff Selection Commission (SSC)",
    "railway recruitment board": "Railway Recruitment Board (RRB)",
    "rrb": "Railway Recruitment Board (RRB)",
    "institute of banking personnel selection": "Institute of Banking Personnel Selection (IBPS)",
    "ibps": "Institute of Banking Personnel Selection (IBPS)",
    "uttar pradesh subordinate services selection commission": "Uttar Pradesh Subordinate Services Selection Commission (UPSSSC)",
    "upsssc": "Uttar Pradesh Subordinate Services Selection Commission (UPSSSC)",
    "delhi subordinate services selection board": "Delhi Subordinate Services Selection Board (DSSSB)",
    "dsssb": "Delhi Subordinate Services Selection Board (DSSSB)",
    "central board of secondary education": "Central Board of Secondary Education (CBSE)",
    "cbse": "Central Board of Secondary Education (CBSE)",
    "indian army": "Indian Army",
    "indian navy": "Indian Navy",
    "indian air force": "Indian Air Force",
    "iaf": "Indian Air Force",
    "border security force": "Border Security Force (BSF)",
    "bsf": "Border Security Force (BSF)",
    "central reserve police force": "Central Reserve Police Force (CRPF)",
    "crpf": "Central Reserve Police Force (CRPF)",
    "central industrial security force": "Central Industrial Security Force (CISF)",
    "cisf": "Central Industrial Security Force (CISF)",
    "indo tibetan border police": "Indo-Tibetan Border Police (ITBP)",
    "itbp": "Indo-Tibetan Border Police (ITBP)",
    "sashastra seema bal": "Sashastra Seema Bal (SSB)",
    "ssb": "Sashastra Seema Bal (SSB)",
    "life insurance corporation": "Life Insurance Corporation of India (LIC)",
    "lic": "Life Insurance Corporation of India (LIC)",
    "drdo": "Defence Research and Development Organisation (DRDO)",
    "isro": "Indian Space Research Organisation (ISRO)",
    "aiims": "All India Institute of Medical Sciences (AIIMS)",
    "national testing agency": "National Testing Agency (NTA)",
    "nta": "National Testing Agency (NTA)",
    "bihar public service commission": "Bihar Public Service Commission (BPSC)",
    "bpsc": "Bihar Public Service Commission (BPSC)",
    "uttar pradesh public service commission": "Uttar Pradesh Public Service Commission (UPPSC)",
    "uppsc": "Uttar Pradesh Public Service Commission (UPPSC)",
    "madhya pradesh public service commission": "Madhya Pradesh Public Service Commission (MPPSC)",
    "mppsc": "Madhya Pradesh Public Service Commission (MPPSC)",
    "rajasthan public service commission": "Rajasthan Public Service Commission (RPSC)",
    "rpsc": "Rajasthan Public Service Commission (RPSC)",
    "haryana staff selection commission": "Haryana Staff Selection Commission (HSSC)",
    "hssc": "Haryana Staff Selection Commission (HSSC)",
    "jharkhand staff selection commission": "Jharkhand Staff Selection Commission (JSSC)",
    "jssc": "Jharkhand Staff Selection Commission (JSSC)",
    "punjab public service commission": "Punjab Public Service Commission (PPSC)",
    "ppsc": "Punjab Public Service Commission (PPSC)",
    "kendriya vidyalaya sangathan": "Kendriya Vidyalaya Sangathan (KVS)",
    "kvs": "Kendriya Vidyalaya Sangathan (KVS)",
    "navodaya vidyalaya samiti": "Navodaya Vidyalaya Samiti (NVS)",
    "nvs": "Navodaya Vidyalaya Samiti (NVS)",
    "india post": "India Post",
    "gds": "India Post GDS",
    "bank of baroda": "Bank of Baroda (BOB)",
    "bob": "Bank of Baroda (BOB)",
    "idbi": "IDBI Bank",
    "nabard": "National Bank for Agriculture and Rural Development (NABARD)",
    "supreme court": "Supreme Court of India",
    "sci": "Supreme Court of India",
    "patna high court": "Patna High Court",
    "btscc": "Bihar Technical Service Commission (BTSC)",
    "btsc": "Bihar Technical Service Commission (BTSC)",
    "cbi": "Central Bureau of Investigation (CBI)",
    "hssc": "Haryana Staff Selection Commission (HSSC)",
    "hpsc": "Haryana Public Service Commission (HPSC)",
    "gpsc": "Gujarat Public Service Commission (GPSC)",
    "mpsc": "Maharashtra Public Service Commission (MPSC)",
}

GENERIC_WORDS = {
    "online", "form", "vacancy", "recruitment", "jobs", "apply", "eligibility", "criteria", "exam", "result",
    "admit", "card", "hall", "ticket", "answer", "key", "syllabus", "2026", "2025", "2024", "2023", "2022",
    "post", "posts", "vacancies", "notification", "out", "advertisement", "details", "for", "and", "the", "of",
    "to", "with", "various", "latest", "alert", "hiring", "mega", "new", "released", "updates"
}

def clean_org_name(title, current_org, dept):
    title_lower = title.lower()
    
    # Check if we can map title to a known clean board
    for key, name in CLEAN_BOARDS.items():
        if key in title_lower:
            return name
            
    # Check current organization name for pollution
    current_lower = current_org.lower() if current_org else ""
    is_polluted = (
        not current_org or
        current_lower == "all board exams" or
        len(current_org) > 80 or
        any(w in current_lower for w in ["result", "admit", "answer", "syllabus", "online form", "interview", "letter", "marks", "cutoff", "typing", "steno", "exam", "has released", "candidates", "recruitment of"])
    )
    
    if not is_polluted:
        return current_org
        
    # Check if department is non-generic and can be matched
    dept_lower = dept.lower() if dept else ""
    if dept_lower and dept_lower not in ["government", "govt", "bank", "police", "defence"]:
        for key, name in CLEAN_BOARDS.items():
            if key == dept_lower:
                return name
        return dept.upper()

    # Extract first few non-generic words from title
    words = title.split()
    clean_words = []
    for w in words:
        w_clean = re.sub(r'[^\w]', '', w).lower()
        if w_clean and w_clean not in GENERIC_WORDS:
            clean_words.append(w)
        if len(clean_words) >= 3:
            break
            
    if clean_words:
        extracted = " ".join(clean_words)
        # Ensure it starts with uppercase
        return extracted
        
    return "Government of India"

def infer_qualification(title, body):
    combined = (title + " " + body).lower()
    
    if "apprentice" in combined:
        return "Bachelor Degree in any stream / ITI / Diploma"
    elif "graduate" in combined or "degree" in combined or "b.sc" in combined or "b.a" in combined or "b.com" in combined or "btech" in combined or "b.tech" in combined or "b.e" in combined or "bachelor" in combined:
        return "Bachelor Degree in any stream"
    elif "mts" in combined or "multi tasking" in combined or "peon" in combined or "helper" in combined:
        return "Class 10th Pass / Matriculation"
    elif "constable" in combined or "gd" in combined or "12th" in combined or "intermediate" in combined or "class 12" in combined:
        return "Class 12th Pass / Intermediate"
    elif "engineer" in combined or "junior engineer" in combined or "je" in combined:
        return "B.E. / B.Tech / Diploma in Engineering"
    elif "diploma" in combined:
        return "Diploma in relevant engineering/discipline"
    elif "iti" in combined:
        return "ITI Certificate in relevant trade"
    elif "driver" in combined:
        return "Class 10th Pass with Valid Driving License"
    elif "sub inspector" in combined or "si " in combined or "officer" in combined:
        return "Bachelor Degree in any stream"
    elif "post graduate" in combined or "master" in combined or "m.sc" in combined or "m.a" in combined:
        return "Master Degree in relevant subject"
    
    return "Bachelor Degree / Class 12th / Class 10th (Check Notification)"

def run():
    files = glob.glob(os.path.join(CONTENT_ROOT, "jobs", "**", "*.mdx"), recursive=True)
    print(f"Scanning {len(files)} jobs files...")
    
    cleaned_count = 0
    qual_added_count = 0
    
    for fpath in files:
        try:
            content = open(fpath, encoding="utf-8").read()
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue
                
            front = parts[1]
            body = parts[2]
            
            # Extract current values
            m_title = re.search(r'^title:\s*"?(.*?)"?\s*$', front, re.M)
            title = m_title.group(1).strip().strip('"') if m_title else ""
            
            m_org = re.search(r'^organization:\s*"?(.*?)"?\s*$', front, re.M)
            org = m_org.group(1).strip().strip('"') if m_org else ""
            
            m_dept = re.search(r'^dept:\s*"?(.*?)"?\s*$', front, re.M)
            dept = m_dept.group(1).strip().strip('"') if m_dept else ""
            
            m_qual = re.search(r'^qualification:\s*"?(.*?)"?\s*$', front, re.M)
            qual = m_qual.group(1).strip().strip('"') if m_qual else ""
            
            # Clean organization
            new_org = clean_org_name(title, org, dept)
            
            # Enrich qualification
            new_qual = qual
            qual_changed = False
            if not qual or qual == "Check Notification":
                new_qual = infer_qualification(title, body)
                qual_changed = True
                
            changed = False
            new_front = front
            
            # Update frontmatter string
            if new_org != org:
                # Replace organization field
                escaped_org = new_org.replace('"', '\\"')
                if re.search(r'^organization:', new_front, re.M):
                    new_front = re.sub(r'^organization:.*$', f'organization: "{escaped_org}"', new_front, flags=re.M)
                else:
                    new_front = new_front.rstrip() + f'\norganization: "{escaped_org}"'
                changed = True
                cleaned_count += 1
                
            if qual_changed:
                escaped_qual = new_qual.replace('"', '\\"')
                if re.search(r'^qualification:', new_front, re.M):
                    new_front = re.sub(r'^qualification:.*$', f'qualification: "{escaped_qual}"', new_front, flags=re.M)
                else:
                    new_front = new_front.rstrip() + f'\nqualification: "{escaped_qual}"'
                changed = True
                qual_added_count += 1
                
            if changed:
                new_content = "---" + new_front.rstrip("\n") + "\n---" + body
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                    
        except Exception as e:
            print(f"Error processing {fpath}: {e}")
            
    print(f"Finished! Organization cleaned/updated in {cleaned_count} files.")
    print(f"Qualification added/inferred in {qual_added_count} files.")

if __name__ == "__main__":
    run()
