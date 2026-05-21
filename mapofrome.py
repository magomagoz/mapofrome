import streamlit as st
import folium
from streamlit_folium import st_folium
import requests

# Ottimizzazione per lo schermo intero
st.set_page_config(layout="wide")

st.title("🗺️ Mappa Cartografica di Roma")
st.write("Naviga sulla mappa e usa gli interruttori per mostrare o nascondere i livelli.")

# --- 1. PANNELLO DI CONTROLLO (I PULSANTI) ---
col1, col2, col3 = st.columns(3)
with col1:
    mostra_hotel = st.toggle("🌟 Hotel (4 e 5 Stelle)", value=True)
with col2:
    mostra_chiese = st.toggle("⛪ Chiese", value=True)
with col3:
    mostra_monumenti = st.toggle("🏛️ Monumenti storici", value=True)

st.divider() # Linea di separazione visiva

# --- 2. GESTIONE DELLA POSIZIONE INIZIALE ---
# Impostiamo Piazza Venezia come punto di partenza e un'area visibile di default
if "bounds" not in st.session_state:
    st.session_state["bounds"] = {"north": 41.905, "south": 41.885, "east": 12.495, "west": 12.475}
if "center" not in st.session_state:
    st.session_state["center"] = [41.8955, 12.4823]
if "zoom" not in st.session_state:
    st.session_state["zoom"] = 15

# --- 3. ESTRAZIONE DATI POTENZIATA (Include Aree e Poligoni) ---
@st.cache_data(show_spinner="Download dati da OpenStreetMap...")
def scarica_punti_rapidi(north, south, east, west):
    punti = []
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # Usiamo 'nwr' (node, way, relation) per prendere anche gli edifici grandi e 'out center' per averne il centro esatto
    overpass_query = f"""
    [out:json][timeout:15];
    (
      nwr["tourism"="hotel"]["stars"~"4|5"]({south},{west},{north},{east});
      nwr["amenity"="place_of_worship"]({south},{west},{north},{east});
      nwr["historic"="monument"]({south},{west},{north},{east});
    );
    out center;
    """
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query})
        data = response.json()
        
        for element in data.get('elements', []):
            # Se è un punto (node) usa lat/lon dirette, se è un'area usa il 'center' calcolato dal server
            lat = element.get('lat') or element.get('center', {}).get('lat')
            lon = element.get('lon') or element.get('center', {}).get('lon')
            
            if not lat or not lon:
                continue
                
            tags = element.get('tags', {})
            nome = tags.get('name', 'Senza nome')
            
            if tags.get('tourism') == 'hotel':
                tipo = 'hotel'
            elif tags.get('amenity') == 'place_of_worship':
                tipo = 'chiesa'
            else:
                tipo = 'monumento'
                
            punti.append({'coords': [lat, lon], 'nome': nome, 'tipo': tipo})
    except Exception as e:
        pass
        
    return punti

# --- 4. PREPARAZIONE DELLA MAPPA (Prima del Rendering) ---
b = st.session_state["bounds"]

# Creiamo la mappa base
m = folium.Map(location=st.session_state["center"], zoom_start=st.session_state["zoom"], tiles='CartoDB voyager')

# Carichiamo i dati solo se non facciamo troppo zoom indietro (per non sovraccaricare il sistema)
if abs(b["north"] - b["south"]) < 0.08:
    punti = scarica_punti_rapidi(b["north"], b["south"], b["east"], b["west"])
    
    # Aggiungiamo i marker SOLO SE il rispettivo pulsante (toggle) è acceso
    for p in punti:
        if p['tipo'] == 'hotel' and mostra_hotel:
            folium.CircleMarker(location=p['coords'], radius=7, color='#DAA520', fill=True, fill_color='#FFD700', fill_opacity=0.9, tooltip=p['nome']).add_to(m)
        elif p['tipo'] == 'chiesa' and mostra_chiese:
            folium.CircleMarker(location=p['coords'], radius=5, color='#8B0000', fill=True, fill_color='#DC143C', fill_opacity=0.8, tooltip=p['nome']).add_to(m)
        elif p['tipo'] == 'monumento' and mostra_monumenti:
            folium.CircleMarker(location=p['coords'], radius=5, color='#00008B', fill=True, fill_color='#1E90FF', fill_opacity=0.8, tooltip=p['nome']).add_to(m)
else:
    st.info("🔍 L'area visibile è troppo vasta. Fai zoom per far comparire i punti d'interesse!")

# --- 5. MOSTRA LA MAPPA A SCHERMO ---
output_mappa = st_folium(m, width="100%", height=650, key="mappa_roma_definitiva")

# --- 6. AGGIORNAMENTO DINAMICO SULLO SPOSTAMENTO ---
if output_mappa and output_mappa.get("bounds"):
    nuovi_bounds = output_mappa["bounds"]
    n_north = nuovi_bounds["_northEast"]["lat"]
    n_south = nuovi_bounds["_southWest"]["lat"]
    n_east = nuovi_bounds["_northEast"]["lng"]
    n_west = nuovi_bounds["_southWest"]["lng"]
    
    # Aggiorna la pagina SOLO se la mappa viene spostata significativamente (evita loop di ricaricamento fastidiosi)
    if abs(n_north - b["north"]) > 0.001 or abs(n_south - b["south"]) > 0.001:
        st.session_state["bounds"] = {"north": n_north, "south": n_south, "east": n_east, "west": n_west}
        st.session_state["center"] = [output_mappa["center"]["lat"], output_mappa["center"]["lng"]]
        st.session_state["zoom"] = output_mappa.get("zoom", 15)
        st.rerun()
