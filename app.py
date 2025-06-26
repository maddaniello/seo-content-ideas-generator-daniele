import streamlit as st
import pandas as pd
import requests
import json
import time
import io
from datetime import datetime
import openai
from typing import List, Dict, Any
import re

# Configurazione della pagina
st.set_page_config(
    page_title="Piano Editoriale SEO",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizzato
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 30px;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Classe principale per l'applicazione
class SEOEditorialPlanner:
    def __init__(self):
        self.openai_client = None
        self.semrush_api_key = None
        self.serper_api_key = None
        
    def setup_apis(self, openai_key: str, semrush_key: str, serper_key: str):
        """Configurazione delle API"""
        try:
            self.openai_client = openai.OpenAI(api_key=openai_key)
            self.semrush_api_key = semrush_key
            self.serper_api_key = serper_key
            return True
        except Exception as e:
            st.error(f"Errore nella configurazione delle API: {str(e)}")
            return False
    
    def get_semrush_keywords(self, domain: str, limit: int = 50) -> List[Dict]:
        """Recupera keywords da SEMrush"""
        try:
            url = "https://api.semrush.com/"
            params = {
                'type': 'domain_organic',
                'key': self.semrush_api_key,
                'display_limit': limit,
                'domain': domain,
                'database': 'it',  # Database italiano
                'export_columns': 'Ph,Po,Nq,Cp,Ur,Tr,Tc,Co,Nr,Td'
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                keywords = []
                for line in lines[1:]:  # Skip header
                    parts = line.split(';')
                    if len(parts) >= 4:
                        keywords.append({
                            'keyword': parts[0],
                            'position': parts[1],
                            'volume': parts[2],
                            'cpc': parts[3]
                        })
                return keywords
            else:
                st.warning(f"Errore SEMrush: {response.status_code}")
                return []
        except Exception as e:
            st.error(f"Errore SEMrush: {str(e)}")
            return []
    
    def get_competitor_keywords(self, competitors: List[str]) -> List[Dict]:
        """Analizza le keywords dei competitor"""
        all_keywords = []
        for competitor in competitors:
            if competitor.strip():
                keywords = self.get_semrush_keywords(competitor.strip())
                for kw in keywords:
                    kw['source'] = competitor
                    all_keywords.append(kw)
                time.sleep(1)  # Rate limiting
        return all_keywords
    
    def get_serper_data(self, query: str) -> Dict:
        """Recupera dati da Serper.dev"""
        try:
            url = "https://google.serper.dev/search"
            headers = {
                'X-API-KEY': self.serper_api_key,
                'Content-Type': 'application/json'
            }
            payload = {
                'q': query,
                'gl': 'it',
                'hl': 'it',
                'num': 10
            }
            
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                st.warning(f"Errore Serper: {response.status_code}")
                return {}
        except Exception as e:
            st.error(f"Errore Serper: {str(e)}")
            return {}
    
    def extract_people_also_ask(self, serper_data: Dict) -> List[str]:
        """Estrae le domande 'People Also Ask' dai risultati Serper"""
        paa = []
        if 'peopleAlsoAsk' in serper_data:
            for item in serper_data['peopleAlsoAsk']:
                paa.append(item.get('question', ''))
        return paa
    
    def generate_content_ideas(self, site_info: Dict, keywords: List[Dict]) -> List[Dict]:
        """Genera idee di contenuto usando OpenAI"""
        try:
            # Prepara il prompt
            keywords_text = ", ".join([kw['keyword'] for kw in keywords[:20]])
            
            prompt = f"""Sei un esperto SEO e content marketer. Basandoti sulle seguenti informazioni:

Sito: {site_info['nome_sito']}
URL: {site_info['url_sito']}
Descrizione: {site_info['descrizione_pagina']}
Obiettivi: {site_info['obiettivi']}
Argomenti da evitare: {site_info['argomenti_evitare']}
Keywords principali: {keywords_text}

Genera 15 idee per articoli di blog ottimizzati SEO. Per ogni idea fornisci:
1. Titolo dell'articolo
2. Breve descrizione (2-3 righe)
3. Obiettivo specifico dell'articolo
4. Parole chiave target (3-5 keywords)

Rispondi SOLO con un array JSON valido in questo formato:
[
    {{
        "titolo": "Titolo articolo",
        "descrizione": "Descrizione dell'articolo",
        "obiettivo": "Obiettivo specifico",
        "keywords_target": ["keyword1", "keyword2", "keyword3"]
    }}
]"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Pulisci la risposta per estrarre solo il JSON
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            # Trova l'array JSON
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_content = content[start_idx:end_idx]
                return json.loads(json_content)
            else:
                st.error("Formato JSON non valido nella risposta OpenAI")
                return []
                
        except json.JSONDecodeError as e:
            st.error(f"Errore parsing JSON: {str(e)}")
            return []
        except Exception as e:
            st.error(f"Errore OpenAI: {str(e)}")
            return []
    
    def generate_fallback_content_ideas(self, site_info: Dict, keywords: List[Dict]) -> List[Dict]:
        """Genera idee di contenuto di fallback se OpenAI fallisce"""
        fallback_ideas = []
        
        # Usa le prime 15 keywords per creare idee base
        top_keywords = keywords[:15] if len(keywords) >= 15 else keywords
        
        for i, kw in enumerate(top_keywords):
            idea = {
                "titolo": f"Guida Completa a {kw['keyword'].title()}",
                "descrizione": f"Un articolo approfondito su {kw['keyword']} per {site_info['nome_sito']}. Coprirà tutti gli aspetti principali per soddisfare le ricerche degli utenti.",
                "obiettivo": "Aumentare traffico organico e posizionamento per keyword target",
                "keywords_target": [kw['keyword']]
            }
            fallback_ideas.append(idea)
        
        # Se non ci sono abbastanza keywords, crea idee generiche
        while len(fallback_ideas) < 15:
            generic_topics = [
                "Tendenze del Settore 2024",
                "Domande Frequenti",
                "Confronto Soluzioni",
                "Caso Studio Successo",
                "Errori Comuni da Evitare"
            ]
            
            topic = generic_topics[len(fallback_ideas) % len(generic_topics)]
            idea = {
                "titolo": f"{topic} - {site_info['nome_sito']}",
                "descrizione": f"Articolo su {topic.lower()} per il settore di {site_info['nome_sito']}",
                "obiettivo": site_info['obiettivi'][:100] + "..." if len(site_info['obiettivi']) > 100 else site_info['obiettivi'],
                "keywords_target": [kw['keyword'] for kw in keywords[:3]]
            }
            fallback_ideas.append(idea)
        
        return fallback_ideas[:15]
        """Crea il piano editoriale finale"""
        editorial_data = []
        
        for i, idea in enumerate(content_ideas):
            # Trova keywords correlate
            related_keywords = []
            for kw in keywords:
                for target_kw in idea['keywords_target']:
                    if target_kw.lower() in kw['keyword'].lower() or kw['keyword'].lower() in target_kw.lower():
                        related_keywords.append(f"{kw['keyword']} ({kw['volume']})")
            
            # Ottieni People Also Ask per la prima keyword target
            paa_list = []
            if idea['keywords_target']:
                serper_data = self.get_serper_data(idea['keywords_target'][0])
                paa_list = self.extract_people_also_ask(serper_data)
                time.sleep(1)  # Rate limiting
            
            editorial_data.append({
                'Titolo Articolo': idea['titolo'],
                'Descrizione': idea['descrizione'],
                'Keywords Target': ', '.join(related_keywords[:10]),  # Limita a 10 keywords
                'People Also Ask': ' | '.join(paa_list[:5]),  # Limita a 5 PAA
                'Obiettivo Articolo': idea['obiettivo'],
                'Priorità': f"Alta" if i < 5 else f"Media" if i < 10 else "Bassa",
                'Data Suggerita': pd.date_range(start='2024-01-01', periods=len(content_ideas), freq='W')[i].strftime('%Y-%m-%d')
            })
        
        return pd.DataFrame(editorial_data)

# Inizializza l'app
if 'planner' not in st.session_state:
    st.session_state.planner = SEOEditorialPlanner()

# Header principale
st.markdown('<h1 class="main-header">🚀 Piano Editoriale SEO Automatizzato</h1>', unsafe_allow_html=True)

# Sidebar per le API keys
st.sidebar.header("🔑 Configurazione API")
st.sidebar.markdown("""
Inserisci le tue API keys per utilizzare l'applicazione:
""")

openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
semrush_key = st.sidebar.text_input("SEMrush API Key", type="password")
serper_key = st.sidebar.text_input("Serper.dev API Key", type="password")

if st.sidebar.button("Configura API"):
    if openai_key and semrush_key and serper_key:
        if st.session_state.planner.setup_apis(openai_key, semrush_key, serper_key):
            st.sidebar.success("✅ API configurate correttamente!")
            st.session_state.apis_configured = True
    else:
        st.sidebar.error("❌ Inserisci tutte le API keys")

# Sezione principale
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📊 Informazioni del Progetto")
    
    # Form per le informazioni del sito
    with st.form("site_info_form"):
        nome_sito = st.text_input("Nome del Sito*", placeholder="Es: La Mia Azienda")
        url_sito = st.text_input("URL del Sito*", placeholder="https://www.example.com")
        
        st.subheader("Competitor (Opzionale)")
        competitor1 = st.text_input("Competitor 1", placeholder="https://competitor1.com")
        competitor2 = st.text_input("Competitor 2", placeholder="https://competitor2.com")
        competitor3 = st.text_input("Competitor 3", placeholder="https://competitor3.com")
        
        descrizione_pagina = st.text_area(
            "Descrizione della pagina 'Chi Siamo'*",
            placeholder="Descrivi la tua azienda, i valori, il tone of voice...",
            height=100
        )
        
        argomenti_evitare = st.text_area(
            "Argomenti da NON trattare",
            placeholder="Specifica argomenti che vuoi evitare negli articoli...",
            height=80
        )
        
        obiettivi = st.text_area(
            "Obiettivi degli articoli*",
            placeholder="Es: Aumentare traffico organico, generare lead, educare i clienti...",
            height=80
        )
        
        submitted = st.form_submit_button("🚀 Genera Piano Editoriale", use_container_width=True)

with col2:
    st.header("ℹ️ Informazioni")
    st.markdown("""
    <div class="info-box">
    <h4>Come funziona:</h4>
    <ol>
        <li>Configura le API keys nella sidebar</li>
        <li>Compila il form con le informazioni del tuo sito</li>
        <li>L'app analizzerà il tuo sito e i competitor</li>
        <li>Genererà un piano editoriale ottimizzato</li>
        <li>Scarica il file Excel con tutti i dettagli</li>
    </ol>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="warning-box">
    <strong>Nota:</strong> Assicurati di avere crediti sufficienti nelle tue API per evitare interruzioni.
    </div>
    """, unsafe_allow_html=True)

# Elaborazione dei dati
if submitted and hasattr(st.session_state, 'apis_configured'):
    if nome_sito and url_sito and descrizione_pagina and obiettivi:
        
        # Crea il dizionario con le informazioni del sito
        site_info = {
            'nome_sito': nome_sito,
            'url_sito': url_sito,
            'descrizione_pagina': descrizione_pagina,
            'argomenti_evitare': argomenti_evitare,
            'obiettivi': obiettivi
        }
        
        # Mostra progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Analisi keywords del sito principale
            status_text.text("🔍 Analizzando keywords del sito principale...")
            progress_bar.progress(20)
            
            domain = url_sito.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
            main_keywords = st.session_state.planner.get_semrush_keywords(domain)
            
            if not main_keywords:
                st.warning("⚠️ Nessuna keyword trovata da SEMrush per il dominio principale. Verifica l'API key e che il dominio sia indicizzato.")
                # Crea keywords di esempio basate sul sito
                main_keywords = [
                    {'keyword': nome_sito.lower(), 'position': '1', 'volume': '1000', 'cpc': '1.0'},
                    {'keyword': f"{nome_sito.lower()} servizi", 'position': '5', 'volume': '500', 'cpc': '1.5'},
                    {'keyword': f"{nome_sito.lower()} contatti", 'position': '3', 'volume': '200', 'cpc': '0.5'}
                ]
            
            # Step 2: Analisi competitor
            status_text.text("🏆 Analizzando competitor...")
            progress_bar.progress(40)
            
            competitors = [comp for comp in [competitor1, competitor2, competitor3] if comp.strip()]
            competitor_keywords = st.session_state.planner.get_competitor_keywords(competitors)
            
            # Combina tutte le keywords
            all_keywords = main_keywords + competitor_keywords
            
            # Step 3: Generazione idee contenuto
            status_text.text("🧠 Generando idee per i contenuti...")
            progress_bar.progress(60)
            
            content_ideas = st.session_state.planner.generate_content_ideas(site_info, all_keywords)
            
            # Se OpenAI fallisce, usa il fallback
            if not content_ideas:
                st.warning("⚠️ Problema con OpenAI, utilizzo generatore di backup...")
                content_ideas = st.session_state.planner.generate_fallback_content_ideas(site_info, all_keywords)
            
            # Step 4: Creazione piano editoriale
            status_text.text("📝 Creando il piano editoriale...")
            progress_bar.progress(80)
            
            editorial_plan = st.session_state.planner.create_editorial_plan(site_info, all_keywords, content_ideas)
            
            # Step 5: Completamento
            status_text.text("✅ Piano editoriale completato!")
            progress_bar.progress(100)
            
            # Mostra risultati
            st.success("🎉 Piano editoriale generato con successo!")
            
            # Visualizza il dataframe
            st.subheader("📋 Anteprima Piano Editoriale")
            st.dataframe(editorial_plan, use_container_width=True)
            
            # Statistiche
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Articoli Generati", len(editorial_plan))
            with col2:
                st.metric("Keywords Analizzate", len(all_keywords))
            with col3:
                st.metric("Competitor Analizzati", len(competitors))
            with col4:
                st.metric("Priorità Alta", len(editorial_plan[editorial_plan['Priorità'] == 'Alta']))
            
            # Download del file Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                editorial_plan.to_excel(writer, index=False, sheet_name='Piano Editoriale')
                
                # Aggiungi un foglio con le informazioni del progetto
                project_info = pd.DataFrame({
                    'Campo': ['Nome Sito', 'URL Sito', 'Data Generazione', 'Totale Articoli'],
                    'Valore': [nome_sito, url_sito, datetime.now().strftime('%Y-%m-%d %H:%M'), len(editorial_plan)]
                })
                project_info.to_excel(writer, index=False, sheet_name='Info Progetto')
            
            st.download_button(
                label="📥 Scarica Piano Editoriale (Excel)",
                data=output.getvalue(),
                file_name=f"piano_editoriale_{nome_sito.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"❌ Errore durante la generazione: {str(e)}")
            progress_bar.empty()
            status_text.empty()
    
    else:
        st.error("❌ Compila tutti i campi obbligatori (contrassegnati con *)")

elif submitted:
    st.error("❌ Configura prima le API keys nella sidebar")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>Piano Editoriale SEO Automatizzato - Sviluppato con ❤️ per il digital marketing</p>
</div>
""", unsafe_allow_html=True)
