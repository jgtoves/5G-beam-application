import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.graph_objs as go
from flask import Flask, request, jsonify
from flask_cors import CORS
import math

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

@server.route('/update', methods=['POST'])
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

# --- FULL CALLBACK ---
@app.callback(
    [Output('signal-graph', 'figure'), 
     Output('needle-rotation', 'style'),
     Output('status-display', 'children'),
     Output('status-display', 'style')],
    [Input('refresh', 'n_intervals')]
)
def update_ui(n):
    # 1. Update Graph
    history_data = list(live_stats["history"])
    fig = go.Figure(go.Scatter(y=history_data, mode='lines+markers', line=dict(color='#00ff00', width=3)))
    fig.update_layout(
        template="plotly_dark", 
        yaxis=dict(range=[-120, -60], gridcolor='#333'),
        xaxis=dict(showgrid=False),
        margin=dict(l=20, r=20, t=10, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # 2. Update Compass
    tower = TOWER_DATABASE[live_stats["active_tower"]]
    angle = calculate_bearing(user_location['lat'], user_location['lon'], tower['lat'], tower['lon'])
    needle_style = {
        'transform': f'rotate({angle}deg)', 'transformOrigin': 'bottom center',
        'width': '4px', 'height': '50px', 'backgroundColor': 'red', 
        'position': 'absolute', 'left': '48%', 'top': '10%'
    }
    
    # 3. Detection Logic
    try:
        rsrp = int(data.get('rsrp', 0))
    except (ValueError, TypeError):
        rsrp = 0 

    # All these lines must start at the exact same vertical column
    if rsrp < -98: 
        msg, color, bg = "⚠️ PERSON DETECTED ⚠️", "white", "red"
    else:
        msg, color, bg = "✅ ROOM CLEAR", "#00ff00", "transparent"
        
    status_style = {
        'color': color, 
        'backgroundColor': bg, 
        'textAlign': 'center', 
        'fontSize': '45px'
    }
    
    return fig, needle_style, msg, status_style

# NO spaces at the start of these two lines!
if __name__ == '__main__':
app.run(host='0.0.0.0', port=5000, debug=True)
