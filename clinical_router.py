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
def find_best_matches_semantic(natural_query, api_key=None):
    """
    Effettua la ricerca sul database usando l'array di termini espansi dinamicamente.
    """
    synonyms = expand_query(natural_query, api_key=api_key)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Costruiamo la query dinamicamente. WHERE 1=0 serve per concatenare in sicurezza gli OR
    query = '''
        SELECT study_id, title, conditions, phases
        FROM studies
        WHERE 1=0
    '''
    params = []
    
    # Per ogni sinonimo generato dall'AI, cerchiamo nella patologia o nel titolo
    for syn in synonyms:
        query += ' OR conditions LIKE ? OR title LIKE ?'
        params.extend([f'%{syn}%', f'%{syn}%'])
        
    query += ' LIMIT 5'
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    return results, synonyms

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
        study_id, title, conditions, phases = row
        print(f"[{idx}] 🆔 ID Studio : {study_id}")
        print(f"    🏷️ Titolo    : {title[:80]}..." if len(title) > 80 else f"    🏷️ Titolo    : {title}")
        print(f"    🦠 Patologia : {conditions[:80]}..." if len(conditions) > 80 else f"    🦠 Patologia : {conditions}")
        print(f"    📈 Fase      : {phases}")
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
