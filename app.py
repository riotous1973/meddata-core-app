import streamlit as st
import time
import json
import sqlite3
import pandas as pd
import plotly.express as px
from collections import Counter
import clinical_router
import importlib

# Forza il reload del modulo per aggirare la cache di Streamlit
importlib.reload(clinical_router)

# Configurazione base della pagina
st.set_page_config(
    page_title="MedData Core",
    page_icon="🏥",
    layout="wide"
)

# Custom CSS opzionale per migliorare le cards
st.markdown("""
    <style>
    .stCard {
        border-radius: 8px;
        padding: 20px;
        background-color: #1e1e1e;
        border: 1px solid #333;
        margin-bottom: 15px;
        color: #f1f1f1;
    }
    .study-id {
        color: #4CAF50;
        font-weight: bold;
    }
    .study-id a {
        color: #4CAF50;
        text-decoration: none;
    }
    .study-id a:hover {
        text-decoration: underline;
    }
    .study-title {
        font-size: 1.1em;
        margin-top: 10px;
        margin-bottom: 10px;
        color: #ffffff;
    }
    .badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 12px;
        background-color: #3b3b3b;
        font-size: 0.85em;
        margin-right: 5px;
        color: #e0e0e0;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏥 MedData Core: Clinical Router")
st.markdown("### Il motore di smistamento definitivo per i trial clinici.")

with st.sidebar:
    st.header("⚙️ Impostazioni API")
    api_key_input = st.text_input("Inserisci Gemini API Key", type="password")
    
    if api_key_input:
        st.session_state["gemini_key"] = api_key_input
        st.success("Chiave API caricata!")
    else:
        st.warning("Inserisci una API Key per sbloccare la traduzione AI avanzata.")

tab1, tab2 = st.tabs(["🔍 Router Clinico", "📊 Analytics Dashboard"])

with tab1:
    st.write("Usa la barra di ricerca sottostante per descrivere la patologia o il sintomo (anche in linguaggio naturale o in italiano). Il nostro **AI Semantic Layer** si occuperà di tradurre ed espandere la query nei corretti termini scientifici internazionali, trovando all'istante i trial sperimentali corrispondenti.")

    st.divider()

    # Area di Input
    query = st.text_input("Inserisci la patologia (es. 'Tumore al rene', 'Caduta dei capelli', 'Pressione alta')", placeholder="Cerca patologia...")

    if st.button("Cerca Trial 🚀", type="primary"):
        if not query.strip():
            st.warning("Per favore, inserisci una patologia o un termine di ricerca.")
        else:
            # Processing Visivo
            with st.spinner("🤖 L'intelligenza Artificiale sta traducendo ed espandendo la query..."):
                time.sleep(0.8) # Piccola pausa scenica per simulare il caricamento LLM
                
                # Prendi la chiave API dalla sessione
                current_api_key = st.session_state.get("gemini_key")
                
                # Richiamo la funzione dal modulo originale
                results, synonyms = clinical_router.find_best_matches_semantic(query, api_key=current_api_key)
            
            st.success("Ricerca completata!")
            
            # Mostro l'avvenuta espansione semantica
            st.markdown(f"**Termini scientifici individuati dall'AI:** `{', '.join(synonyms)}`")
            st.divider()
            
            if not results:
                st.info("Nessun trial compatibile trovato nel database locale.")
            else:
                st.markdown(f"### Trovati {len(results)} Top Match:")
                
                # Rendering dei risultati in "Cards"
                for row in results:
                    study_id, title, conditions, phases = row
                    
                    card_html = f"""
                    <div class="stCard">
                        <div class="study-id">🆔 <a href="https://clinicaltrials.gov/study/{study_id}" target="_blank">{study_id}</a></div>
                        <div class="study-title">{title}</div>
                        <div><span class="badge">🦠 {conditions[:100]}{'...' if len(conditions)>100 else ''}</span></div>
                        <div style="margin-top: 8px;"><span class="badge">📈 {phases}</span></div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)


with tab2:
    st.header("Statistiche Locali del Database")
    st.write("Una panoramica in tempo reale sui trial clinici attualmente scaricati e normalizzati nella Staging Area.")
    
    # Query the SQLite database
    conn = sqlite3.connect(clinical_router.DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT phases, conditions FROM studies")
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        rows = []
    
    conn.close()
    
    if not rows:
        st.info("Nessun dato presente nel database locale. Esegui la pipeline di ingestione per popolare i grafici!")
    else:
        st.metric(label="Total Trial Normalizzati in DB", value=len(rows))
        st.divider()
        
        # Aggregate data for charts
        phases_counter = Counter()
        conditions_counter = Counter()
        
        for r in rows:
            try:
                # r[0] is phases (JSON string)
                if r[0]:
                    p_list = json.loads(r[0])
                    for p in p_list:
                        if p and p != "NA":
                            phases_counter[p] += 1
                            
                # r[1] is conditions (JSON string)
                if r[1]:
                    c_list = json.loads(r[1])
                    for c in c_list:
                        if c:
                            conditions_counter[c] += 1
            except json.JSONDecodeError:
                continue
                
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Distribuzione Trial per Fase")
            if phases_counter:
                df_phases = pd.DataFrame(phases_counter.items(), columns=["Phase", "Count"])
                fig_pie = px.pie(df_phases, names="Phase", values="Count", hole=0.4, 
                                 color_discrete_sequence=px.colors.sequential.Teal)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.write("Dati fasi non disponibili.")
                
        with col2:
            st.subheader("Top 10 Patologie nel Database")
            if conditions_counter:
                top_conditions = conditions_counter.most_common(10)
                df_cond = pd.DataFrame(top_conditions, columns=["Condition", "Count"])
                fig_bar = px.bar(df_cond, x="Count", y="Condition", orientation='h',
                                 color="Count", color_continuous_scale="Viridis")
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.write("Dati patologie non disponibili.")
