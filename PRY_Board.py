# === PART 1: AUTHENTICATION, SETUP, DATA ===

import os
import pandas as pd
import plotly.express as px
import dash
from dash import html, dcc, Input, Output, State, ctx, dash_table
import dash_bootstrap_components as dbc
from flask import Flask, redirect, request
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
import uuid

# === USERS & LOGIN ===
USERS = {
    "bdistel17$$": {"password": "bad_bunny1017$$"},
    "cbarnard2025": {"password": "admin_equityinsight!"},
    "PRY_Admin": {"password": "382716!"}
}

server = Flask(__name__)
server.secret_key = "supersecretkey"
login_manager = LoginManager()
login_manager.init_app(server)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# === LOGGING FUNCTION ===
def log_activity(user, action):
    os.makedirs("logs", exist_ok=True)
    with open("logs/activity_log.csv", "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp},{user},{action}\n")

def log_login(user):
    os.makedirs("logs", exist_ok=True)
    with open("logs/logins.csv", "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp},{user},login\n")

# === LOAD DATA ===
df = pd.read_excel("PRY_Dash.xlsx", sheet_name="Data")

# Preprocessing
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
df = df.dropna(subset=['Date'])

# Category map
category_map = {
    "ALUM-PR": "Aluminum Wire (Price Inferred) Imports",
    "ALBW": "Aluminum Building Wire Imports",
    "PV": "Photovoltaic Wire Imports",
    "OHT": "Overhead Transmission Wire Imports",
    "COPP-PR": "Copper Wire (Price Inferred) Imports",
    "COPP": "Copper Wire Imports",
    "CORD": "Cord Imports",
    "RESI": "Residential Imports",
    "MV": "Medium Voltage Imports",
    "TRAY": "Tray Cable Imports",
    "SPEC": "Specialty Item Imports",
    "CATH": "Cathode Imports",
    "COMMS": "Communications Wire Imports",
    "TOOL": "Tool Imports",
    "RM": "Raw Material Imports",
    "UNMP": "Unmapped Imports"
}
df["Category Description"] = df["Category"].map(category_map)
df = df[df["Category"] != "CATH"]  # exclude CATH for pie chart

# Buyer/Seller logic
def get_buyer(row):
    if row['Shipper Declared'] == row['International Competitor']:
        return row['Domestic Competitor']
    elif row['Shipper Declared'] == row['Domestic Competitor']:
        return row['International Competitor']
    else:
        return "Unknown"

df["Seller"] = df["Shipper Declared"]
df["Buyer"] = df.apply(get_buyer, axis=1)
df["HS Code"] = df["HS Code"].astype(str).str.zfill(6)

# === COLORS ===
COLOR_BG = "#191B27"
COLOR_ACCENT = "#0093FF"
COLOR_SUCCESS = "#22C70C"
COLOR_TEXT = "#DCE4F2"
COLOR_PANEL = "#2D354A"

# === DASH APP SETUP ===
from flask import Flask
server = Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Maritime Imports Dashboard"
# === PART 2: DASH LAYOUT ===

# === LOGIN PAGE ===
login_layout = dbc.Container([
    html.Div([
        html.H2("Login", style={"color": COLOR_TEXT, "fontFamily": "Montserrat"}),
        dcc.Input(id="username", type="text", placeholder="Username", className="mb-2 form-control"),
        dcc.Input(id="password", type="password", placeholder="Password", className="mb-2 form-control"),
        html.Button("Login", id="login-btn", n_clicks=0, className="btn btn-primary"),
        html.Div(id="login-message", className="mt-2", style={"color": "red"})
    ], className="p-5", style={"maxWidth": "400px", "margin": "auto"})
], fluid=True, style={"backgroundColor": COLOR_BG, "height": "100vh"})

