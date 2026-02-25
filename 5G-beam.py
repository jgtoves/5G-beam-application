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

# --- GLOBAL STORAGE ---
# This acts as the bridge between Tasker and your Dashboard
latest_signal = {"rsrp": -90, "tower": "GTA_Micronesia_Mall"} 
history_data = [] # Stores RSRP over time for the graph

# --- FLASK ROUTE (Receives data from Tasker) ---
@server.route('/update', methods=['GET', 'POST'])
def update_signal():
    global latest_signal
    if request.method == 'POST':
        content = request.get_json(silent=True)
        if content and 'rsrp' in content:
            # Update the global variable
            latest_signal['rsrp'] = int(content['rsrp'])
            print(f"Tasker sent: {latest_signal['rsrp']} dBm")
            return jsonify({"status": "success"}), 200
    return "Server is running. Send POST to /update", 200

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

# --- DASHBOARD CALLBACK (Updates the UI) ---
@app.callback(
    [Output('status-display', 'children'),
     Output('status-display', 'style'),
     Output('needle-rotation', 'style'),
     Output('signal-graph', 'figure')],
    [Input('refresh', 'n_intervals')]
)
def update_dashboard(n):
    global latest_signal, history_data
    
    rsrp = latest_signal['rsrp']
    history_data.append(rsrp)
    if len(history_data) > 50: history_data.pop(0)

    # 1. Detection Logic
    # Calibration: -105 is usually the 'person blocking' threshold
    if rsrp < -105:
        status_text = "⚠️ PERSON DETECTED"
        status_style = {'backgroundColor': '#ff0000', 'color': 'white', 'borderRadius': '10px'}
    else:
        status_text = "✅ ROOM CLEAR"
        status_style = {'backgroundColor': '#00ff00', 'color': 'black', 'borderRadius': '10px'}

    # 2. Compass Rotation (Fake math for visual effect)
    needle_style = {
        'width': '4px', 'height': '50px', 'backgroundColor': 'red',
        'position': 'absolute', 'left': '48%', 'top': '10%',
        'transformOrigin': 'bottom center', 
        'transform': f'rotate({(rsrp + 140) * 2}deg)', # Rotate based on signal
        'transition': 'transform 0.5s'
    }

    # 3. Graph Data
    fig = go.Figure(
        data=[go.Scatter(y=list(history_data), mode='lines', line=dict(color='#00ff00', width=3))],
        layout=go.Layout(
            title=f"Current Signal: {rsrp} dBm",
            paper_bgcolor='#111', plot_bgcolor='#111',
            font=dict(color='white'),
            xaxis=dict(visible=False),
            yaxis=dict(range=[-130, -60], gridcolor='#333'),
            margin=dict(l=20, r=20, t=40, b=20)
        )
    )

    return status_text, status_style, needle_style, fig

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=5000, debug=False)
