import folium
import osmnx as ox

# 1. Inizializza la mappa centrata su Roma
rome_coords = [41.8902, 12.4922]
mappa_roma = folium.Map(location=rome_coords, zoom_start=13, tiles='CartoDB positron')

# Definiamo il luogo di ricerca
luogo = "Rome, Italy"

print("Estrazione della rete stradale (può richiedere tempo)...")
# Nota: Scaricare TUTTE le strade di Roma consuma molta RAM. 
# Per sicurezza, limitiamo al centro storico in questo esempio.
strade = ox.graph_from_place(luogo, network_type='drive', retain_all=True)
ox.plot_graph_folium(strade, graph_map=mappa_roma, color="#333333", weight=1)

print("Estrazione degli Hotel 4+ stelle...")
# Estrae hotel tramite i tag di OpenStreetMap
tags_hotels = {'tourism': 'hotel', 'stars': ['4', '5']}
hotels = ox.features_from_place(luogo, tags=tags_hotels)

# Aggiungiamo i marker per gli hotel di lusso
for idx, row in hotels.iterrows():
    if row.geometry.geom_type == 'Point':
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=3,
            color='gold',
            fill=True,
            tooltip=row.get('name', 'Hotel di lusso')
        ).add_to(mappa_roma)

print("Estrazione dei monumenti principali e chiese...")
tags_poi = {'historic': 'monument', 'amenity': 'place_of_worship'}
pois = ox.features_from_place(luogo, tags=tags_poi)

# Aggiungiamo i monumenti e le chiese (limitato ai primi 500 per non bloccare il browser)
for idx, row in pois.head(500).iterrows():
    if row.geometry.geom_type == 'Point':
        colore = 'red' if row.get('amenity') == 'place_of_worship' else 'blue'
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=2,
            color=colore,
            fill=True,
            tooltip=row.get('name', 'Luogo Storico/Religioso')
        ).add_to(mappa_roma)

# Salvataggio della mappa
mappa_roma.save("Mappa_Roma_Dettagliata.html")
print("Mappa completata e salvata come 'Mappa_Roma_Dettagliata.html'. Apri il file nel tuo browser!")
