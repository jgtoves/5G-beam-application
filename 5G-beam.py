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

# --- GLOBALS ---
latest_signal = {"rsrp": -95}
history_data = []
user_location = {"lat": 13.520, "lon": 144.820}

# --- THE DATA RECEIVER (Completely separate path) ---
@server.route('/signal', methods=['GET', 'POST'])
def update_signal():
    global latest_signal
    # Support both GET (from URL) and POST (from JSON)
    val = request.args.get('rsrp') or (request.json.get('rsrp') if request.is_json else None)
    
    if val is not None:
        latest_signal['rsrp'] = int(val)
        print(f"📡 DATA RECEIVED: {val}")
        return f"OK: {val}", 200
    return "No Data", 400

# --- DASHBOARD LAYOUT ---
app.layout = html.Div([
    html.H2("5G Person-Detection Radar", style={'textAlign': 'center', 'color': '#00ff00'}),
    html.Div(id='status-display', style={'textAlign': 'center', 'fontSize': '30px', 'padding': '10px'}),
    dcc.Graph(id='signal-graph', config={'displayModeBar': False}),
    dcc.Interval(id='refresh', interval=1000) # 1 second refresh
], style={'backgroundColor': '#111', 'color': 'white', 'height': '100vh'})

# --- DASHBOARD CALLBACK ---
@app.callback(
    [Output('status-display', 'children'),
     Output('status-display', 'style'),
     Output('signal-graph', 'figure')],
    [Input('refresh', 'n_intervals')]
)
def update_ui(n):
    global latest_signal, history_data
    rsrp = latest_signal['rsrp']
    history_data.append(rsrp)
    if len(history_data) > 30: history_data.pop(0)

    # Simple Detection Logic
    color = "#00ff00" if rsrp > -105 else "#ff0000"
    status = "✅ CLEAR" if rsrp > -105 else "⚠️ DETECTED"
    
    fig = {
        'data': [{'y': list(history_data), 'type': 'line', 'line': {'color': color}}],
        'layout': {'paper_bgcolor': '#111', 'plot_bgcolor': '#111', 'font': {'color': 'white'},
                   'yaxis': {'range': [-130, -60]}}
    }
    
    style = {'backgroundColor': color, 'color': 'black', 'borderRadius': '10px'}
    return f"{status} ({rsrp} dBm)", style, fig

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