# === MAIN DASHBOARD LAYOUT ===
def dashboard_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.Img(src="/assets/PRY_Logo.png", height="60px"), width="auto"),
            dbc.Col(html.H1("Maritime Imports Dashboard", className="text-left",
                            style={"color": COLOR_TEXT, "fontFamily": "Montserrat", "paddingTop": "10px"}))
        ], align="center", justify="start", className="mb-4"),

        dbc.Row([
            dbc.Col([
                dcc.DatePickerSingle(id="start-date", placeholder="Start Date", display_format="MM/DD/YYYY"),
                html.Button("Clear", id="clear-start", className="btn btn-outline-secondary btn-sm mt-1")
            ]),
            dbc.Col([
                dcc.DatePickerSingle(id="end-date", placeholder="End Date", display_format="MM/DD/YYYY"),
                html.Button("Clear", id="clear-end", className="btn btn-outline-secondary btn-sm mt-1")
            ]),
            dbc.Col([
                dcc.Dropdown(id="category-dropdown", placeholder="Category"),
                html.Button("Clear", id="clear-category", className="btn btn-outline-secondary btn-sm mt-1")
            ]),
            dbc.Col([
                dcc.Dropdown(id="buyer-dropdown", placeholder="Buyer"),
                html.Button("Clear", id="clear-buyer", className="btn btn-outline-secondary btn-sm mt-1")
            ]),
            dbc.Col([
                dcc.Dropdown(id="seller-dropdown", placeholder="Seller"),
                html.Button("Clear", id="clear-seller", className="btn btn-outline-secondary btn-sm mt-1")
            ]),
            dbc.Col([
                dcc.Dropdown(id="hs-dropdown", placeholder="HS Code"),
                html.Button("Clear", id="clear-hs", className="btn btn-outline-secondary btn-sm mt-1")
            ]),
            dbc.Col([
                dcc.Dropdown(id="country-dropdown", placeholder="Country"),
                html.Button("Clear", id="clear-country", className="btn btn-outline-secondary btn-sm mt-1")
            ])
        ], className="g-2"),

        html.Div([
            html.Div([
                html.Div(id="kpi-volume", className="kpi-card"),
                html.Div(id="kpi-value", className="kpi-card"),
                html.Div(id="kpi-price", className="kpi-card"),
                html.Div(id="kpi-count", className="kpi-card")
            ], className="d-flex justify-content-between my-4")
        ]),

        dbc.Row([
            dbc.Col(dcc.Graph(id="buyers-chart"), md=6),
            dbc.Col(dcc.Graph(id="sellers-chart"), md=6)
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id="categories-pie"), md=6),
            dbc.Col(dcc.Graph(id="countries-chart"), md=6)
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id="time-series-chart"), md=6),
            dbc.Col(dcc.Graph(id="hs-analysis-chart"), md=6)
        ]),

        html.Div([
            html.Button("Clear All Filters", id="clear-all", className="btn btn-warning me-2"),
            html.Button("Logout", id="logout-btn", className="btn btn-danger me-2"),
            html.Button("Export to Excel", id="export-button", className="btn btn-success")
        ], className="my-4"),

        dash_table.DataTable(
            id="data-table",
            page_size=15,
            style_table={"overflowX": "auto"},
            style_header={"backgroundColor": COLOR_PANEL, "color": COLOR_TEXT, "fontWeight": "bold", "fontFamily": "Montserrat"},
            style_data={"backgroundColor": COLOR_BG, "color": COLOR_TEXT, "fontFamily": "Montserrat"}
        ),

        dcc.Download(id="download-data")
    ], fluid=True, style={"backgroundColor": COLOR_BG, "padding": "20px"})
# === PART 3: CALLBACKS & LOGIC ===

# Initial page loader
@app.callback(Output("page-content", "children"), Input("login-btn", "n_clicks"),
              State("username", "value"), State("password", "value"),
              prevent_initial_call=True)
def process_login(n, u, p):
    if u in USERS and USERS[u]["password"] == p:
        login_user(User(id=u))
        log_login(u)
        log_activity(u, "Logged In")
        return dashboard_layout()
    return login_layout

@app.callback(Output("page-content", "children"), Input("logout-btn", "n_clicks"),
              prevent_initial_call=True)
def process_logout(n):
    log_activity(current_user.id, "Logged Out")
    logout_user()
    return login_layout

