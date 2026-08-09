import streamlit as st
import folium
from folium import plugins # <-- NUOVO IMPORT per i plugin di Folium
from streamlit_folium import st_folium
import json
import os

# Configurazione schermo intero
st.set_page_config(layout="wide")

st.image("banner.png")
st.title("🗺️ Mappa di Roma per NCC")
st.write("Spostati sulla mappa o usa il **Mirino GPS** in alto a sinistra per trovare la tua posizione, poi carica i punti.")

# --- 1. CONFIGURAZIONE TOGGLE CON COLORI ---
col1, col2, col3 = st.columns(3)
with col1:
    mostra_hotel = st.toggle("🟡 :orange[**Hotel (4/5 Stelle)**]", value=True)
with col2:
    mostra_chiese = st.toggle("🔴 :red[**Chiese**]", value=True)
with col3:
    mostra_monumenti = st.toggle("🔵 :blue[**Monumenti**]", value=True)

st.divider()

# --- 2. STATO DELLA SESSIONE ---
if "punti_salvati" not in st.session_state:
    st.session_state["punti_salvati"] = []
# Memorizziamo la posizione per non perdere il focus dopo aver usato il GPS
if "mappa_centro" not in st.session_state:
    st.session_state["mappa_centro"] = [41.8955, 12.4823]
if "mappa_zoom" not in st.session_state:
    st.session_state["mappa_zoom"] = 14

# --- 3. LETTURA DATI LOCALE ---
def carica_punti_locali(north, south, east, west):
    punti_filtrati = []
    file_path = "punti_roma.geojson" # Assicurati di usare il nome del tuo file più corposo
    
    if not os.path.exists(file_path):
        st.error(f"File {file_path} non trovato su GitHub! Controlla di averlo creato.")
        return []
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        for feature in data.get("features", []):
            coords = feature["geometry"]["coordinates"] 
            lon, lat = coords[0], coords[1]
            props = feature["properties"]
            
            if south <= lat <= north and west <= lon <= east:
                punti_filtrati.append({'coords': [lat, lon], 'nome': props["nome"], 'tipo': props["tipo"]})
    except Exception as e:
        st.error(f"Errore nella lettura del file: {e}")
        
    return punti_filtrati

# --- 4. COSTRUZIONE MAPPA BASE CON GPS ---
# La mappa ora si avvia leggendo le coordinate memorizzate nella sessione
m = folium.Map(
    location=st.session_state["mappa_centro"], 
    zoom_start=st.session_state["mappa_zoom"], 
    tiles='CartoDB voyager'
)

# IL NUOVO PULSANTE GPS (LocateControl)
plugins.LocateControl(
    position="topleft",
    drawCircle=True, # Disegna un cerchio blu attorno alla tua posizione
    flyTo=True,      # Animazione fluida verso il punto
    strings={"title": "Centra sulla mia posizione GPS", "popup": "Ti trovi qui!"}
).add_to(m)

# Creiamo il foglio trasparente per i marker
livello_punti = folium.FeatureGroup(name="Punti NCC")

# Disegniamo i punti SOLO sul foglio trasparente
for p in st.session_state["punti_salvati"]:
    if p['tipo'] == 'hotel' and mostra_hotel:
        folium.CircleMarker(location=p['coords'], radius=8, color='#DAA520', fill=True, fill_color='#FFD700', fill_opacity=0.9, tooltip=p['nome']).add_to(livello_punti)
    elif p['tipo'] == 'chiesa' and mostra_chiese:
        folium.CircleMarker(location=p['coords'], radius=7, color='#8B0000', fill=True, fill_color='#DC143C', fill_opacity=0.8, tooltip=p['nome']).add_to(livello_punti)
    elif p['tipo'] == 'monumento' and mostra_monumenti:
        folium.CircleMarker(location=p['coords'], radius=7, color='#00008B', fill=True, fill_color='#1E90FF', fill_opacity=0.8, tooltip=p['nome']).add_to(livello_punti)

# --- 5. VISUALIZZAZIONE MAPPA DINAMICA ---
output_mappa = st_folium(
    m, 
    feature_group_to_add=livello_punti,
    use_container_width=True, 
    height=600, 
    key="mappa_roma_fluida",
    # Abbiamo aggiunto center e zoom per poter salvare l'ultima vista scelta dall'utente
    returned_objects=["bounds", "center", "zoom"] 
)

# Registra la posizione aggiornata non appena muovi la mappa o usi il GPS
if output_mappa and output_mappa.get("center"):
    st.session_state["mappa_centro"] = [output_mappa["center"]["lat"], output_mappa["center"]["lng"]]
    st.session_state["mappa_zoom"] = output_mappa["zoom"]

# --- 6. PULSANTE E LOGICA ---
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
        with st.spinner("⏳ Estrazione dati per quest'area..."):
            punti_zona = carica_punti_locali(north, south, east, west)
            st.session_state["punti_salvati"] = punti_zona
            
        if len(punti_zona) > 0:
            st.success(f"Fatto! Trovati {len(punti_zona)} elementi in quest'area.")
        else:
            st.info("Nessun elemento presente in questa inquadratura. Spostati o zooma indietro.")
        st.rerun()

if len(st.session_state["punti_salvati"]) > 0:
    st.caption(f"📍 Indicatori attivi sulla mappa: {len(st.session_state['punti_salvati'])}")
