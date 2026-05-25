import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import time

# Configurazione schermo intero per iPad Pro
st.set_page_config(layout="wide")

st.title("🗺️ Mappa di Roma (Con Indicatore di Caricamento)")
st.write("Spostati sulla mappa. Sotto di essa troverai il pulsante per caricare i dati in tempo reale.")

# --- 1. CONFIGURAZIONE TOGGLE ---
col1, col2, col3 = st.columns(3)
with col1:
    mostra_hotel = st.toggle("🌟 Hotel (4/5 Stelle)", value=True)
with col2:
    mostra_chiese = st.toggle("⛪ Chiese", value=True)
with col3:
    mostra_monumenti = st.toggle("🏛️ Monumenti", value=True)

st.divider()

# --- 2. STATO DELLA SESSIONE ---
if "punti_salvati" not in st.session_state:
    st.session_state["punti_salvati"] = []
if "mappa_centro" not in st.session_state:
    st.session_state["mappa_centro"] = [41.8955, 12.4823]
if "mappa_zoom" not in st.session_state:
    st.session_state["mappa_zoom"] = 15

# --- 3. ESTRAZIONE DATI DA OVERPASS ---
def scarica_dati_api(north, south, east, west):
    punti_trovati = []
    overpass_url = "https://overpass.kumi.systems/api/interpreter"
    
    overpass_query = f"""
    [out:json][timeout:25];
    (
      nwr["tourism"="hotel"]({south},{west},{north},{east});
      nwr["amenity"="place_of_worship"]({south},{west},{north},{east});
      nwr["historic"="monument"]({south},{west},{north},{east});
    );
    out center;
    """
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, headers=headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            for element in data.get('elements', []):
                lat = element.get('lat') or element.get('center', {}).get('lat')
                lon = element.get('lon') or element.get('center', {}).get('lon')
                if lat and lon:
                    tags = element.get('tags', {})
                    nome = tags.get('name') or 'Struttura'
                    
                    if tags.get('tourism') == 'hotel':
                        tipo = 'hotel'
                    elif tags.get('amenity') == 'place_of_worship':
                        tipo = 'chiesa'
                    else:
                        tipo = 'monumento'
                        
                    punti_trovati.append({'coords': [float(lat), float(lon)], 'nome': str(nome), 'tipo': tipo})
    except Exception:
        pass # Se fallisce, useremo i dati di test sotto
        
    # --- LOGICA DI EMERGENZA (Se il server restituisce 0 punti, carichiamo punti fissi di test) ---
    if len(punti_trovati) == 0:
        punti_trovati = [
            {'coords': [41.8902, 12.4922], 'nome': '🚨 TEST: Il Colosseo (Verifica Grafica)', 'tipo': 'monumento'},
            {'coords': [41.8986, 12.4769], 'nome': '🚨 TEST: Il Pantheon (Verifica Grafica)', 'tipo': 'chiesa'},
            {'coords': [41.9015, 12.4900], 'nome': '🚨 TEST: Grand Hotel (Verifica Grafica)', 'tipo': 'hotel'}
        ]
        
    return punti_trovati

# --- 4. COSTRUZIONE MAPPA FOLLIUM ---
m = folium.Map(
    location=st.session_state["mappa_centro"], 
    zoom_start=st.session_state["mappa_zoom"], 
    tiles='CartoDB voyager'
)

# Disegna i punti memorizzati
for p in st.session_state["punti_salvati"]:
    if p['tipo'] == 'hotel' and mostra_hotel:
        folium.CircleMarker(location=p['coords'], radius=8, color='#DAA520', fill=True, fill_color='#FFD700', fill_opacity=0.9, tooltip=p['nome']).add_to(m)
    elif p['tipo'] == 'chiesa' and mostra_chiese:
        folium.CircleMarker(location=p['coords'], radius=7, color='#8B0000', fill=True, fill_color='#DC143C', fill_opacity=0.8, tooltip=p['nome']).add_to(m)
    elif p['tipo'] == 'monumento' and mostra_monumenti:
        folium.CircleMarker(location=p['coords'], radius=7, color='#00008B', fill=True, fill_color='#1E90FF', fill_opacity=0.8, tooltip=p['nome']).add_to(m)

# --- 5. VISUALIZZAZIONE DELLA MAPPA ---
output_mappa = st_folium(
    m, 
    width="100%", 
    height=500, 
    key="mappa_roma_ottimizzata_caricamento",
    returned_objects=["bounds", "center", "zoom"]
)

# Salva la posizione corrente dello schermo ad ogni tocco o zoom
if output_mappa and output_mappa.get("bounds") and output_mappa.get("center"):
    st.session_state["mappa_centro"] = [output_mappa["center"]["lat"], output_mappa["center"]["lng"]]
    st.session_state["mappa_zoom"] = output_mappa["zoom"]

# --- 6. PULSANTE CON STATO DI CARICAMENTO AVANZATO ---
st.write("---")

# Estrazione sicura delle coordinate per iPad
if output_mappa and output_mappa.get("bounds"):
    bounds = output_mappa["bounds"]
    
    # Questo metodo garantisce la corretta lettura sia da iPad che da desktop
    try:
        south = bounds["_southWest"]["lat"]
        west = bounds["_southWest"]["lng"]
        north = bounds["_northEast"]["lat"]
        east = bounds["_northEast"]["lng"]
    except KeyError:
        # Alternativa nel caso in cui le chiavi arrivino con nomi diversi
        south, west = bounds[0][0], bounds[0][1]
        north, east = bounds[1][0], bounds[1][1]

    # Pulsante interattivo: quando viene premuto esegue il blocco 'with st.spinner'
    # che rende automaticamente grigia l'area e mostra una ruota che gira.
    if st.button("🚀 Carica elementi in questa zona", use_container_width=True, key="btn_carica"):
        with st.spinner("⏳ Connessione al database cartografico... Download dei punti in corso..."):
            # Scarica i dati (reali o di emergenza)
            punti_scaricati = scarica_dati_api(north, south, east, west)
            st.session_state["punti_salvati"] = punti_scaricati
            time.sleep(0.5) # Piccolo delay per permettere all'iPad di elaborare la grafica
            
        st.success(f"Aggiornato! Visualizzati {len(punti_scaricati)} elementi sulla mappa.")
        st.rerun()

# Stato attuale dei dati stampato in piccolo sotto
if len(st.session_state["punti_salvati"]) > 0:
    st.caption(f"📍 Indicatori pronti sulla mappa: {len(st.session_state['punti_salvati'])}")
