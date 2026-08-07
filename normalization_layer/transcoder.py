import json
import os
import re
import db_manager

def clean_text(text):
    if not text:
        return ""
    # Remove HTML tags if any
    clean = re.sub(r'<[^>]+>', '', text)
    # Normalize whitespaces
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def parse_study(study_data):
    protocol = study_data.get("protocolSection", {})
    
    # Identification
    ident_mod = protocol.get("identificationModule", {})
    nct_id = ident_mod.get("nctId", "UNKNOWN")
    title = clean_text(ident_mod.get("briefTitle", ""))
    
    # Conditions
    cond_mod = protocol.get("conditionsModule", {})
    conditions = [clean_text(c) for c in cond_mod.get("conditions", [])]
    
    # Phase
    design_mod = protocol.get("designModule", {})
    phases = design_mod.get("phases", [])
    # Se la fase non c'è, magari è uno studio osservazionale
    study_type = design_mod.get("studyType", "")
    if not phases and study_type:
        phases = [study_type]
        
    # Interventions
    interv_mod = protocol.get("armsInterventionsModule", {})
    interventions_raw = interv_mod.get("interventions", [])
    interventions = [clean_text(i.get("name", "")) for i in interventions_raw if i.get("name")]
    
    # Status, Dates, Results, Why Stopped
    status_mod = protocol.get("statusModule", {})
    overall_status = status_mod.get("overallStatus", "UNKNOWN")
    why_stopped = clean_text(status_mod.get("whyStopped", ""))
    start_date = status_mod.get("startDateStruct", {}).get("date", "")
    completion_date = status_mod.get("primaryCompletionDateStruct", {}).get("date", "")
    has_results = study_data.get("hasResults", False)

    # Locations / Countries
    contacts_mod = protocol.get("contactsLocationsModule", {})
    locations = contacts_mod.get("locations", [])
    countries = list(set([loc.get("country", "") for loc in locations if loc.get("country")]))
    countries_str = json.dumps(countries) if countries else ""

    return {
        "study_id": nct_id,
        "title": title,
        "conditions": conditions,
        "phases": phases,
        "interventions": interventions,
        "source": "ClinicalTrials",
        "status": overall_status,
        "start_date": start_date,
        "completion_date": completion_date,
        "has_results": has_results,
        "why_stopped": why_stopped,
        "countries": countries_str
    }

def parse_pubmed_article(article_data):
    citation = article_data.get("MedlineCitation", {})
    
    # PMID
    pmid_obj = citation.get("PMID", "")
    nct_id = f"PMID:{pmid_obj.get('_', pmid_obj) if isinstance(pmid_obj, dict) else pmid_obj}"
    
    # Title
    article_info = citation.get("Article", {})
    raw_title = article_info.get("ArticleTitle", "")
    if isinstance(raw_title, dict):
        raw_title = raw_title.get("_", str(raw_title))
    title = clean_text(str(raw_title))
        
    # Conditions (MeshTerms)
    conditions = []
    mesh_list = citation.get("MeshHeadingList", {}).get("MeshHeading", [])
    if isinstance(mesh_list, dict):
        mesh_list = [mesh_list] # In case there's only one
    for mesh in mesh_list:
        desc = mesh.get("DescriptorName", "")
        if isinstance(desc, dict):
            desc = desc.get("_", "")
        conditions.append(clean_text(desc))
        
    # Phases (PublicationType)
    phases = []
    pub_types = article_info.get("PublicationTypeList", {}).get("PublicationType", [])
    if isinstance(pub_types, dict):
        pub_types = [pub_types]
    for pt in pub_types:
        name = pt.get("_", pt) if isinstance(pt, dict) else pt
        phases.append(clean_text(name))
        
    # Interventions (Keywords)
    interventions = []
    kw_list_obj = citation.get("KeywordList", {})
    if isinstance(kw_list_obj, list) and kw_list_obj:
        kw_list_obj = kw_list_obj[0]
    keywords = kw_list_obj.get("Keyword", []) if isinstance(kw_list_obj, dict) else []
    if isinstance(keywords, dict) or isinstance(keywords, str):
        keywords = [keywords]
    for kw in keywords:
        val = kw.get("_", kw) if isinstance(kw, dict) else kw
        interventions.append(clean_text(val))
        
    # PubMed literature is considered completed research
    overall_status = "Completed"
    why_stopped = ""
    has_results = True
    
    # Extract Publication Date for start/completion dates
    pub_date = article_info.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
    year = pub_date.get("Year", "")
    month = pub_date.get("Month", "")
    start_date = f"{year} {month}".strip()
    completion_date = start_date

    return {
        "study_id": nct_id,
        "title": title,
        "conditions": conditions,
        "phases": phases,
        "interventions": interventions,
        "source": "PubMed",
        "status": overall_status,
        "start_date": start_date,
        "completion_date": completion_date,
        "has_results": has_results,
        "why_stopped": why_stopped,
        "countries": '["Global / Literature"]'
    }

def main():
    db_manager.init_db()
    
    raw_dir = os.path.join("..", "staging_area", "raw")
    clean_dir = os.path.join("..", "staging_area", "normalized")
    
    # Process all JSON files in raw_dir
    raw_files = [f for f in os.listdir(raw_dir) if f.endswith(".json")]
    if not raw_files:
        print("No raw JSON files found in staging_area/raw.")
        return
        
    for file_name in raw_files:
        raw_file_path = os.path.join(raw_dir, file_name)
        clean_file_name = f"clean_{file_name}"
        clean_file_path = os.path.join(clean_dir, clean_file_name)
        
        print(f"Reading raw data from {raw_file_path}...")
        try:
            with open(raw_file_path, "r", encoding="utf-8") as f:
                raw_payload = json.load(f)
        except Exception as e:
            print(f"Error reading {raw_file_path}: {e}")
            continue

        is_pubmed = "pubmed_batch" in file_name
        
        studies_list = raw_payload.get("articles", []) if is_pubmed else raw_payload.get("studies", [])
        
        if not studies_list:
            print(f"No records found in {file_name}.")
            continue
            
        print(f"Found {len(studies_list)} record/s in {file_name}. Parsing and cleaning...")
        
        normalized_records = []
        for item in studies_list:
            if is_pubmed:
                parsed_record = parse_pubmed_article(item)
            else:
                parsed_record = parse_study(item)
            normalized_records.append(parsed_record)
            
        final_output = {
            "status": "normalized",
            "source_file": file_name,
            "record_count": len(normalized_records),
            "data": normalized_records
        }
        
        print(f"Saving normalized data to {clean_file_path}...")
        with open(clean_file_path, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
            
        print(f"Loading {len(normalized_records)} records into SQLite...")
        db_manager.insert_records(normalized_records)
            
    print("Transcoding completed successfully for all files!")

if __name__ == "__main__":
    main()
