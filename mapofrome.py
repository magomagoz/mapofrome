import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os

# Configurazione schermo intero per iPad Pro
st.set_page_config(layout="wide")

st.title("🗺️ Mappa di Roma (Database Locale Super-Veloce)")
st.write("Spostati sulla mappa e premi il pulsante per caricare i monumenti, le chiese e gli hotel reali presenti in quella zona.")

# --- 1. CONFIGURAZIONE TOGGLE CON COLORI ---
col1, col2, col3 = st.columns(3)
with col1:
    # Giallo/Arancione per gli Hotel
    mostra_hotel = st.toggle("🟡 :orange[**Hotel (4/5 Stelle)**]", value=True)
with col2:
    # Rosso per le Chiese
    mostra_chiese = st.toggle("🔴 :red[**Chiese**]", value=True)
with col3:
    # Blu per i Monumenti
    mostra_monumenti = st.toggle("🔵 :blue[**Monumenti**]", value=True)

st.divider()

# --- 2. STATO DELLA SESSIONE ---
if "punti_salvati" not in st.session_state:
    st.session_state["punti_salvati"] = []
if "mappa_centro" not in st.session_state:
    st.session_state["mappa_centro"] = [41.8955, 12.4823]
if "mappa_zoom" not in st.session_state:
    st.session_state["mappa_zoom"] = 15

# --- 3. LETTURA DATI LOCALE (A prova di blocchi di rete) ---
def carica_punti_locali(north, south, east, west):
    punti_filtrati = []
    file_path = "punti_roma.geojson"
    
    # Controlla se il file esiste
    if not os.path.exists(file_path):
        st.error(f"File {file_path} non trovato su GitHub! Controlla di averlo creato.")
        return []
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        for feature in data.get("features", []):
            coords = feature["geometry"]["coordinates"] # [lon, lat] nel formato GeoJSON
            lon, lat = coords[0], coords[1]
            props = feature["properties"]
            
            # Filtra i punti: li prende solo se sono dentro l'area visibile dell'iPad
            if south <= lat <= north and west <= lon <= east:
                punti_filtrati.append({
                    'coords': [lat, lon],
                    'nome': props["nome"],
                    'tipo': props["tipo"]
                })
    except Exception as e:
        st.error(f"Errore nella lettura del file dei dati: {e}")
        
    return punti_filtrati

# --- 4. COSTRUZIONE MAPPA FOLLIUM ---
m = folium.Map(
    location=st.session_state["mappa_centro"], 
    zoom_start=st.session_state["mappa_zoom"], 
    tiles='CartoDB voyager'
)

# Disegna i punti approvati dai toggle
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
    height=550, 
    key="mappa_roma_locale",
    returned_objects=["bounds", "center", "zoom"]
)

# Salva la posizione dello schermo ad ogni tocco
if output_mappa and output_mappa.get("bounds") and output_mappa.get("center"):
    st.session_state["mappa_centro"] = [output_mappa["center"]["lat"], output_mappa["center"]["lng"]]
    st.session_state["mappa_zoom"] = output_mappa["zoom"]

# --- 6. PULSANTE CON ANIMAZIONE ---
st.write("---")
if output_mappa and output_mappa.get("bounds"):
    bounds = output_mappa["bounds"]
    try:
        south = bounds["_southWest"]["lat"]
        west = bounds["_southWest"]["lng"]
        north = bounds["_northEast"]["lat"]
        east = bounds["_northEast"]["lng"]
    except KeyError:
        south, west = bounds[0][0], bounds[0][1]
        north, east = bounds[1][0], bounds[1][1]

    if st.button("🚀 Carica elementi in questa zona", use_container_width=True):
        with st.spinner("⏳ Elaborazione database locale..."):
            # Carica i veri dati dal file locale
            punti_zona = carica_punti_locali(north, south, east, west)
            st.session_state["punti_salvati"] = punti_zona
            
        if len(punti_zona) > 0:
            st.success(f"Fatto! Trovati {len(punti_zona)} elementi reali in questa vista.")
        else:
            st.info("Nessun elemento del database presente in questa inquadratura. Prova a spostarti verso il centro (es. Colosseo o Pantheon).")
        st.rerun()

if len(st.session_state["punti_salvati"]) > 0:
    st.caption(f"📍 Indicatori attivi sulla mappa: {len(st.session_state['punti_salvati'])}")
