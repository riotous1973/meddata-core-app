import sqlite3
import os
import sys
import streamlit as st

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clinical_data.db')

try:
    from google import genai
except ImportError:
    genai = None

def get_connection():
    return sqlite3.connect(DB_PATH)

def advanced_fallback(query):
    query_lower = query.lower()
    if "zucchero" in query_lower or "diabete" in query_lower:
        return ["Diabetes Mellitus", "Hyperglycemia", "Diabetes"]
    elif "pressione" in query_lower or "ipertensione" in query_lower:
        return ["Hypertension", "High Blood Pressure"]
    elif "seno" in query_lower:
        return ["Breast Cancer", "Breast Carcinoma", "Mammary Neoplasm"]
    elif "capelli" in query_lower or "calvizie" in query_lower:
        return ["Alopecia", "Hair Loss", "Baldness"]
    elif "rene" in query_lower:
        return ["Kidney Cancer", "Renal Cell Carcinoma", "Renal Cancer"]
    elif "prostata" in query_lower:
        return ["Prostate Cancer", "Prostatic Neoplasm"]
    elif "cuore" in query_lower or "infarto" in query_lower or "cardiaco" in query_lower:
        return ["Heart Failure", "Myocardial Infarction", "Cardiac"]
    elif "tumore" in query_lower or "cancro" in query_lower:
        return ["Cancer", "Neoplasm", "Tumor", "Carcinoma"]
    else:
        return [query]

@st.cache_data(show_spinner=False)
def expand_query(natural_query, api_key=None):
    """
    Real AI Semantic Expansion Layer with Caching.
    Usa l'API di Gemini per tradurre ed espandere la patologia, con fallback locale in caso di Rate Limit.
    """
    print(f"\n🧠 [AI Semantic Layer] Contatto il vero LLM per la query: '{natural_query}'...")
    
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            pass
            
    if not genai or not api_key:
        return [f"DEBUG_INIT_FAILED: genai_loaded={bool(genai)}, api_key_found={bool(api_key)}"]

    try:
        client = genai.Client(api_key=api_key)
        
        prompt = (
            f"Sei un assistente medico per la ricerca di Trial Clinici. "
            f"L'utente ha inserito questa patologia/sintomo (spesso in italiano, colloquiale o con errori ortografici): '{natural_query}'. "
            f"Per prima cosa correggi mentalmente eventuali errori (es. 'allopecia' -> 'alopecia'). Poi traduci ed espandi questo concetto nei 3 o 4 termini scientifici/medici (MeSH terms) più usati nei database dei trial clinici. "
            f"REGOLA FERREA: I termini estratti DEVONO ESSERE TASSATIVAMENTE IN INGLESE (es. se l'utente scrive 'diabete', tu devi restituire 'Diabetes', se scrive 'emoglobina glicata' restituisci 'Glycated Hemoglobin'). "
            f"Restituisci SOLO una lista di termini in inglese separati da virgola. Non aggiungere altre parole, spiegazioni o punteggiatura."
        )
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
        )
        
        raw_text = response.text.replace('"', '').strip()
        synonyms = [s.strip() for s in raw_text.split(',') if s.strip()]
        
        if not synonyms:
            raise ValueError("Risposta vuota dall'LLM")
            
        print(f"🌐 [AI Semantic Layer] Termini generati dall'LLM: {synonyms}")
        return synonyms
        
    except Exception as e:
        return [f"API_ERROR: {str(e)}"]

@st.cache_data(show_spinner=False)
def extract_patient_profile(clinical_text, api_key=None):
    """
    Estrae i parametri clinici (Età, Sesso, Mutazioni) dal referto in formato testo libero.
    """
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY")
        except:
            pass
            
    if not genai or not api_key:
        return {"age": None, "sex": "ALL", "biomarkers": ""}
        
    try:
        client = genai.Client(api_key=api_key)
        
        prompt = (
            f"Estrai le seguenti informazioni cliniche dal testo fornito. "
            f"Testo: '{clinical_text}'\n\n"
            f"Rispondi ESATTAMENTE e SOLO con un oggetto JSON valido con queste chiavi:\n"
            f"- 'age' (numero intero, oppure null se non specificata)\n"
            f"- 'sex' (stringa: 'MALE', 'FEMALE', oppure 'ALL' se non specificato)\n"
            f"- 'biomarkers' (stringa unica con le mutazioni separate da virgola, es. 'BRAF, KRAS', oppure stringa vuota se non ci sono)\n"
            f"Niente markdown, niente spiegazioni, solo il JSON puro."
        )
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
        )
        
        import json
        raw_json = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw_json)
        return data
        
    except Exception as e:
        print(f"Errore estrazione profilo: {e}")
        return {"age": None, "sex": "ALL", "biomarkers": ""}

