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
            source TEXT DEFAULT 'ClinicalTrials'
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
        INSERT INTO studies (study_id, title, conditions, phases, interventions, source)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(study_id) DO UPDATE SET
            title=excluded.title,
            conditions=excluded.conditions,
            phases=excluded.phases,
            interventions=excluded.interventions,
            source=excluded.source
    '''
    
    data_tuples = []
    for r in records:
        data_tuples.append((
            r.get("study_id"),
            r.get("title"),
            json.dumps(r.get("conditions", [])),
            json.dumps(r.get("phases", [])),
            json.dumps(r.get("interventions", [])),
            r.get("source", "ClinicalTrials")
        ))
        
    cursor.executemany(insert_query, data_tuples)
    conn.commit()
    
    print(f"Successfully inserted/updated {cursor.rowcount} records in SQLite.")
    conn.close()

if __name__ == "__main__":
    init_db()
