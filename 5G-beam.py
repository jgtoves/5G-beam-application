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

server = Flask(__name__)
CORS(server)
app = dash.Dash(__name__, server=server)

# Global storage
live_stats = {"current_rsrp": -100, "active_tower": "GTA_Micronesia_Mall", "history": []}
user_location = {"lat": 13.520, "lon": 144.820} # Your house in Dededo

# Add this near the top of your script
latest_signal = {"rsrp": -90} # Default starting value

@server.route('/update', methods=['GET', 'POST'])
def update_signal():
    global latest_signal
    if request.method == 'POST':
        content = request.get_json(silent=True)
        if content and 'rsrp' in content:
            # 1. Update the global variable for the Dashboard
            latest_signal = content  
            
            # 2. Extract the value for local printing/logic
            val = content['rsrp']
            print(f"Received Signal: {val}")
            
            # 3. Person Detection Logic (Terminal Alert)
            if int(val) < -105:
                print("⚠️ PERSON DETECTED (Signal Blocked)")
            else:
                print("✅ Room Clear")
                
            return {"status": "ok"}, 200
    return "Server Active", 200

def update_data():
    data = request.json
    live_stats["current_rsrp"] = data.get("rsrp", -110)
    live_stats["history"].append(live_stats["current_rsrp"])
    if len(live_stats["history"]) > 50: live_stats["history"].pop(0)
    return jsonify({"status": "success"})

def calculate_bearing(lat1, lon1, lat2, lon2):
    dLon = math.radians(lon2 - lon1)
    y = math.sin(dLon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
        math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dLon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


# --- FULL DASHBOARD LAYOUT ---
# Initialize a global list to store the history for the graph
# (Starts with a neutral -90 dBm)
signal_history = deque(maxlen=50) 
signal_history.append(-90)

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
                html.Div(id='needle-rotation', style={ # <--- ID MUST BE HERE
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
    
    dcc.Interval(id='refresh', interval=500)
], style={'backgroundColor': '#111', 'padding': '20px', 'height': '100vh', 'fontFamily': 'sans-serif'})

# adding below layout
@app.callback(
    [Output('status-display', 'children'),
     Output('status-display', 'style'),
     Output('needle-rotation', 'style'),
     Output('signal-graph', 'figure')],
    [Input('refresh', 'n_intervals')]
)
def update_dashboard(n):
    # latest_signal is the global variable Tasker updates via /update
    global latest_signal
    rsrp = latest_signal.get('rsrp', -110)
    signal_history.append(rsrp)

    # 1. Logic for Detection Status
    if rsrp < -105:
        status_text = "⚠️ PERSON DETECTED"
        status_style = {'backgroundColor': '#ff0000', 'color': 'white', 'textAlign': 'center', 'fontSize': '45px'}
    else:
        status_text = "✅ ROOM CLEAR"
        status_style = {'backgroundColor': '#00ff00', 'color': 'black', 'textAlign': 'center', 'fontSize': '45px'}

    # 2. Logic for Compass (Mapping RSRP to a fake 'rotation' for visual effect)
    # This rotates the needle based on signal strength
    rotation = {'transform': f'rotate({rsrp * 2}deg)', 'width': '4px', 'height': '50px', 
                'backgroundColor': 'red', 'position': 'absolute', 'left': '48%', 'top': '10%',
                'transformOrigin': 'bottom center', 'transition': 'transform 0.5s'}

    # 3. Logic for Graph
    fig = {
        'data': [{'x': list(range(len(signal_history))), 'y': list(signal_history), 'type': 'line', 'marker': {'color': '#00ff00'}}],
        'layout': {
            'title': f'Live RSRP: {rsrp} dBm',
            'plot_bgcolor': '#111',
            'paper_bgcolor': '#111',
            'font': {'color': 'white'},
            'xaxis': {'visible': False},
            'yaxis': {'range': [-140, -60]}
        }
    }

    return status_text, status_style, rotation, fig


# NO spaces at the start of these two lines!
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
