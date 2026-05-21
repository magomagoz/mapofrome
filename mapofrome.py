import streamlit as st
import folium
import osmnx as ox
from streamlit_folium import st_folium

# Sfrutta lo schermo dell'iPad Pro al massimo
st.set_page_config(layout="wide")

st.title("🗺️ Mappa Dinamica di Roma")
st.write("Spostati sulla mappa o fai zoom: i dati verranno scaricati automaticamente per l'area visibile.")

# Inizializza le coordinate di partenza (Piazza Venezia) se l'utente non ha ancora interagito
if "center" not in st.session_state:
    st.session_state["center"] = [41.8955, 12.4823]
if "zoom" not in st.session_state:
    st.session_state["zoom"] = 20

# Crea l'oggetto mappa base
m = folium.Map(
    location=st.session_state["center"], 
    zoom_start=st.session_state["zoom"], 
    tiles='CartoDB positron'
)

# Funzione per scaricare i dati nell'area visibile (Bounding Box) con cache per non saturare la RAM
@st.cache_data(show_spinner="Aggiornamento dati cartografici per l'area visibile...")
def scarica_dati_visibili(north, south, east, west):
    collezione_elementi = []
    strade_linee = None
    
    # 1. Scarica la rete stradale dell'area visibile
    try:
        strade = ox.graph_from_bbox(bbox=(north, south, east, west), network_type='drive')
        _, edges = ox.graph_to_gdfs(strade)
        strade_linee = edges[['geometry']]
    except Exception:
        pass # Se l'area è troppo piccola o priva di strade, ignora l'errore

    # 2. Scarica i punti di interesse
    try:
        tags = {'tourism': 'hotel', 'amenity': 'place_of_worship', 'historic': 'monument'}
        elementi = ox.features_from_bbox(bbox=(north, south, east, west), tags=tags)
        
        for idx, row in elementi.iterrows():
            centroide = row.geometry.centroid if hasattr(row.geometry, 'centroid') else row.geometry
            nome = row.get('name', 'Struttura senza nome')
            tipo = None
            
            if row.get('tourism') == 'hotel' and row.get('stars') in ['4', '5']:
                tipo = 'hotel'
            elif row.get('amenity') == 'place_of_worship':
                tipo = 'chiesa'
            elif row.get('historic') == 'monument':
                tipo = 'monumento'
                
            if tipo:
                collezione_elementi.append({
                    'coords': [centroide.y, centroide.x],
                    'nome': nome,
                    'tipo': tipo
                })
    except Exception:
        pass
        
    return strade_linee, collezione_elementi

# Mostra una mappa vuota al primissimo avvio per ottenere i confini dello schermo dello Streamlit
# Altrimenti usiamo i confini della mappa calcolati dall'interazione dell'utente
output_mappa = st_folium(m, width="100%", height=650, key="mappa_roma")

# Controlla se l'utente ha mosso la mappa o fatto zoom (otteniamo i confini dello schermo)
if output_mappa and output_mappa.get("bounds"):
    bounds = output_mappa["bounds"]
    south = bounds["_southWest"]["lat"]
    west = bounds["_southWest"]["lng"]
    north = bounds["_northEast"]["lat"]
    east = bounds["_northEast"]["lng"]
    
    # Salva la posizione attuale per evitare che la mappa si resetti al rinfresco della pagina
    st.session_state["center"] = [output_mappa["center"]["lat"], output_mappa["center"]["lng"]]
    st.session_state["zoom"] = output_mappa["zoom"]
    
    # Calcola l'area per evitare di bloccare il server se l'utente zooma troppo indietro su tutta Italia
    if abs(north - south) < 0.1 and abs(east - west) < 0.1:
        
        # Scarica strade e punti relativi solo a questo Bounding Box visibile
        strade_visibili, punti_visibili = scarica_dati_visibili(north, south, east, west)
        
        # Disegna le strade aggiornate sulla mappa corrente
        if strade_visibili is not None:
            folium.GeoJson(strade_visibili, color="#444444", weight=1.5, opacity=0.7).add_to(m)
            
        # Posiziona i marker aggiornati
        for p in punti_visibili:
            if p['tipo'] == 'hotel':
                folium.CircleMarker(location=p['coords'], radius=5, color='gold', fill=True, popup=p['nome']).add_to(m)
            elif p['tipo'] == 'chiesa':
                folium.CircleMarker(location=p['coords'], radius=4, color='crimson', fill=True, popup=p['nome']).add_to(m)
            elif p['tipo'] == 'monumento':
                folium.CircleMarker(location=p['coords'], radius=4, color='royalblue', fill=True, popup=p['nome']).add_to(m)
                
        # Forza un rapido aggiornamento della mappa a schermo con i nuovi dati inclusi
        st.rerun()
    else:
        st.info("🔍 Fai un po' di zoom in avanti per caricare i dettagli di questa zona.")
