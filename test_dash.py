import dash
from dash import html
import os
from flask import Flask

# Create Flask server
server = Flask(__name__)
server.secret_key = "test-secret"

# Create Dash app
app = dash.Dash(__name__, server=server)

# FORCE A SIMPLE LAYOUT
app.layout = html.Div([
    html.H1("TEST DASHBOARD WORKS!", style={'color': 'white', 'text-align': 'center'}),
    html.P("If you see this, Dash is working on Heroku!", style={'color': 'white', 'text-align': 'center'})
], style={'background-color': '#191B27', 'padding': '50px', 'min-height': '100vh'})

# Server setup
if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=8050)