# Dynamic filter options based on selection
@app.callback(
    Output("category-dropdown", "options"),
    Output("buyer-dropdown", "options"),
    Output("seller-dropdown", "options"),
    Output("hs-dropdown", "options"),
    Output("country-dropdown", "options"),
    Input("start-date", "date"),
    Input("end-date", "date"),
    Input("category-dropdown", "value"),
    Input("buyer-dropdown", "value"),
    Input("seller-dropdown", "value"),
    Input("hs-dropdown", "value"),
    Input("country-dropdown", "value")
)
def update_filter_options(start, end, cat, buyer, seller, hs, country):
    dff = df.copy()
    if start: dff = dff[dff["Date"] >= pd.to_datetime(start)]
    if end: dff = dff[dff["Date"] <= pd.to_datetime(end)]
    if cat: dff = dff[dff["Category Description"] == cat]
    if buyer: dff = dff[dff["Buyer"] == buyer]
    if seller: dff = dff[dff["Seller"] == seller]
    if hs: dff = dff[dff["HS Code"] == hs]
    if country: dff = dff[dff["Country of Origin"] == country]

    return [
        [{"label": i, "value": i} for i in sorted(dff["Category Description"].dropna().unique())],
        [{"label": i, "value": i} for i in sorted(dff["Buyer"].dropna().unique())],
        [{"label": i, "value": i} for i in sorted(dff["Seller"].dropna().unique())],
        [{"label": i, "value": i} for i in sorted(dff["HS Code"].dropna().unique())],
        [{"label": i, "value": i} for i in sorted(dff["Country of Origin"].dropna().unique())]
    ]

# Clear buttons per filter
@app.callback(
    Output("start-date", "date"),
    Output("end-date", "date"),
    Output("category-dropdown", "value"),
    Output("buyer-dropdown", "value"),
    Output("seller-dropdown", "value"),
    Output("hs-dropdown", "value"),
    Output("country-dropdown", "value"),
    Input("clear-start", "n_clicks"),
    Input("clear-end", "n_clicks"),
    Input("clear-category", "n_clicks"),
    Input("clear-buyer", "n_clicks"),
    Input("clear-seller", "n_clicks"),
    Input("clear-hs", "n_clicks"),
    Input("clear-country", "n_clicks"),
    Input("clear-all", "n_clicks"),
    prevent_initial_call=True
)
def clear_filters(*args):
    triggered = ctx.triggered_id
    if triggered == "clear-start" or triggered == "clear-all":
        return None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if triggered == "clear-end" or triggered == "clear-all":
        return dash.no_update, None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if triggered == "clear-category" or triggered == "clear-all":
        return dash.no_update, dash.no_update, None, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if triggered == "clear-buyer" or triggered == "clear-all":
        return dash.no_update, dash.no_update, dash.no_update, None, dash.no_update, dash.no_update, dash.no_update
    if triggered == "clear-seller" or triggered == "clear-all":
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, None, dash.no_update, dash.no_update
    if triggered == "clear-hs" or triggered == "clear-all":
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, None, dash.no_update
    if triggered == "clear-country" or triggered == "clear-all":
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, None

    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Shared filtered dataframe
def filter_df(start, end, cat, buyer, seller, hs, country):
    dff = df.copy()
    if start: dff = dff[dff["Date"] >= pd.to_datetime(start)]
    if end: dff = dff[dff["Date"] <= pd.to_datetime(end)]
    if cat: dff = dff[dff["Category Description"] == cat]
    if buyer: dff = dff[dff["Buyer"] == buyer]
    if seller: dff = dff[dff["Seller"] == seller]
    if hs: dff = dff[dff["HS Code"] == hs]
    if country: dff = dff[dff["Country of Origin"] == country]
    return dff

