import streamlit as st
import folium
from streamlit_folium import st_folium
import requests

# Sfrutta lo schermo dell'iPad Pro al massimo
st.set_page_config(layout="wide")

st.title("🗺️ Mappa Rapida di Roma")
st.write("Versione ottimizzata: spostati e zooma. Le strade si caricano istantaneamente, i punti seguono lo zoom.")

# Inizializza lo stato della mappa
if "center" not in st.session_state:
    st.session_state["center"] = [41.8955, 12.4823]
if "zoom" not in st.session_state:
    st.session_state["zoom"] = 18

# Creiamo la mappa base. Usiamo il tile 'OpenStreetMap' o 'CartoDB voyager' 
# che mostra già TUTTE le strade, i vicoli e i nomi delle vie in tempo reale e gratis.
m = folium.Map(
    location=st.session_state["center"], 
    zoom_start=st.session_state["zoom"], 
    tiles='CartoDB voyager'
)

# Funzione turbo per scaricare SOLO i punti tramite richiesta HTTP diretta (senza OSMnx)
@st.cache_data(show_spinner="Recupero hotel, chiese e monumenti in questa zona...")
def scarica_punti_rapidi(north, south, east, west):
    punti = []
    
    # Query Overpass specifica per prendere solo ciò che serve nell'area visibile
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json][timeout:10];
    (
      node["tourism"="hotel"]["stars"~"4|5"]({south},{west},{north},{east});
      node["amenity"="place_of_worship"]({south},{west},{north},{east});
      node["historic"="monument"]({south},{west},{north},{east});
    );
    out body;
    """
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query})
        data = response.json()
        
        for element in data.get('elements', []):
            lat = element.get('lat')
            lon = element.get('lon')
            tags = element.get('tags', {})
            nome = tags.get('name', 'Senza nome')
            
            # Categorizzazione immediata
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

# Mostra la mappa sull'iPad
output_mappa = st_folium(m, width="100%", height=650, key="mappa_roma_veloce")

# Se l'utente si sposta, aggiorna i punti
if output_mappa and output_mappa.get("bounds"):
    bounds = output_mappa["bounds"]
    south = bounds["_southWest"]["lat"]
    west = bounds["_southWest"]["lng"]
    north = bounds["_northEast"]["lat"]
    east = bounds["_northEast"]["lng"]
    
    # Salva la posizione per evitare rinfreschi molesti
    st.session_state["center"] = [output_mappa["center"]["lat"], output_mappa["center"]["lng"]]
    st.session_state["zoom"] = output_mappa["zoom"]
    
    # Limite di sicurezza per lo zoom indietro
    if abs(north - south) < 0.05:
        punti_visibili = scarica_punti_rapidi(north, south, east, west)
        
        # Disegna i punti sulla mappa
        for p in punti_visibili:
            if p['tipo'] == 'hotel':
                folium.CircleMarker(location=p['coords'], radius=6, color='#FFD700', fill=True, fill_color='#FFD700', fill_opacity=0.9, popup=p['nome']).add_to(m)
            elif p['tipo'] == 'chiesa':
                folium.CircleMarker(location=p['coords'], radius=5, color='#DC143C', fill=True, fill_color='#DC143C', fill_opacity=0.8, popup=p['nome']).add_to(m)
            elif p['tipo'] == 'monumento':
                folium.CircleMarker(location=p['coords'], radius=5, color='#1E90FF', fill=True, fill_color='#1E90FF', fill_opacity=0.8, popup=p['nome']).add_to(m)
        
        # Aggiorna l'app con i nuovi marker
        st.rerun()
    else:
        st.info("🔍 Zoomando più da vicino vedrai comparire gli hotel, le chiese e i monumenti di quella zona.")
