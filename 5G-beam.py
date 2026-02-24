import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.graph_objs as go
from flask import Flask, request, jsonify
from flask_cors import CORS
import math

# --- CONFIGURATION: MANUALLY ADD YOUR 10 TOWERS ---
# You can get these Lat/Lon from CellMapper.net for Dededo
# --- TOWER DATABASE: DEDEDO VILLAGE CLUSTERS ---
# Note: RSRP (Signal) will be strongest when your phone faces these coordinates.
TOWER_DATABASE = {
    "GTA_Micronesia_Mall": {"lat": 13.5152, "lon": 144.8155, "name": "Mall Main Hub"},
    "GTA_Wusstig_Rd": {"lat": 13.5481, "lon": 144.8512, "name": "North Dededo"},
    "GTA_Macheche": {"lat": 13.5225, "lon": 144.8285, "name": "Macheche/Harmon Loop"},
    "ITE_Harmon_Industrial": {"lat": 13.5095, "lon": 144.8050, "name": "Harmon Data Center"},
    "GTA_Liguan_Terrace": {"lat": 13.5280, "lon": 144.8210, "name": "Liguan Residential"},
    "GTA_Y_Sengsong": {"lat": 13.5410, "lon": 144.8320, "name": "Y-Sengsong Rd Site"},
    "GTA_Marine_Drive_North": {"lat": 13.5350, "lon": 144.8450, "name": "Marine Drive Corridor"},
    "GTA_Astumbo": {"lat": 13.5520, "lon": 144.8180, "name": "Astumbo District"},
    "ITE_Dededo_Village": {"lat": 13.5180, "lon": 144.8390, "name": "Central Dededo Hub"},
    "GTA_Chalan_Lagu": {"lat": 13.5590, "lon": 144.8350, "name": "North Coastal Site"}
}

server = Flask(__name__)
CORS(server)
app = dash.Dash(__name__, server=server)

# Global storage for live data
live_stats = {"current_rsrp": -100, "active_tower": "Searching...", "history": []}
user_location = {"lat": 13.520, "lon": 144.820} # Your house in Dededo

@server.route('/update', methods=['POST'])
def update_data():
    data = request.json
    live_stats["current_rsrp"] = data.get("rsrp", -110)
    live_stats["active_tower"] = data.get("tower_id", "Unknown")
    live_stats["history"].append(live_stats["current_rsrp"])
    if len(live_stats["history"]) > 100: live_stats["history"].pop(0)
    return jsonify({"status": "success"})

# --- MATH: CALCULATE DIRECTION TO TOWER ---
def calculate_bearing(lat1, lon1, lat2, lon2):
    dLon = math.radians(lon2 - lon1)
    y = math.sin(dLon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
        math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dLon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

# --- DASHBOARD LAYOUT ---
app.layout = html.Div([
    html.H2("Guam 5G Person-Detection Radar", style={'textAlign': 'center'}),
    
    html.Div([
        html.Div([
            html.H4("Tower Compass"),
            html.Div(id='compass-needle', style={
                'width': '100px', 'height': '100px', 'borderRadius': '50%',
                'border': '2px solid white', 'margin': 'auto', 'position': 'relative'
            }, children=[
                html.Div(style={
                    'width': '4px', 'height': '40px', 'backgroundColor': 'red',
                    'position': 'absolute', 'left': '48%', 'top': '10%',
                    'transformOrigin': 'bottom center', 'id': 'needle-rotation'
                })
            ])
        ], style={'width': '30%', 'display': 'inline-block', 'textAlign': 'center'}),
        
        html.Div([
            html.H4("Signal Movement Tracker"),
            dcc.Graph(id='signal-graph', animate=True)
        ], style={'width': '65%', 'display': 'inline-block'})
    ]),
    
    dcc.Interval(id='refresh', interval=500) # 0.5 second updates
])

@app.callback(
    [Output('signal-graph', 'figure'), Output('needle-rotation', 'style')],
    [Input('refresh', 'n_intervals')]
)
def update_ui(n):
    # Graph logic
    fig = go.Figure(go.Scatter(y=live_stats["history"], mode='lines+markers', line=dict(color='#00ff00')))
    fig.update_layout(template="plotly_dark", yaxis=dict(range=[-120, -60]), title="RSRP Intensity")
    
    # Compass logic
    target = TOWER_DATABASE.get("GTA_Dededo_1") 
    angle = calculate_bearing(user_location['lat'], user_location['lon'], target['lat'], target['lon'])
    needle_style = {'transform': f'rotate({angle}deg)', 'transformOrigin': 'bottom center', 
                    'width': '4px', 'height': '40px', 'backgroundColor': 'red', 'position': 'absolute', 'left': '48%', 'top': '10%'}

    
    return fig, needle_style

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# Inside update_ui(n)
rsrp_current = live_stats["current_rsrp"]
baseline = -90  # Adjust based on your room's average signal

# If signal drops by more than 5dBm, it's likely a human body
if rsrp_current < (baseline - 5):
    status_text = "PERSON DETECTED"
    status_color = "red"
else:
    status_text = "CLEAR"
    status_color = "green"
