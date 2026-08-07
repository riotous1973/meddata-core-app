import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'clinical_data.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    print(f"Initializing SQLite database at {DB_PATH}...")
    conn = get_connection()
    cursor = conn.cursor()
    
    # Crea la tabella se non esiste
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS studies (
            study_id TEXT PRIMARY KEY,
            title TEXT,
            conditions TEXT,
            phases TEXT,
            interventions TEXT,
            source TEXT DEFAULT 'ClinicalTrials',
            status TEXT,
            start_date TEXT,
            completion_date TEXT,
            has_results BOOLEAN,
            why_stopped TEXT,
            countries TEXT,
            elig_sex TEXT,
            elig_min_age TEXT,
            elig_max_age TEXT,
            elig_criteria TEXT
        )
    ''')
    
    # Retrocompatibilità: aggiunge la colonna se la tabella esiste già ma è alla vecchia versione
    try:
        cursor.execute("ALTER TABLE studies ADD COLUMN source TEXT DEFAULT 'ClinicalTrials'")
    except sqlite3.OperationalError:
        pass

    
    conn.commit()
    conn.close()
    print("Database initialization complete.")

def insert_records(records):
    """
    Inserisce o aggiorna una lista di dizionari nel DB.
    Le liste (conditions, phases, interventions) vengono serializzate in stringhe JSON.
    """
    if not records:
        return
        
    conn = get_connection()
    cursor = conn.cursor()
    
    insert_query = '''
        INSERT INTO studies (study_id, title, conditions, phases, interventions, source, status, start_date, completion_date, has_results, why_stopped, countries, elig_sex, elig_min_age, elig_max_age, elig_criteria)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(study_id) DO UPDATE SET
            title=excluded.title,
            conditions=excluded.conditions,
            phases=excluded.phases,
            interventions=excluded.interventions,
            source=excluded.source,
            status=excluded.status,
            start_date=excluded.start_date,
            completion_date=excluded.completion_date,
            has_results=excluded.has_results,
            why_stopped=excluded.why_stopped,
            countries=excluded.countries,
            elig_sex=excluded.elig_sex,
            elig_min_age=excluded.elig_min_age,
            elig_max_age=excluded.elig_max_age,
            elig_criteria=excluded.elig_criteria
    '''
    
    data_tuples = []
    for r in records:
        data_tuples.append((
            r.get("study_id"),
            r.get("title"),
            json.dumps(r.get("conditions", [])),
            json.dumps(r.get("phases", [])),
            json.dumps(r.get("interventions", [])),
            r.get("source", "ClinicalTrials"),
            r.get("status"),
            r.get("start_date"),
            r.get("completion_date"),
            r.get("has_results", False),
            r.get("why_stopped"),
            r.get("countries"),
            r.get("elig_sex", "ALL"),
            r.get("elig_min_age", ""),
            r.get("elig_max_age", ""),
            r.get("elig_criteria", "")
        ))
        
    cursor.executemany(insert_query, data_tuples)
    conn.commit()
    
    print(f"Successfully inserted/updated {cursor.rowcount} records in SQLite.")
    conn.close()

if __name__ == "__main__":
    init_db()
