from flask import Flask, render_template, request, jsonify, send_from_directory
import osmnx as ox
import networkx as nx
import json
import math

app = Flask(__name__)

# Load crime data
with open("crimes.json") as f:
    crimes = json.load(f)

# Download road network for District 5, Quezon City
print("Downloading road network...")
G = ox.graph_from_place("District 5, Quezon City, Philippines", network_type="walk")

# Haversine formula for distance in kilometers
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# Compute cumulative crime severity near a point
def compute_crime_penalty(lat, lon, radius_km=0.5):
    penalty = 0
    for crime in crimes:
        dist = haversine(lat, lon, crime["lat"], crime["long"])
        if dist < radius_km:
            penalty += crime.get("severity", 1)  # Default severity if missing
    return penalty

# Add weighted cost to edges based on crime
for u, v, k, data in G.edges(keys=True, data=True):
    if "length" in data:
        # Calculate midpoint of edge
        u_lat, u_lon = G.nodes[u]['y'], G.nodes[u]['x']
        v_lat, v_lon = G.nodes[v]['y'], G.nodes[v]['x']
        midpoint_lat = (u_lat + v_lat) / 2
        midpoint_lon = (u_lon + v_lon) / 2

        # Compute crime penalty and assign weight
        penalty = compute_crime_penalty(midpoint_lat, midpoint_lon)

        # Adjust weight to strongly discourage crime-heavy areas
        if penalty > 0:
            data['weight'] = float('inf')  # Completely avoid this edge
        else:
            data['weight'] = data['length']

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/crimes.json')
def crimes_json():
    return send_from_directory('.', 'crimes.json')

@app.route('/route', methods=['POST'])
def route():
    data = request.get_json()
    start_lat, start_lon = data["start"]
    end_lat, end_lon = data["end"]

    orig_node = ox.distance.nearest_nodes(G, X=start_lon, Y=start_lat)
    dest_node = ox.distance.nearest_nodes(G, X=end_lon, Y=end_lat)

    try:
        route = nx.shortest_path(G, orig_node, dest_node, weight='weight')
        coords = [[G.nodes[n]['y'], G.nodes[n]['x']] for n in route]
        return jsonify({"path": coords})
    except nx.NetworkXNoPath:
        return jsonify({"error": "No route found"}), 400

if __name__ == '__main__':
    app.run(debug=True)
