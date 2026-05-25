import streamlit as st
import folium
from streamlit_folium import st_folium
import requests

# Sfrutta lo schermo dell'iPad Pro al massimo
st.set_page_config(layout="wide")

st.title("🗺️ Mappa di Roma - Versione Stabile")
st.write("Naviga liberamente sulla mappa. Usa gli interruttori per mostrare o nascondere i dati senza perdere la posizione.")

# --- 1. PANNELLO DI CONTROLLO ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    mostra_hotel = st.toggle("🌟 Hotel (4 e 5 Stelle)", value=True)
with col2:
    mostra_chiese = st.toggle("⛪ Chiese", value=True)
with col3:
    mostra_monumenti = st.toggle("🏛️ Monumenti", value=True)
with col4:
    if st.button("🔄 Forza Aggiornamento Dati"):
        st.cache_data.clear()
        st.rerun()

st.divider()

# --- 2. STATO DELLA SESSIONE (Previene i reset della mappa) ---
# Usiamo coordinate ampie di partenza per Roma Centro
if "center" not in st.session_state:
    st.session_state["center"] = [41.8955, 12.4823]
if "zoom" not in st.session_state:
    st.session_state["zoom"] = 15
if "bounds" not in st.session_state:
    st.session_state["bounds"] = {"north": 41.905, "south": 41.885, "east": 12.495, "west": 12.475}

# --- 3. ESTRAZIONE DATI OTTIMIZZATA (Risolve Errore 406) ---
@st.cache_data(show_spinner="Recupero dati da OpenStreetMap...")
def scarica_punti_sicuri(north, south, east, west):
    punti = []
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    overpass_query = f"""
    [out:json][timeout:30];
    (
      nwr["tourism"="hotel"]["stars"~"4|5"]({south},{west},{north},{east});
      nwr["amenity"="place_of_worship"]({south},{west},{north},{east});
      nwr["historic"="monument"]({south},{west},{north},{east});
    );
    out center;
    """
    
    # AGGIUNTA FONDAMENTALE: Definiamo l'header per evitare il blocco 406 dei server
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) StreamlitRomeMapApp/1.0'
    }
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, headers=headers)
        
        if response.status_code == 429:
            st.warning("⚠️ Troppe richieste inviate al server. Attendi qualche istante.")
            return []
        elif response.status_code != 200:
            st.error(f"❌ Errore di connessione Overpass: Codice {response.status_code}")
            return []
            
        data = response.json()
        
        for element in data.get('elements', []):
            lat = element.get('lat') or element.get('center', {}).get('lat')
            lon = element.get('lon') or element.get('center', {}).get('lon')
            
            if not lat or not lon:
                continue
                
            tags = element.get('tags', {})
            nome = tags.get('name', 'Struttura senza nome')
            
            if tags.get('tourism') == 'hotel':
                tipo = 'hotel'
            elif tags.get('amenity') == 'place_of_worship':
                tipo = 'chiesa'
            else:
                tipo = 'monumento'
                
            punti.append({'coords': [float(lat), float(lon)], 'nome': nome, 'tipo': tipo})
            
    except Exception as e:
        st.error(f"❌ Errore generico: {e}")
        
    return punti

# --- 4. COSTRUZIONE DELLA MAPPA CON I DATI DELLA SESSIONE ---
# Creiamo la mappa inserendo l'ultima posizione valida salvata in memoria
m = folium.Map(
    location=st.session_state["center"], 
    zoom_start=st.session_state["zoom"], 
    tiles='CartoDB voyager'
)

b = st.session_state["bounds"]

# Estraiamo i dati solo per l'area attualmente registrata nella sessione
if abs(b["north"] - b["south"]) < 0.08:
    lista_punti = scarica_punti_sicuri(b["north"], b["south"], b["east"], b["west"])
    
    st.caption(f"📍 Elementi rilevati nella zona: {len(lista_punti)}")
    
    for p in lista_punti:
        if p['tipo'] == 'hotel' and mostra_hotel:
            folium.CircleMarker(location=p['coords'], radius=6, color='#DAA520', fill=True, fill_color='#FFD700', fill_opacity=0.9, tooltip=p['nome']).add_to(m)
        elif p['tipo'] == 'chiesa' and mostra_chiese:
            folium.CircleMarker(location=p['coords'], radius=5, color='#8B0000', fill=True, fill_color='#DC143C', fill_opacity=0.8, tooltip=p['nome']).add_to(m)
        elif p['tipo'] == 'monumento' and mostra_monumenti:
            folium.CircleMarker(location=p['coords'], radius=5, color='#00008B', fill=True, fill_color='#1E90FF', fill_opacity=0.8, tooltip=p['nome']).add_to(m)
else:
    st.info("🔍 Zoomando più da vicino verranno scaricati automaticamente i punti d'interesse.")

# --- 5. VISUALIZZAZIONE DELLA MAPPA ---
# st_folium ora gestisce l'interfaccia in modo asincrono senza generare loop continui
output_mappa = st_folium(
    m, 
    width="100%", 
    height=600, 
    key="mappa_roma_stabile",
    returned_objects=["bounds", "center", "zoom"] # Chiediamo solo i dati strettamente necessari
)

# --- 6. AGGIORNAMENTO TRACCIATO DELLA SESSIONE ---
# Raccogliamo la nuova posizione dell'utente SOLO se si ferma o cambia area, evitando il loop di st.rerun()
if output_mappa and output_mappa.get("bounds") and output_mappa.get("center"):
    nuovi_bounds = output_mappa["bounds"]
    n_north = nuovi_bounds["_northEast"]["lat"]
    n_south = nuovi_bounds["_southWest"]["lat"]
    n_east = nuovi_bounds["_northEast"]["lng"]
    n_west = nuovi_bounds["_southWest"]["lng"]
    
    # Controlliamo se c'è stato uno spostamento reale e significativo prima di aggiornare lo stato
    vecchio_b = st.session_state["bounds"]
    scostamento = abs(n_north - vecchio_b["north"]) + abs(n_south - vecchio_b["south"])
    
    if scostamento > 0.002: # Tolleranza per evitare i micro-aggiornamenti durante lo zoom
        st.session_state["bounds"] = {"north": n_north, "south": n_south, "east": n_east, "west": n_west}
        st.session_state["center"] = [output_mappa["center"]["lat"], output_mappa["center"]["lng"]]
        st.session_state["zoom"] = output_mappa["zoom"]
        st.rerun()
