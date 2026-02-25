import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.graph_objs as go
from flask import Flask, request, jsonify
from flask_cors import CORS
import math
import subprocess
import json
import re
from flask import request

# --- TOWER DATABASE ---
TOWER_DATABASE = {
    "GTA_Micronesia_Mall": {"lat": 13.5152, "lon": 144.8155, "name": "Mall Main Hub"},
    "GTA_Macheche": {"lat": 13.5225, "lon": 144.8285, "name": "Macheche/Harmon Loop"},
    "GTA_Wusstig_Rd": {"lat": 13.5481, "lon": 144.8512, "name": "North Dededo"},
    "GTA_Yigo_South": {"lat": 13.5350, "lon": 144.8850, "name": "Yigo Main Entry"},
    "GTA_Two_Lovers": {"lat": 13.5220, "lon": 144.8010, "name": "Two Lovers Point Ridge"},
    "IT&E_Harmon_Ind": {"lat": 13.5085, "lon": 144.8050, "name": "Harmon Industrial Park"},
    "GTA_Barrigada_Hts": {"lat": 13.4950, "lon": 144.8150, "name": "Barrigada Heights"},
    "DOCOMO_Tamuning": {"lat": 13.4850, "lon": 144.7880, "name": "Tamuning Medical Hub"},
    "GTA_NCTAMS_South": {"lat": 13.5650, "lon": 144.8380, "name": "Finegayan Ridge"},
    "IT&E_Dededo_Village": {"lat": 13.5280, "lon": 144.8450, "name": "Central Dededo Hub"}
}

# --- 1. SETTINGS & GLOBALS (Define these FIRST) ---
user_location = {"lat": 13.520, "lon": 144.820} 
latest_signal = {"rsrp": -90}
history_data = []

server = Flask(__name__)
CORS(server)
app = dash.Dash(__name__, server=server)


# --- FLASK ROUTE (Receives data from Tasker) ---
@server.route('/update/', methods=['GET', 'POST'])
def update_signal():
    global latest_signal
    if request.method == 'POST':
        content = request.get_json(silent=True)
        if content and 'rsrp' in content:
            latest_signal['rsrp'] = int(content['rsrp'])
            return {"status": "success"}, 200
    return "Server is alive. Waiting for Tasker...", 200

# --- DASHBOARD LAYOUT ---
app.layout = html.Div([
    html.H2("5G Person-Detection Radar", style={'textAlign': 'center', 'color': '#00ff00'}),
    
    html.Div([
        # LEFT SIDE: COMPASS
        html.Div([
            html.H4("Tower Direction", style={'color': 'white'}),
            html.Div(id='compass-needle', style={
                'width': '120px', 'height': '120px', 'borderRadius': '50%',
                'border': '3px solid #555', 'margin': 'auto', 'position': 'relative',
                'backgroundColor': '#222'
            }, children=[
                html.Div(id='needle-rotation', style={
                    'width': '4px', 'height': '50px', 'backgroundColor': 'red',
                    'position': 'absolute', 'left': '48%', 'top': '10%',
                    'transformOrigin': 'bottom center', 'transition': 'transform 0.5s'
                })
            ])
        ], style={'width': '30%', 'display': 'inline-block', 'textAlign': 'center', 'verticalAlign': 'top'}),
        
        # RIGHT SIDE: GRAPH
        html.Div([
            dcc.Graph(id='signal-graph', animate=True, config={'displayModeBar': False})
        ], style={'width': '65%', 'display': 'inline-block'})
    ]),
    
    # BOTTOM: DETECTION STATUS
    html.Div(id='status-display', style={
        'textAlign': 'center', 'fontSize': '45px', 'marginTop': '40px', 
        'padding': '20px', 'borderRadius': '10px', 'fontWeight': 'bold'
    }),
    
    dcc.Interval(id='refresh', interval=500) # Refresh every half-second
], style={'backgroundColor': '#111', 'padding': '20px', 'height': '100vh', 'fontFamily': 'sans-serif'})

# --- MATH HELPER ---
def calculate_bearing(lat1, lon1, lat2, lon2):
    try:
        dLon = math.radians(lon2 - lon1)
        y = math.sin(dLon) * math.cos(math.radians(lat2))
        x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
            math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dLon)
        return (math.degrees(math.atan2(y, x)) + 360) % 360
    except:
        return 0

# --- DASHBOARD CALLBACK ---
# --- 1. SETTINGS & GLOBALS (Define these FIRST) ---
user_location = {"lat": 13.520, "lon": 144.820} 
latest_signal = {"rsrp": -90}
history_data = []

# --- 2. APP INITIALIZATION ---
server = Flask(__name__)
app = dash.Dash(__name__, server=server)

# --- 3. THE FUNCTION (Tell it where to look) ---
@app.callback(
    [Output('status-display', 'children'),
     Output('status-display', 'style'),
     Output('needle-rotation', 'style'),
     Output('signal-graph', 'figure')],
    [Input('refresh', 'n_intervals')]
)
def update_dashboard(n):
    # You MUST include 'user_location' in this global line
    global latest_signal, history_data, user_location 
    
    
    # Grab data safely
    rsrp = latest_signal.get('rsrp', -105)
    history_data.append(rsrp)
    if len(history_data) > 50:
        history_data.pop(0)

    # 1. Compass Math
    # Pointing to the Micronesia Mall tower as a test
    target = TOWER_DATABASE["GTA_Micronesia_Mall"]
    bearing = calculate_bearing(user_location['lat'], user_location['lon'], target['lat'], target['lon'])
    
    # Add 'jitter' so the needle looks alive
    jitter = (n % 5) - 2 # Artificial tiny movement to show it's "scanning"
    
    # 2. Needle Style
    needle_style = {
        'width': '4px', 'height': '50px', 'backgroundColor': 'red',
        'position': 'absolute', 'left': '48%', 'top': '10%',
        'transformOrigin': 'bottom center', 
        'transform': f'rotate({bearing + jitter}deg)',
        'transition': 'transform 0.2s'
    }

    # 3. Status Logic
    if rsrp < -108: # Adjusted for Guam typical indoor signals
        status_text = f"⚠️ INTRUSION DETECTED | {rsrp} dBm"
        status_style = {'backgroundColor': '#660000', 'color': 'white', 'textAlign': 'center'}
    else:
        status_text = f"✅ RADAR CLEAR | {rsrp} dBm"
        status_style = {'backgroundColor': '#002200', 'color': '#00ff00', 'textAlign': 'center'}

    # 4. Graph Update
    fig = go.Figure(
        data=[go.Scatter(y=list(history_data), mode='lines+markers', line=dict(color='#00ff00'))],
        layout=go.Layout(
            plot_bgcolor='#111', paper_bgcolor='#111',
            font=dict(color='#00ff00'),
            yaxis=dict(range=[-130, -60], gridcolor='#222'),
            xaxis=dict(visible=False),
            height=300, margin=dict(l=10, r=10, t=10, b=10)
        )
    )

    return status_text, status_style, needle_style, fig

    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
