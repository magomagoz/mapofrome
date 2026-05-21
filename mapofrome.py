import streamlit as st
import folium
import osmnx as ox
import streamlit.components.v1 as components

# Configurazione della pagina per sfruttare tutto lo schermo dell'iPad
st.set_page_config(layout="wide")

st.title("🗺️ Mappa Cartografica di Roma Centro")
st.write("Estrazione dati live da OpenStreetMap ottimizzata per iPad Pro.")

# Centro di Roma (Piazza Venezia) e raggio controllato per non sovraccaricare la RAM
centro_roma = (41.8955, 12.4823)
raggio_metri = st.select_slider("Seleziona il raggio di estrazione (metri):", options=[500, 1000, 1500, 2000, 3000], value=500)

@st.cache_data(show_spinner="Estrazione dati geospaziali in corso...")
def genera_mappa_roma(centro, raggio):
    # Inizializza la mappa Folium
    m = folium.Map(location=centro, zoom_start=14, tiles='CartoDB positron')
    
    try:
        # 1. Scarica e disegna le vie principali
        strade = ox.graph_from_point(centro, dist=raggio_metri, network_type='drive')
        _, edges = ox.graph_to_gdfs(strade)
        folium.GeoJson(edges[['geometry']], name="Vie", color="#444444", weight=1, opacity=0.6).add_to(m)
    except Exception as e:
        st.warning(f"Impossibile caricare alcune vie minori: {e}")

    try:
        # 2. Scarica i Punti di Interesse (Hotel 4/5 stelle, Chiese, Monumenti)
        tags = {'tourism': 'hotel', 'amenity': 'place_of_worship', 'historic': 'monument'}
        elementi = ox.features_from_point(centro, tags=tags, dist=raggio)
        
        for idx, row in elementi.iterrows():
            # Gestione pulita delle geometrie (punti o poligoni) per evitare crash su iPad
            centroide = row.geometry.centroid if hasattr(row.geometry, 'centroid') else row.geometry
            coords = [centroide.y, centroide.x]
            nome = row.get('name', 'Struttura senza nome')
            
            # Hotel di lusso (4 e 5 stelle)
            if row.get('tourism') == 'hotel' and row.get('stars') in ['4', '5']:
                folium.CircleMarker(location=coords, radius=5, color='gold', fill=True, fill_opacity=0.8, popup=f"🌟 Hotel: {nome}").add_to(m)
            
            # Chiese e Luoghi di Culto
            elif row.get('amenity') == 'place_of_worship':
                folium.CircleMarker(location=coords, radius=4, color='crimson', fill=True, fill_opacity=0.7, popup=f"⛪ Chiesa: {nome}").add_to(m)
                
            # Monumenti Storici
            elif row.get('historic') == 'monument':
                folium.CircleMarker(location=coords, radius=4, color='royalblue', fill=True, fill_opacity=0.7, popup=f"🏛️ Monumento: {nome}").add_to(m)
    except Exception as e:
        st.error(f"Errore nel caricamento dei punti di interesse: {e}")
        
    return m

# Genera l'oggetto mappa
mappa = genera_mappa_roma(centro_roma, raggio_metri)

# --- IL PASSAGGIO CRUCIALE PER STREAMLIT ---
# Estraiamo l'HTML e il codice JavaScript generato da Folium e lo passiamo al componente di Streamlit
mappa_html = mappa._repr_html_()

# Rendering responsive dentro Streamlit
components.html(mappa_html, height=600, scrolling=True)
