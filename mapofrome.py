import streamlit as st
import folium
from streamlit_folium import st_folium
import requests

# Configurazione schermo intero per iPad Pro
st.set_page_config(layout="wide")

st.title("🗺️ Mappa di Roma (Caricamento Dati Ottimizzato)")
st.write("Muoviti sulla mappa. Quando hai scelto l'area, premi il pulsante in fondo per visualizzare i punti.")

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

# --- 3. ESTRAZIONE DATI POTENZIATA E SU SERVER ALTERNATIVO ---
def scarica_dati_api(north, south, east, west):
    punti_trovati = []
    
    # CAMBIO SERVER: Usiamo il mirror di Kumi Systems, molto più stabile per app cloud
    overpass_url = "https://overpass.kumi.systems/api/interpreter"
    
    # Query semplificata per evitare timeout o blocchi del server
    overpass_query = f"""
    [out:json][timeout:30];
    (
      nwr["tourism"="hotel"]({south},{west},{north},{east});
      nwr["amenity"="place_of_worship"]({south},{west},{north},{east});
      nwr["historic"="monument"]({south},{west},{north},{east});
    );
    out center;
    """
    
    # Header simulato per bypassare completamente i blocchi di sicurezza
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, headers=headers, timeout=25)
        
        if response.status_code == 200:
            data = response.json()
            elementi = data.get('elements', [])
            
            for element in elementi:
                # Estrazione flessibile delle coordinate (punti o aree)
                lat = element.get('lat') or element.get('center', {}).get('lat')
                lon = element.get('lon') or element.get('center', {}).get('lon')
                
                if lat and lon:
                    tags = element.get('tags', {})
                    nome = tags.get('name') or tags.get('operator') or 'Struttura senza nome'
                    
                    # Logica di classificazione
                    if tags.get('tourism') == 'hotel':
                        # Filtro stelle flessibile: se non specificato lo teniamo per sicurezza, altrimenti verifichiamo 4 o 5
                        stelle = tags.get('stars', '')
                        if stelle in ['', '4', '5', '4 stars', '5 stars']:
                            tipo = 'hotel'
                        else:
                            continue
                    elif tags.get('amenity') == 'place_of_worship':
                        tipo = 'chiesa'
                    else:
                        tipo = 'monumento'
                        
                    punti_trovati.append({
                        'coords': [float(lat), float(lon)], 
                        'nome': str(nome), 
                        'tipo': tipo
                    })
        else:
            st.error(f"⚠️ Errore Server (Codice {response.status_code}). Provo ad usare il server di riserva...")
            # Server di riserva in caso di blackout del primo
            overpass_url_backup = "https://overpass-api.de/api/interpreter"
            response = requests.get(overpass_url_backup, params={'data': overpass_query}, headers=headers, timeout=25)
            if response.status_code == 200:
                # Ripeti la lettura per il backup
                data = response.json()
                for element in data.get('elements', []):
                    lat = element.get('lat') or element.get('center', {}).get('lat')
                    lon = element.get('lon') or element.get('center', {}).get('lon')
                    if lat and lon:
                        tags = element.get('tags', {})
                        nome = tags.get('name') or 'Struttura senza nome'
                        tipo = 'hotel' if tags.get('tourism') == 'hotel' else ('chiesa' if tags.get('amenity') == 'place_of_worship' else 'monumento')
                        punti_trovati.append({'coords': [float(lat), float(lon)], 'nome': str(nome), 'tipo': tipo})

    except Exception as e:
        st.error(f"❌ Impossibile raggiungere i server cartografici: {e}")
        
    return punti_trovati

# --- 4. COSTRUZIONE MAPPA ---
m = folium.Map(
    location=st.session_state["mappa_centro"], 
    zoom_start=st.session_state["mappa_zoom"], 
    tiles='CartoDB voyager'
)

# Visualizza i marker (se abilitati dai toggle)
for p in st.session_state["punti_salvati"]:
    if p['tipo'] == 'hotel' and mostra_hotel:
        folium.CircleMarker(location=p['coords'], radius=6, color='#DAA520', fill=True, fill_color='#FFD700', fill_opacity=0.9, tooltip=p['nome']).add_to(m)
    elif p['tipo'] == 'chiesa' and mostra_chiese:
        folium.CircleMarker(location=p['coords'], radius=5, color='#8B0000', fill=True, fill_color='#DC143C', fill_opacity=0.8, tooltip=p['nome']).add_to(m)
    elif p['tipo'] == 'monumento' and mostra_monumenti:
        folium.CircleMarker(location=p['coords'], radius=5, color='#00008B', fill=True, fill_color='#1E90FF', fill_opacity=0.8, tooltip=p['nome']).add_to(m)

# --- 5. AGGIORNAMENTO COMPONENTE STREAMLIT ---
output_mappa = st_folium(
    m, 
    width="100%", 
    height=550, 
    key="mappa_roma_stabile_v3",
    returned_objects=["bounds", "center", "zoom"]
)

# Salva la posizione corrente dell'iPad ad ogni spostamento
if output_mappa and output_mappa.get("bounds") and output_mappa.get("center"):
    st.session_state["mappa_centro"] = [output_mappa["center"]["lat"], output_mappa["center"]["lng"]]
    st.session_state["mappa_zoom"] = output_mappa["zoom"]
    
    # --- 6. PULSANTE ON-DEMAND ---
    st.write("---")
    if st.button("🚀 Carica elementi in questa zona", use_container_width=True):
        bounds = output_mappa["bounds"]
        south = bounds["_southWest"]["lat"]
        west = bounds["_southWest"]["lng"]
        north = bounds["_northEast"]["lat"]
        east = bounds["_northEast"]["lng"]
        
        # Chiamata API e salvataggio dei punti
        punti_scaricati = scarica_dati_api(north, south, east, west)
        st.session_state["punti_salvati"] = punti_scaricati
        
        if len(punti_scaricati) > 0:
            st.success(f"✅ Caricamento completato! Trovati {len(punti_scaricati)} elementi in questa zona.")
        else:
            st.info("ℹ️ Nessun elemento trovato in questa specifica area visibile. Prova a spostarti o a zoomare indietro.")
        st.rerun()

if len(st.session_state["punti_salvati"]) > 0:
    st.caption(f"📍 Indicatori pronti sulla mappa: {len(st.session_state['punti_salvati'])}")
