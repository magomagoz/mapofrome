import folium
import osmnx as ox
import webbrowser
import os

# 1. Centro di Roma (Piazza Venezia) e raggio di tolleranza (4 km coprono il centro storico)
centro_roma = (41.8955, 12.4823)
raggio_metri = 4000 

print("Inizializzazione della mappa...")
mappa_roma = folium.Map(location=centro_roma, zoom_start=14, tiles='CartoDB positron')

# 2. Scarichiamo la rete stradale limitata al raggio impostato
print("Scaricamento delle strade del centro (richiede un attimo)...")
try:
    strade = ox.graph_from_point(centro_roma, dist=raggio_metri, network_type='drive')
    # Convertiamo in GeoDataFrame per folium
    _, edges = ox.graph_to_gdfs(strade)
    folium.GeoJson(edges[['geometry']], name="Vie di Roma", color="#555555", weight=1, opacity=0.6).add_to(mappa_roma)
except Exception as e:
    print(f"Nota sulle strade: {e}. Procedo comunque con il resto.")

# 3. Scarichiamo Hotel (4 e 5 stelle) e Chiese/Monumenti nell'area
print("Estrazione di Hotel 4+ stelle, Chiese e Monumenti...")
tags = {
    'tourism': 'hotel', 
    'amenity': 'place_of_worship', 
    'historic': 'monument'
}

try:
    elementi = ox.features_from_point(centro_roma, tags=tags, dist=raggio_metri)
    
    for idx, row in elementi.iterrows():
        # Trova il punto centrale indipendentemente dal fatto che sia un punto o un edificio (poligono)
        centroide = row.geometry.centroid if hasattr(row.geometry, 'centroid') else row.geometry
        coords = [centroide.y, centroide.x]
        
        nome = row.get('name', 'Nessun nome disponibile')
        
        # Logica di filtraggio e colorazione dei Marker
        if row.get('tourism') == 'hotel' and row.get('stars') in ['4', '5']:
            folium.CircleMarker(location=coords, radius=4, color='gold', fill=True, popup=f"Hotel: {nome}").add_to(mappa_roma)
            
        elif row.get('amenity') == 'place_of_worship':
            folium.CircleMarker(location=coords, radius=3, color='red', fill=True, popup=f"Chiesa: {nome}").add_to(mappa_roma)
            
        elif row.get('historic') == 'monument':
            folium.CircleMarker(location=coords, radius=3, color='blue', fill=True, popup=f"Monumento: {nome}").add_to(mappa_roma)

except Exception as e:
    print(f"Errore durante l'estrazione dei POI: {e}")

# 4. Salvataggio e Apertura automatica
nome_file = "Mappa_Roma_Centro.html"
mappa_roma.save(nome_file)
print(f"Mappa salvata con successo in '{nome_file}'.")

# Tenta di aprire automaticamente la mappa nel browser
path_assoluto = os.path.abspath(nome_file)
webbrowser.open('file://' + path_assoluto)
