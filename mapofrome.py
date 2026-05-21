import streamlit as st
import folium
from streamlit_folium import st_folium
import requests

st.set_page_config(layout="wide")

st.title("🗺️ Mappa Cartografica di Roma (Diagnostica)")
st.write("Vediamo esattamente cosa sta succedendo dietro le quinte.")

# --- 1. PANNELLO DI CONTROLLO CON TASTO RESET ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    mostra_hotel = st.toggle("🌟 Hotel (4 e 5 Stelle)", value=True)
with col2:
    mostra_chiese = st.toggle("⛪ Chiese", value=True)
with col3:
    mostra_monumenti = st.toggle("🏛️ Monumenti", value=True)
with col4:
    # Questo tasto è fondamentale per forzare il server a riscaricare i dati
    if st.button("🔄 Svuota Cache e Ricarica"):
        st.cache_data.clear()
        st.rerun()

st.divider()

# --- 2. GESTIONE DELLA POSIZIONE INIZIALE ---
if "bounds" not in st.session_state:
    st.session_state["bounds"] = {"north": 41.905, "south": 41.885, "east": 12.495, "west": 12.475}
if "center" not in st.session_state:
    st.session_state["center"] = [41.8955, 12.4823]
if "zoom" not in st.session_state:
    st.session_state["zoom"] = 15

# --- 3. ESTRAZIONE DATI CON MESSAGGI DI ERRORE ESPLICITI ---
@st.cache_data(show_spinner="Download dati da OpenStreetMap...")
def scarica_punti_rapidi(north, south, east, west):
    punti = []
    # IMPORTANTE: Ora usiamo HTTPS per non essere bloccati dal cloud
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    overpass_query = f"""
    [out:json][timeout:25];
    (
      nwr["tourism"="hotel"]["stars"~"4|5"]({south},{west},{north},{east});
      nwr["amenity"="place_of_worship"]({south},{west},{north},{east});
      nwr["historic"="monument"]({south},{west},{north},{east});
    );
    out center;
    """
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query})
        
        # Se il server Overpass rifiuta la connessione, ora ce lo dirà
        if response.status_code != 200:
            st.error(f"❌ Errore API Overpass (Codice {response.status_code}): Riprova tra poco.")
            return []
            
        data = response.json()
        
        for element in data.get('elements', []):
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
                
            # Forziamo la conversione in float (numero decimale) per sicurezza di Folium
            punti.append({'coords': [float(lat), float(lon)], 'nome': nome, 'tipo': tipo})
            
    except Exception as e:
        st.error(f"❌ Errore di esecuzione: {e}")
        
    return punti

# --- 4. PREPARAZIONE DELLA MAPPA ---
b = st.session_state["bounds"]
m = folium.Map(location=st.session_state["center"], zoom_start=st.session_state["zoom"], tiles='CartoDB voyager')

if abs(b["north"] - b["south"]) < 0.08:
    punti = scarica_punti_rapidi(b["north"], b["south"], b["east"], b["west"])
    
    # Questo messaggio ci farà capire se il problema è la rete (0 punti) o il rendering
    st.caption(f"📍 Diagnostica: Trovati {len(punti)} elementi cartografici in quest'area visibile.")
    
    for p in punti:
        if p['tipo'] == 'hotel' and mostra_hotel:
            folium.CircleMarker(location=p['coords'], radius=6, color='#DAA520', fill=True, fill_opacity=0.9, tooltip=p['nome']).add_to(m)
        elif p['tipo'] == 'chiesa' and mostra_chiese:
            folium.CircleMarker(location=p['coords'], radius=5, color='#8B0000', fill=True, fill_opacity=0.8, tooltip=p['nome']).add_to(m)
        elif p['tipo'] == 'monumento' and mostra_monumenti:
            folium.CircleMarker(location=p['coords'], radius=5, color='#00008B', fill=True, fill_opacity=0.8, tooltip=p['nome']).add_to(m)
else:
    st.info("🔍 L'area visibile è troppo vasta. Fai zoom per far comparire i punti d'interesse!")

# --- 5. MOSTRA LA MAPPA A SCHERMO ---
output_mappa = st_folium(m, width="100%", height=650, key="mappa_roma_diagnostica")

# --- 6. AGGIORNAMENTO DINAMICO SULLO SPOSTAMENTO ---
if output_mappa and output_mappa.get("bounds"):
    nuovi_bounds = output_mappa["bounds"]
    n_north = nuovi_bounds["_northEast"]["lat"]
    n_south = nuovi_bounds["_southWest"]["lat"]
    n_east = nuovi_bounds["_northEast"]["lng"]
    n_west = nuovi_bounds["_southWest"]["lng"]
    
    if abs(n_north - b["north"]) > 0.001 or abs(n_south - b["south"]) > 0.001:
        st.session_state["bounds"] = {"north": n_north, "south": n_south, "east": n_east, "west": n_west}
        st.session_state["center"] = [output_mappa["center"]["lat"], output_mappa["center"]["lng"]]
        st.session_state["zoom"] = output_mappa.get("zoom", 15)
        st.rerun()