# KPI cards
@app.callback(
    Output("kpi-volume", "children"),
    Output("kpi-value", "children"),
    Output("kpi-price", "children"),
    Output("kpi-count", "children"),
    Input("start-date", "date"),
    Input("end-date", "date"),
    Input("category-dropdown", "value"),
    Input("buyer-dropdown", "value"),
    Input("seller-dropdown", "value"),
    Input("hs-dropdown", "value"),
    Input("country-dropdown", "value")
)
def update_kpis(*filters):
    dff = filter_df(*filters)
    return (
        f"Total Volume: {dff['Metric Tons'].sum():,.0f}",
        f"Total Value: ${dff['Calculated Value'].sum():,.0f}",
        f"Avg $/KG: ${dff['Val/KG ($)'].mean():.2f}",
        f"Transactions: {len(dff):,}"
    )

# Charts
@app.callback(
    Output("buyers-chart", "figure"),
    Output("sellers-chart", "figure"),
    Output("categories-pie", "figure"),
    Output("countries-chart", "figure"),
    Output("time-series-chart", "figure"),
    Output("hs-analysis-chart", "figure"),
    Output("data-table", "data"),
    Input("start-date", "date"),
    Input("end-date", "date"),
    Input("category-dropdown", "value"),
    Input("buyer-dropdown", "value"),
    Input("seller-dropdown", "value"),
    Input("hs-dropdown", "value"),
    Input("country-dropdown", "value")
)
def update_charts(*filters):
    dff = filter_df(*filters)
    # Buyers chart
    buyers = dff.groupby("Buyer")["Metric Tons"].sum().nlargest(8).reset_index()
    fig_buyers = px.bar(buyers, x="Buyer", y="Metric Tons", color="Metric Tons", color_continuous_scale=[[0, COLOR_SUCCESS], [1, COLOR_ACCENT]])

    # Sellers chart
    sellers = dff.groupby("Seller")["Metric Tons"].sum().nlargest(8).reset_index()
    fig_sellers = px.bar(sellers, x="Seller", y="Metric Tons", color="Metric Tons", color_continuous_scale=[[0, COLOR_SUCCESS], [1, COLOR_ACCENT]])

    # Categories pie
    cats = dff.groupby("Category Description")["Metric Tons"].sum().nlargest(4).reset_index()
    fig_pie = px.pie(cats, names="Category Description", values="Metric Tons", hole=0.4)

    # Countries
    countries = dff.groupby("Country of Origin")["Metric Tons"].sum().nlargest(8).reset_index()
    fig_countries = px.bar(countries, x="Country of Origin", y="Metric Tons", color="Metric Tons", color_continuous_scale=[[0, COLOR_SUCCESS], [1, COLOR_ACCENT]])

    # Time series
    time = dff.groupby("Date").agg({"Metric Tons": "sum", "Calculated Value": "sum"}).reset_index()
    fig_time = px.line(time, x="Date", y=["Metric Tons", "Calculated Value"])

    # HS code chart
    hs = dff.groupby("HS Code").agg({"Metric Tons": "sum", "Calculated Value": "sum"}).nlargest(8, "Metric Tons").reset_index()
    fig_hs = px.bar(hs, x="HS Code", y="Metric Tons", color="Metric Tons", color_continuous_scale=[[0, COLOR_SUCCESS], [1, COLOR_ACCENT]])

    return fig_buyers, fig_sellers, fig_pie, fig_countries, fig_time, fig_hs, dff.to_dict("records")

# Export
@app.callback(
    Output("download-data", "data"),
    Input("export-button", "n_clicks"),
    State("start-date", "date"),
    State("end-date", "date"),
    State("category-dropdown", "value"),
    State("buyer-dropdown", "value"),
    State("seller-dropdown", "value"),
    State("hs-dropdown", "value"),
    State("country-dropdown", "value"),
    prevent_initial_call=True
)
def export_filtered_data(n, *filters):
    user = current_user.id if current_user else "Anonymous"
    log_activity(user, "Exported filtered table")
    dff = filter_df(*filters)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return dcc.send_data_frame(dff.to_excel, f"Filtered_Data_{timestamp}.xlsx", sheet_name="Data", index=False)

# Run the app
if __name__ == "__main__":
    app.layout = html.Div(id="page-content")
    app.run_server(debug=True)
