import streamlit as st
import folium
from streamlit_folium import st_folium
import requests

# Sfrutta al massimo lo schermo dell'iPad Pro
st.set_page_config(layout="wide")

st.title("🗺️ Mappa di Roma (Modalità Touch Stabile)")
st.write("Spostati e zooma liberamente sulla mappa. Quando hai scelto la zona, premi **'Carica elementi in questa zona'**.")

# --- 1. CONFIGURAZIONE TOGGLE ---
col1, col2, col3 = st.columns(3)
with col1:
    mostra_hotel = st.toggle("🌟 Hotel (4/5 Stelle)", value=True)
with col2:
    mostra_chiese = st.toggle("⛪ Chiese", value=True)
with col3:
    mostra_monumenti = st.toggle("🏛️ Monumenti", value=True)

st.divider()

# --- 2. STATO DELLA SESSIONE PER I PUNTI ---
if "punti_salvati" not in st.session_state:
    st.session_state["punti_salvati"] = []
if "mappa_centro" not in st.session_state:
    st.session_state["mappa_centro"] = [41.8955, 12.4823]
if "mappa_zoom" not in st.session_state:
    st.session_state["mappa_zoom"] = 15

# --- 3. FUNZIONE DI SCARICAMENTO PROTOCOLLO SICURO ---
def scarica_dati_api(north, south, east, west):
    punti_trovati = []
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    overpass_query = f"""
    [out:json][timeout:20];
    (
      nwr["tourism"="hotel"]["stars"~"4|5"]({south},{west},{north},{east});
      nwr["amenity"="place_of_worship"]({south},{west},{north},{east});
      nwr["historic"="monument"]({south},{west},{north},{east});
    );
    out center;
    """
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) StreamlitAppRoma/2.0'
    }
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for element in data.get('elements', []):
                lat = element.get('lat') or element.get('center', {}).get('lat')
                lon = element.get('lon') or element.get('center', {}).get('lon')
                if lat and lon:
                    tags = element.get('tags', {})
                    nome = tags.get('name', 'Struttura senza nome')
                    
                    if tags.get('tourism') == 'hotel':
                        tipo = 'hotel'
                    elif tags.get('amenity') == 'place_of_worship':
                        tipo = 'chiesa'
                    else:
                        tipo = 'monumento'
                        
                    punti_trovati.append({'coords': [float(lat), float(lon)], 'nome': nome, 'tipo': tipo})
        else:
            st.error(f"Il server cartografico ha risposto con codice: {response.status_code}")
    except Exception as e:
        st.error(f"Errore di rete: {e}")
        
    return punti_trovati

# --- 4. COSTRUZIONE DELLA MAPPA FOLLIUM ---
m = folium.Map(
    location=st.session_state["mappa_centro"], 
    zoom_start=st.session_state["mappa_zoom"], 
    tiles='CartoDB voyager'
)

# Disegna sulla mappa i punti attualmente salvati in memoria (se abilitati dai toggle)
for p in st.session_state["punti_salvati"]:
    if p['tipo'] == 'hotel' and mostra_hotel:
        folium.CircleMarker(location=p['coords'], radius=6, color='#DAA520', fill=True, fill_color='#FFD700', fill_opacity=0.9, tooltip=p['nome']).add_to(m)
    elif p['tipo'] == 'chiesa' and mostra_chiese:
        folium.CircleMarker(location=p['coords'], radius=5, color='#8B0000', fill=True, fill_color='#DC143C', fill_opacity=0.8, tooltip=p['nome']).add_to(m)
    elif p['tipo'] == 'monumento' and mostra_monumenti:
        folium.CircleMarker(location=p['coords'], radius=5, color='#00008B', fill=True, fill_color='#1E90FF', fill_opacity=0.8, tooltip=p['nome']).add_to(m)

# --- 5. INTERFACCIA MAPPA DI STREAMLIT ---
# Chiediamo solo i bounds per sapere dove si trova l'utente quando premerà il bottone
output_mappa = st_folium(
    m, 
    width="100%", 
    height=600, 
    key="mappa_roma_stabile_v2",
    returned_objects=["bounds", "center", "zoom"]
)

# Memorizziamo la posizione in tempo reale nello stato temporaneo (SENZA forzare il rerun)
if output_mappa and output_mappa.get("bounds"):
    st.session_state["mappa_centro"] = [output_mappa["center"]["lat"], output_mappa["center"]["lng"]]
    st.session_state["mappa_zoom"] = output_mappa["zoom"]
    
    # --- 6. IL BOTTONE DI ATTIVAZIONE ---
    # Posizionato sotto la mappa per permettere il caricamento on-demand
    st.write("---")
    if st.button("🚀 Carica elementi in questa zona", use_container_width=True):
        bounds = output_mappa["bounds"]
        south = bounds["_southWest"]["lat"]
        west = bounds["_southWest"]["lng"]
        north = bounds["_northEast"]["lat"]
        east = bounds["_northEast"]["lng"]
        
        # Esegui il download e salva i dati nella sessione
        punti_scaricati = scarica_dati_api(north, south, east, west)
        st.session_state["punti_salvati"] = punti_scaricati
        
        # Mostra un riscontro all'utente e aggiorna la mappa graficamente
        st.success(f"Caricamento completato! Trovati {len(punti_scaricati)} elementi in questa vista.")
        st.rerun()

# Informazioni di aiuto
if len(st.session_state["punti_salvati"]) > 0:
    st.caption(f"📍 Attualmente visualizzati: {len(st.session_state['punti_salvati'])} marker totali.")
