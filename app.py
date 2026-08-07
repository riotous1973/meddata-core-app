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

# Barra laterale rimossa per mantenere l'interfaccia pulita per i medici.
# La chiave API verrà letta automaticamente dalle Streamlit Secrets (st.secrets o os.environ).

tab1, tab2 = st.tabs(["🔍 Router Clinico", "📊 Analytics Dashboard"])

with tab1:
    st.write("Usa la barra di ricerca sottostante per descrivere la patologia o il sintomo (anche in linguaggio naturale o in italiano). Il nostro **AI Semantic Layer** si occuperà di tradurre ed espandere la query nei corretti termini scientifici internazionali, trovando all'istante i trial sperimentali corrispondenti.")

    st.divider()

    # Form di Ricerca per abilitare il tasto "Invio"
    with st.form(key='search_form'):
        # Area di Input
        query = st.text_input("Inserisci la patologia (es. 'Tumore al rene', 'Caduta dei capelli', 'Pressione alta')", placeholder="Cerca patologia...")

        # Filtri di Intento
        intent_options = {
            "⚪ Ricerca Globale (Tutti i risultati)": "ALL",
            "🟢 Trial Aperti (Solo Sperimentali)": "OPEN",
            "🔵 Studi Conclusi & Letteratura": "COMPLETED"
        }
        selected_intent_label = st.radio("Filtra per stato del trial:", options=list(intent_options.keys()), horizontal=True)
        selected_intent = intent_options[selected_intent_label]

        submit_button = st.form_submit_button("Cerca Trial 🚀", type="primary")

    if submit_button:
        if not query.strip():
            st.warning("Per favore, inserisci una patologia o un termine di ricerca.")
        else:
            # Processing Visivo
            with st.spinner("🤖 L'intelligenza Artificiale sta traducendo ed espandendo la query..."):
                time.sleep(0.8) # Piccola pausa scenica per simulare il caricamento LLM
                # Richiamo la funzione dal modulo originale (leggerà la chiave da os.environ)
                results, synonyms = clinical_router.find_best_matches_semantic(query, intent_filter=selected_intent)
            
            st.success("Ricerca completata!")
            
            # Mostro l'avvenuta espansione semantica
            st.markdown(f"**Termini scientifici individuati dall'AI:** `{', '.join(synonyms)}`")
            st.divider()
            
            if not results:
                st.warning(f"⚠️ **Nessun trial clinico in corso trovato per '{query}'.**\n\nQuesto può accadere se la patologia è troppo specifica o se non ci sono trial registrati al momento.\n\n*Suggerimento: Prova a utilizzare una classificazione diagnostica più ampia.*")
            else:
                st.markdown(f"### Trovati {len(results)} Top Match:")
                
                # Rendering dei risultati in "Cards"
                for row in results:
                    study_id, title, conditions, phases, status, start_date, comp_date, has_res, why_stopped, countries = row
                    
                    # Logica semaforo
                    status_upper = (status or "").upper()
                    status_icon = "⚪"
                    status_color = "#555555" # Default gray
                    
                    if "RECRUITING" in status_upper or "ACTIVE" in status_upper:
                        status_icon = "🟢"
                        status_color = "#2e7d32"
                    elif "COMPLETED" in status_upper or "PUBLISHED" in status_upper:
                        status_icon = "🔵"
                        status_color = "#1565c0"
                    elif "TERMINATED" in status_upper or "WITHDRAWN" in status_upper or "SUSPENDED" in status_upper:
                        status_icon = "🔴"
                        status_color = "#c62828"
                        
                    # Warning Motivo Stop
                    why_stopped_html = ""
                    if why_stopped and "🔴" in status_icon:
                        why_stopped_html = f'<div style="margin-top: 10px; padding: 8px; background-color: #3b1515; border-left: 3px solid #ff4444; color: #ff8888; font-size: 0.9em;">⚠️ <b>Interrotto:</b> {why_stopped}</div>'
                        
                    # Date info
                    date_info = f"📅 {start_date or '?'} ➔ {comp_date or '?'}"
                    
                    # Risultati
                    res_badge = '<span class="badge" style="background-color: #b8860b; color: white;">🏆 Risultati Disponibili</span>' if has_res else ""
                    
                    # Generazione URL dinamica
                    if study_id.startswith("PMID:"):
                        pmid = study_id.split(":")[1]
                        study_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    else:
                        study_url = f"https://clinicaltrials.gov/study/{study_id}"
                    
                    # Pulizia stringhe array JSON per l'estetica
                    try:
                        cond_list = json.loads(conditions) if conditions else []
                        cond_str = ", ".join(cond_list)
                    except:
                        cond_str = conditions
                        
                    try:
                        phase_list = json.loads(phases) if phases else []
                        phase_str = ", ".join(phase_list)
                    except:
                        phase_str = phases

                    # Nazioni
                    try:
                        country_list = json.loads(countries) if countries else []
                        if country_list:
                            if "Italy" in country_list:
                                c_style = "background-color: #008c45; color: white; border: 1px solid #f4f5f0;"
                                country_str = "Italia 🇮🇹"
                            else:
                                c_style = ""
                                country_str = ", ".join(country_list[:3]) + ("..." if len(country_list)>3 else "")
                            country_badge = f'<span class="badge" style="{c_style}">🌍 {country_str}</span>'
                        else:
                            country_badge = ""
                    except:
                        country_badge = ""
                        
                    card_html = f"""
<div class="stCard">
    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div class="study-id">🆔 <a href="{study_url}" target="_blank">{study_id}</a></div>
        <div>
            <span class="badge" style="background-color: {status_color}; color: white; border: 1px solid {status_color};">{status_icon} {status or 'UNKNOWN'}</span>
            {res_badge}
        </div>
    </div>
    <div class="study-title">{title}</div>
    <div><span class="badge">🦠 {cond_str[:100]}{'...' if len(cond_str)>100 else ''}</span></div>
    <div style="margin-top: 8px;">
        <span class="badge">📈 {phase_str}</span>
        <span class="badge">{date_info}</span>
        {country_badge}
    </div>
    {why_stopped_html}
</div>
"""
                    st.markdown(card_html.replace('\n', ''), unsafe_allow_html=True)


with tab2:
    st.header("Statistiche Locali del Database")
    st.write("Una panoramica in tempo reale sui trial clinici attualmente scaricati e normalizzati nella Staging Area.")
    
    # Query the SQLite database
    conn = sqlite3.connect(clinical_router.DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT phases, conditions FROM studies")
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        st.error(f"Errore database: {e}")
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
