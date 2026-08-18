import urllib.request
import urllib.parse
import json
import os
import sys
import datetime
import gzip
import shutil

# Aggiungiamo la root al path per poter importare i moduli della normalization_layer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from normalization_layer.transcoder import parse_study
from normalization_layer.db_manager import insert_records

def download_and_update(days_back=30):
    # Decomprimiamo il DB se non è presente (utile per le GitHub Actions)
    if not os.path.exists("../clinical_data.db") and os.path.exists("../clinical_data.db.gz"):
        print("Decomprimendo il DB compresso...")
        with gzip.open("../clinical_data.db.gz", "rb") as f_in:
            with open("../clinical_data.db", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
                
    today = datetime.datetime.now()
    past = today - datetime.timedelta(days=days_back)
    date_str = past.strftime("%Y-%m-%d")
    
    print(f"Scaricando i trial aggiornati dal {date_str} ad oggi...")
    
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    # Query parameter format for ClinicalTrials V2 API
    query_str = f"AREA[LastUpdatePostDate]RANGE[{date_str},MAX]"
    params = {
        "filter.advanced": query_str,
        "pageSize": 1000
    }
    
    total_inserted = 0
    page_token = None
    
    while True:
        if page_token:
            params["pageToken"] = page_token
            
        url = base_url + "?" + urllib.parse.urlencode(params)
        print(f"Richiesta API: {url}")
        
        req = urllib.request.Request(url, headers={'User-Agent': 'MedDataCore/1.0'})
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            print(f"Errore durante la richiesta API: {e}")
            break
            
        studies = data.get("studies", [])
        if not studies:
            break
            
        print(f"Estratti {len(studies)} studi dalla pagina corrente. Analisi e salvataggio...")
        parsed_records = [parse_study(s) for s in studies]
        insert_records(parsed_records)
        total_inserted += len(parsed_records)
        
        page_token = data.get("nextPageToken")
        if not page_token:
            break
            
    print(f"Aggiornamento mensile completato. {total_inserted} studi aggiornati/inseriti.")
    
    # Ricomprimi il DB per GitHub
    print("Ricompressione del database per l'archiviazione...")
    with open("../clinical_data.db", "rb") as f_in:
        with gzip.open("../clinical_data.db.gz", "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    print("Ricompressione completata.")

if __name__ == "__main__":
    # Esegue l'aggiornamento per gli ultimi 30 giorni
    download_and_update(30)