@st.cache_data(show_spinner=False)
def find_best_matches_semantic(natural_query, api_key=None, intent_filter="ALL", patient_profile=None):
    """
    Effettua la ricerca sul database usando l'array di termini espansi dinamicamente.
    intent_filter può essere: 'OPEN', 'COMPLETED', 'ALL'
    patient_profile: dict con 'age', 'sex', 'biomarkers'
    """
    synonyms = expand_query(natural_query, api_key=api_key)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Costruiamo la query dinamicamente. WHERE 1=0 serve per concatenare in sicurezza gli OR
    base_query = '''
        SELECT study_id, title, conditions, phases, status, start_date, completion_date, has_results, why_stopped, countries, elig_sex, elig_min_age, elig_max_age, elig_criteria
        FROM studies
        WHERE (1=0
    '''
    
    order_by_clause = " ORDER BY ("
    order_params = []
    params = []
    
    # Biomarcatori aggiunti come sinonimi per dare più peso ai trial che li menzionano
    search_terms = list(synonyms)
    if patient_profile and patient_profile.get("biomarkers"):
        biomarks = [b.strip() for b in patient_profile["biomarkers"].split(",") if b.strip()]
        search_terms.extend(biomarks)
    
    for idx, syn in enumerate(search_terms):
        base_query += ' OR conditions LIKE ? OR title LIKE ?'
        params.extend([f'%{syn}%', f'%{syn}%'])
        
        # Un match esatto o parziale nel titolo vale di più (es. 2 punti), nelle conditions 1 punto
        score_term = f"(CASE WHEN title LIKE ? THEN 2 ELSE 0 END) + (CASE WHEN conditions LIKE ? THEN 1 ELSE 0 END)"
        if idx > 0:
            order_by_clause += " + "
        order_by_clause += score_term
        order_params.extend([f'%{syn}%', f'%{syn}%'])
        
    base_query += ')'
    order_by_clause += ") DESC"
    
    # Logica Filtro Intent
    if intent_filter == "OPEN":
        base_query += " AND source='ClinicalTrials' AND (UPPER(status) LIKE '%RECRUITING%' OR UPPER(status) LIKE '%ACTIVE%')"
    elif intent_filter == "COMPLETED":
        base_query += " AND (UPPER(status) LIKE '%COMPLETED%' OR source='PubMed')"
    
    # Estraiamo un pool più largo per poter filtrare in memoria i pazienti
    final_query = base_query + order_by_clause + " LIMIT 50"
    params = params + order_params
    
    cursor.execute(final_query, params)
    raw_results = cursor.fetchall()
    conn.close()
    
    # POST-FILTERING (Paziente)
    filtered_results = []
    for row in raw_results:
        study_id, title, conditions, phases, status, start_date, comp_date, has_res, why_stopped, countries, elig_sex, elig_min_age, elig_max_age, elig_criteria = row
        
        # Se c'è un profilo paziente
        if patient_profile:
            p_sex = patient_profile.get("sex", "ALL")
            p_age = patient_profile.get("age")
            
            # 1. Filtro Sesso
            if p_sex in ["MALE", "FEMALE"] and elig_sex in ["MALE", "FEMALE"]:
                if p_sex != elig_sex:
                    continue # Scartato: sesso non compatibile
            
            # 2. Filtro Età
            if p_age is not None:
                # Estraiamo l'età minima (es. "18 Years" -> 18)
                import re
                try:
                    if elig_min_age:
                        min_match = re.search(r'(\d+)', elig_min_age)
                        if min_match and int(min_match.group(1)) > p_age:
                            continue # Paziente troppo giovane
                    if elig_max_age:
                        max_match = re.search(r'(\d+)', elig_max_age)
                        if max_match and int(max_match.group(1)) < p_age:
                            continue # Paziente troppo vecchio
                except:
                    pass
        
        # Rimuoviamo i campi extra usati solo per il filtro in modo da non rompere l'unpacking
        filtered_results.append((study_id, title, conditions, phases, status, start_date, comp_date, has_res, why_stopped, countries))
        
        if len(filtered_results) >= 5:
            break
            
    return filtered_results, synonyms

def print_report_semantic(results, original_query, synonyms):
    print("\n" + "="*80)
    print(" 🏥 MEDDATA_CORE: CLINICAL ROUTER - SEMANTIC MATCH REPORT 🏥")
    print("="*80)
    print(f"🗣️ Query Naturale    : '{original_query}'")
    print(f"🤖 Termini Espansi   : {', '.join(synonyms)}")
    print("-" * 80)
    
    if not results:
        print("Nessun trial compatibile trovato nel database locale.")
        print("="*80 + "\n")
        return
        
    print(f"Trovati {len(results)} Top Match:\n")
    
    for idx, row in enumerate(results, 1):
        study_id, title, conditions, phases, status, start_date, comp_date, has_res, why_stopped, countries = row
        print(f"[{idx}] 🆔 ID Studio : {study_id}")
        print(f"    🏷️ Titolo    : {title[:80]}..." if len(title) > 80 else f"    🏷️ Titolo    : {title}")
        print(f"    🦠 Patologia : {conditions[:80]}..." if len(conditions) > 80 else f"    🦠 Patologia : {conditions}")
        print(f"    📈 Fase      : {phases}")
        print(f"    🚥 Status    : {status}")
        print(f"    🌍 Paesi     : {countries}")
        print("-" * 80)
        
    print("="*80 + "\n")

if __name__ == "__main__":
    # Test 1: Termine colloquiale in italiano (Rene)
    query_1 = "Tumore al rene"
    results_1, syn_1 = find_best_matches_semantic(query_1)
    print_report_semantic(results_1, query_1, syn_1)
    
    # Test 2: Termine colloquiale in italiano (Prostata)
    query_2 = "Cancro alla prostata"
    results_2, syn_2 = find_best_matches_semantic(query_2)
    print_report_semantic(results_2, query_2, syn_2)
