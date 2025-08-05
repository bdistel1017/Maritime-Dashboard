import dash
from dash import dcc, html, dash_table, Input, Output, State, callback, ctx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import re
import warnings
import os
from typing import List, Dict, Any
import json
import base64

# Flask-Login imports
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import Flask, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

# Suppress warnings
warnings.filterwarnings("ignore")

# Initialize Flask server
# Initialize Flask server
server = Flask(__name__)
server.secret_key = os.environ.get('SECRET_KEY', 'pry-maritime-dashboard-secret-2024-production')

# Initialize Dash app - MINIMAL SETUP
app = dash.Dash(__name__, server=server)
app.title = "Maritime Imports Dashboard - PRY Analytics"

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = '/login'

# Force component registration
app.scripts.config.serve_locally = True
app.css.config.serve_locally = True
app.title = "Maritime Imports Dashboard - PRY Analytics"

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = '/login'

# Color Palette - YOUR EXACT COLORS
COLORS = {
    'night_black': '#191B27',
    'light_blue': '#0093FF',
    'light_gray': '#DCE4F2',
    'dark_gray': '#2D354A',
    'light_green': '#22C70C',
    'purple': '#8B5CF6'
}

CHART_COLORS = [COLORS['light_blue'], COLORS['light_green'], COLORS['purple'], '#4ECDC4', '#45B7D1', '#0EA5E9']

# YOUR CUSTOM USER DATABASE
USERS_DB = {
    'bdistel17$$': {
        'password_hash': generate_password_hash('bad_bunny1017$$'),
        'role': 'admin'
    },
    'cbarnard2025': {
        'password_hash': generate_password_hash('admin_equityinsight!'),
        'role': 'admin'
    },
    'PRY_Admin': {
        'password_hash': generate_password_hash('382716!'),
        'role': 'super_admin'
    }
}

# CATEGORY MAPPING
CATEGORY_MAPPING = {
    'Aluminum Wire (Price Inferred) Imports': 'ALUM-PR',
    'Aluminum Building Wire Imports': 'ALBW',
    'Photovoltaic Wire Imports': 'PV',
    'Overhead Transmission Wire Imports': 'OHT',
    'Copper Wire (Price Inferred) Imports': 'COPP-PR',
    'Copper Wire Imports': 'COPP',
    'Cord Imports': 'CORD',
    'Residential Imports': 'RESI',
    'Medium Voltage Imports': 'MV',
    'Tray Cable Imports': 'TRAY',
    'Specialty Item Imports': 'SPEC',
    'Cathode Imports': 'CATH',
    'Communications Wire Imports': 'COMMS',
    'Tool Imports': 'TOOL',
    'Raw Material Imports': 'RM',
    'Unmapped Imports': 'UNMP'
}

CODE_TO_DESCRIPTION = {v: k for k, v in CATEGORY_MAPPING.items()}


# User class for Flask-Login
class User(UserMixin):
    def __init__(self, username, role):
        self.id = username
        self.username = username
        self.role = role


@login_manager.user_loader
def load_user(username):
    if username in USERS_DB:
        return User(username, USERS_DB[username]['role'])
    return None


def load_data():
    """Load and preprocess Excel data"""
    try:
        df = pd.read_excel('PRY_Dash.xlsx', sheet_name='Data')
        df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y', errors='coerce')

        def determine_buyer(row):
            shipper = str(row['Shipper Declared']).strip() if pd.notna(row['Shipper Declared']) else ''
            intl_comp = str(row['International Competitor']).strip() if pd.notna(
                row['International Competitor']) else ''
            dom_comp = str(row['Domestic Competitor']).strip() if pd.notna(row['Domestic Competitor']) else ''

            def clean_name(name):
                return re.sub(r'\b(LTD|LLC|INC|CO|COMPANY|LIMITED|PRIVATE)\b\.?', '', name.upper()).strip()

            shipper_clean = clean_name(shipper)
            intl_clean = clean_name(intl_comp)
            dom_clean = clean_name(dom_comp)

            if intl_comp and intl_clean != shipper_clean:
                return intl_comp
            elif dom_comp and dom_clean != shipper_clean:
                return dom_comp
            elif intl_comp:
                return intl_comp
            elif dom_comp:
                return dom_comp
            else:
                return 'Unknown'

        df['Buyer'] = df.apply(determine_buyer, axis=1)
        df['Seller'] = df['Shipper Declared']
        df['Metric Tons'] = pd.to_numeric(df['Metric Tons'], errors='coerce')
        df['Total calculated value ($)'] = pd.to_numeric(df['Total calculated value ($)'], errors='coerce')
        df['Val/KG ($)'] = pd.to_numeric(df['Val/KG ($)'], errors='coerce')

        # Clean up data - remove NaN values
        df = df.dropna(subset=['Metric Tons', 'Total calculated value ($)', 'Val/KG ($)'])

        target_hs_codes = ['854442', '854449', '854460', '740311']
        df = df[df['HS Code'].astype(str).isin(target_hs_codes)]

        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()


# Load data
df = load_data()


def parse_date_simple(date_string):
    """Parse various date formats"""
    if not date_string:
        return None
    try:
        return datetime.strptime(date_string.strip(), '%m/%d/%Y').date()
    except:
        try:
            return datetime.strptime(date_string.strip(), '%m-%d-%Y').date()
        except:
            return None


def get_logo_data():
    """Get base64 encoded logo data"""
    try:
        with open('PRY_Logo.png', 'rb') as f:
            logo_data = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{logo_data}"
    except:
        return None


LOGO_DATA = get_logo_data()


# LOGIN PAGE LAYOUT
def create_login_layout():
    return html.Div([
        html.Div([
            html.Div([
                html.Img(src=LOGO_DATA, style={'height': '80px', 'margin-bottom': '30px'}) if LOGO_DATA else html.Div(),
                html.H1("Maritime Imports Dashboard", style={
                    'color': COLORS['light_gray'],
                    'text-align': 'center',
                    'margin-bottom': '20px',
                    'font-size': '36px',
                    'font-family': 'Montserrat, sans-serif'
                }),
                html.H3("Secure Dashboard Access", style={
                    'color': COLORS['light_blue'],
                    'text-align': 'center',
                    'margin-bottom': '30px',
                    'font-family': 'Montserrat, sans-serif'
                }),

                html.Div([
                    html.Label("Username:", style={
                        'color': COLORS['light_gray'],
                        'margin-bottom': '10px',
                        'display': 'block',
                        'font-family': 'Montserrat, sans-serif',
                        'font-weight': '600'
                    }),
                    dcc.Input(
                        id='username-input',
                        type='text',
                        placeholder='Enter your username',
                        style={
                            'width': '100%',
                            'padding': '15px',
                            'border-radius': '8px',
                            'border': f'2px solid {COLORS["dark_gray"]}',
                            'background-color': COLORS['dark_gray'],
                            'color': COLORS['light_gray'],
                            'font-size': '16px',
                            'margin-bottom': '20px',
                            'font-family': 'Montserrat, sans-serif'
                        }
                    ),

                    html.Label("Password:", style={
                        'color': COLORS['light_gray'],
                        'margin-bottom': '10px',
                        'display': 'block',
                        'font-family': 'Montserrat, sans-serif',
                        'font-weight': '600'
                    }),
                    dcc.Input(
                        id='password-input',
                        type='password',
                        placeholder='Enter your password',
                        style={
                            'width': '100%',
                            'padding': '15px',
                            'border-radius': '8px',
                            'border': f'2px solid {COLORS["dark_gray"]}',
                            'background-color': COLORS['dark_gray'],
                            'color': COLORS['light_gray'],
                            'font-size': '16px',
                            'margin-bottom': '20px',
                            'font-family': 'Montserrat, sans-serif'
                        }
                    ),

                    html.Button("Login", id='login-button', style={
                        'width': '100%',
                        'padding': '15px',
                        'background': f'linear-gradient(135deg, {COLORS["light_blue"]} 0%, {COLORS["light_green"]} 100%)',
                        'color': COLORS['night_black'],
                        'border': 'none',
                        'border-radius': '8px',
                        'font-size': '18px',
                        'font-weight': 'bold',
                        'cursor': 'pointer',
                        'margin-bottom': '20px',
                        'font-family': 'Montserrat, sans-serif'
                    }),

                    html.Div(id='login-status', style={
                        'text-align': 'center',
                        'margin-top': '20px',
                        'font-family': 'Montserrat, sans-serif'
                    })

                ], style={'max-width': '400px', 'margin': '0 auto'})

            ], style={
                'background': f'linear-gradient(135deg, {COLORS["dark_gray"]} 0%, {COLORS["night_black"]} 100%)',
                'padding': '50px',
                'border-radius': '20px',
                'box-shadow': '0 10px 40px rgba(0,0,0,0.5)',
                'border': f'1px solid {COLORS["light_blue"]}',
                'text-align': 'center'
            })
        ], style={
            'display': 'flex',
            'justify-content': 'center',
            'align-items': 'center',
            'min-height': '100vh',
            'background-color': COLORS['night_black'],
            'padding': '20px'
        })
    ], style={'font-family': 'Montserrat, sans-serif'})


# PERFECT CHART FUNCTIONS WITH BLUE-GREEN GRADIENTS
def create_buyer_analysis_chart(data):
    """Top 8 buyers with blue-green gradient - SMART FILTERING"""
    if len(data) == 0:
        return px.bar(title="No data available")

    buyer_data = data.groupby('Buyer').agg({
        'Metric Tons': 'sum',
        'Total calculated value ($)': 'sum',
        'Val/KG ($)': 'mean'
    }).sort_values('Metric Tons', ascending=False).head(8)

    fig = px.bar(
        x=buyer_data.index,
        y=buyer_data['Metric Tons'],
        title="Top 8 Buyers by Volume",
        labels={'x': 'Buyer', 'y': 'Volume (MT)'}
    )

    fig.update_traces(
        marker=dict(
            color=buyer_data['Total calculated value ($)'],
            colorscale=[[0, COLORS['light_blue']], [1, COLORS['light_green']]],
            showscale=True,
            colorbar=dict(title="Value ($)", titlefont=dict(color=COLORS['light_gray']),
                          tickfont=dict(color=COLORS['light_gray']))
        ),
        hovertemplate="<b>%{x}</b><br>Volume: %{y:,.1f} MT<br>Value: $%{customdata[0]:,.0f}<br>Price/KG: $%{customdata[1]:.2f}<extra></extra>",
        customdata=buyer_data[['Total calculated value ($)', 'Val/KG ($)']].values
    )

    fig.update_layout(
        plot_bgcolor=COLORS['night_black'],
        paper_bgcolor=COLORS['night_black'],
        font_color=COLORS['light_gray'],
        title_font_size=18,
        title_font_color=COLORS['light_gray'],
        title_font_family='Montserrat',
        xaxis_tickangle=-45,
        height=400,
        margin=dict(l=50, r=50, t=60, b=100)
    )

    return fig


def create_seller_analysis_chart(data):
    """Top 8 sellers with blue-green gradient - SMART FILTERING"""
    if len(data) == 0:
        return px.bar(title="No data available")

    seller_data = data.groupby('Seller').agg({
        'Metric Tons': 'sum',
        'Total calculated value ($)': 'sum',
        'Val/KG ($)': 'mean'
    }).sort_values('Metric Tons', ascending=False).head(8)

    fig = px.bar(
        x=seller_data.index,
        y=seller_data['Metric Tons'],
        title="Top 8 Suppliers by Volume",
        labels={'x': 'Supplier', 'y': 'Volume (MT)'}
    )

    fig.update_traces(
        marker=dict(
            color=seller_data['Total calculated value ($)'],
            colorscale=[[0, COLORS['light_blue']], [1, COLORS['light_green']]],
            showscale=True,
            colorbar=dict(title="Value ($)", titlefont=dict(color=COLORS['light_gray']),
                          tickfont=dict(color=COLORS['light_gray']))
        ),
        hovertemplate="<b>%{x}</b><br>Volume: %{y:,.1f} MT<br>Value: $%{customdata[0]:,.0f}<br>Price/KG: $%{customdata[1]:.2f}<extra></extra>",
        customdata=seller_data[['Total calculated value ($)', 'Val/KG ($)']].values
    )

    fig.update_layout(
        plot_bgcolor=COLORS['night_black'],
        paper_bgcolor=COLORS['night_black'],
        font_color=COLORS['light_gray'],
        title_font_size=18,
        title_font_color=COLORS['light_gray'],
        title_font_family='Montserrat',
        xaxis_tickangle=-45,
        height=400,
        margin=dict(l=50, r=50, t=60, b=100)
    )

    return fig


def create_category_pie_chart(data):
    """Top 4 categories EXCLUDING CATH - PIE CHART"""
    if len(data) == 0:
        return px.pie(title="No data available")

    non_cath_data = data[data['Category'] != 'CATH']
    category_data = non_cath_data.groupby('Category')['Metric Tons'].sum().sort_values(ascending=False).head(4)

    if len(category_data) == 0:
        return px.pie(title="No non-cathode data available")

    category_labels = [CODE_TO_DESCRIPTION.get(cat, cat) for cat in category_data.index]

    fig = px.pie(
        values=category_data.values,
        names=category_labels,
        title="Top 4 Import Categories (Excluding Cathode)",
        color_discrete_sequence=CHART_COLORS[:4]
    )

    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Volume: %{value:,.1f} MT<br>Percentage: %{percent}<extra></extra>",
        textinfo='label+percent',
        textposition='inside',
        textfont_size=12
    )

    fig.update_layout(
        plot_bgcolor=COLORS['night_black'],
        paper_bgcolor=COLORS['night_black'],
        font_color=COLORS['light_gray'],
        title_font_size=18,
        title_font_color=COLORS['light_gray'],
        title_font_family='Montserrat',
        height=400,
        margin=dict(l=50, r=50, t=60, b=50)
    )

    return fig


def create_country_distribution_chart(data):
    """Top 8 countries with blue-green gradient"""
    if len(data) == 0:
        return px.bar(title="No data available")

    country_data = data.groupby('Country of Origin').agg({
        'Metric Tons': 'sum',
        'Total calculated value ($)': 'sum',
        'Date': 'count'
    }).rename(columns={'Date': 'Transactions'}).sort_values('Metric Tons', ascending=False).head(8)

    fig = px.bar(
        x=country_data.index,
        y=country_data['Metric Tons'],
        title="Top 8 Countries by Volume",
        labels={'x': 'Country', 'y': 'Volume (MT)'}
    )

    fig.update_traces(
        marker=dict(
            color=country_data['Total calculated value ($)'],
            colorscale=[[0, COLORS['light_blue']], [1, COLORS['light_green']]],
            showscale=True,
            colorbar=dict(title="Value ($)", titlefont=dict(color=COLORS['light_gray']),
                          tickfont=dict(color=COLORS['light_gray']))
        ),
        hovertemplate="<b>%{x}</b><br>Volume: %{y:,.1f} MT<br>Value: $%{customdata[0]:,.0f}<br>Transactions: %{customdata[1]:,}<extra></extra>",
        customdata=country_data[['Total calculated value ($)', 'Transactions']].values
    )

    fig.update_layout(
        plot_bgcolor=COLORS['night_black'],
        paper_bgcolor=COLORS['night_black'],
        font_color=COLORS['light_gray'],
        title_font_size=18,
        title_font_color=COLORS['light_gray'],
        title_font_family='Montserrat',
        xaxis_tickangle=-45,
        height=400,
        margin=dict(l=50, r=50, t=60, b=100)
    )

    return fig


def create_time_series_chart(data):
    """Time series analysis with blue-green gradient"""
    if len(data) == 0:
        return px.line(title="No data available")

    monthly_data = data.groupby(data['Date'].dt.to_period('M')).agg({
        'Metric Tons': 'sum',
        'Total calculated value ($)': 'sum'
    })

    if len(monthly_data) == 0:
        return px.line(title="No time series data available")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=[str(period) for period in monthly_data.index],
        y=monthly_data['Metric Tons'],
        mode='lines+markers',
        name='Volume (MT)',
        line=dict(color=COLORS['light_blue'], width=3),
        marker=dict(size=8, color=COLORS['light_blue']),
        hovertemplate="<b>%{x}</b><br>Volume: %{y:,.1f} MT<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=[str(period) for period in monthly_data.index],
        y=monthly_data['Total calculated value ($)'] / 1000000,
        mode='lines+markers',
        name='Value ($M)',
        yaxis='y2',
        line=dict(color=COLORS['light_green'], width=3),
        marker=dict(size=8, color=COLORS['light_green']),
        hovertemplate="<b>%{x}</b><br>Value: $%{y:.1f}M<extra></extra>"
    ))

    fig.update_layout(
        title="Volume and Value Trends Over Time",
        plot_bgcolor=COLORS['night_black'],
        paper_bgcolor=COLORS['night_black'],
        font_color=COLORS['light_gray'],
        title_font_size=18,
        title_font_color=COLORS['light_gray'],
        title_font_family='Montserrat',
        xaxis=dict(title="Month", color=COLORS['light_gray']),
        yaxis=dict(title="Volume (MT)", side="left", color=COLORS['light_gray']),
        yaxis2=dict(title="Value ($M)", side="right", overlaying="y", color=COLORS['light_gray']),
        legend=dict(x=0.01, y=0.99),
        height=400,
        margin=dict(l=50, r=50, t=60, b=50)
    )

    return fig


def create_hs_code_analysis_chart(data):
    """HS Code analysis with blue-green gradient"""
    if len(data) == 0:
        return px.bar(title="No data available")

    hs_data = data.groupby('HS Code').agg({
        'Metric Tons': 'sum',
        'Total calculated value ($)': 'sum'
    }).sort_values('Metric Tons', ascending=False)

    fig = px.bar(
        x=hs_data.index,
        y=hs_data['Metric Tons'],
        title="Trade Volume by HS Code",
        labels={'x': 'HS Code', 'y': 'Volume (MT)'}
    )

    fig.update_traces(
        marker=dict(
            color=hs_data['Total calculated value ($)'],
            colorscale=[[0, COLORS['light_blue']], [1, COLORS['light_green']]],
            showscale=True,
            colorbar=dict(title="Value ($)", titlefont=dict(color=COLORS['light_gray']),
                          tickfont=dict(color=COLORS['light_gray']))
        ),
        hovertemplate="<b>HS Code: %{x}</b><br>Volume: %{y:,.1f} MT<br>Value: $%{customdata:,.0f}<extra></extra>",
        customdata=hs_data['Total calculated value ($)'].values
    )

    fig.update_layout(
        plot_bgcolor=COLORS['night_black'],
        paper_bgcolor=COLORS['night_black'],
        font_color=COLORS['light_gray'],
        title_font_size=18,
        title_font_color=COLORS['light_gray'],
        title_font_family='Montserrat',
        height=400,
        margin=dict(l=50, r=50, t=60, b=50)
    )

    return fig


# PERFECT PROTECTED LAYOUT WITH ALL YOUR REQUIREMENTS
def create_protected_layout():
    """Main dashboard layout - EXACTLY as you specified"""

    # Create filter options with proper data handling
    try:
        buyer_options = [{'label': buyer, 'value': buyer} for buyer in sorted(df['Buyer'].dropna().unique()) if
                         buyer != 'Unknown' and str(buyer) != 'nan']
        seller_options = [{'label': seller, 'value': seller} for seller in sorted(df['Seller'].dropna().unique()) if
                          str(seller) != 'nan']

        hs_codes = [str(hs) for hs in df['HS Code'].dropna().unique() if str(hs) != 'nan']
        hs_code_options = [{'label': hs, 'value': hs} for hs in sorted(hs_codes)]

        country_options = [{'label': country, 'value': country} for country in
                           sorted(df['Country of Origin'].dropna().unique()) if str(country) != 'nan']

        # Enhanced category options with descriptions
        available_categories = [cat for cat in sorted(df['Category'].dropna().unique()) if str(cat) != 'nan']
        category_options = []
        for cat in available_categories:
            description = CODE_TO_DESCRIPTION.get(cat, cat)
            category_options.append({'label': description, 'value': cat})

        category_options = sorted(category_options, key=lambda x: x['label'])

    except Exception as e:
        print(f"Error creating filter options: {e}")
        buyer_options = seller_options = hs_code_options = country_options = category_options = []

    return html.Div([
        # PERFECT HEADER: Logo + Title + Buttons (EXACTLY as requested)
        html.Div([
            # LEFT SIDE: Logo + Title
            html.Div([
                html.Img(
                    src=LOGO_DATA,
                    style={
                        'height': '70px',
                        'width': 'auto',
                        'margin-right': '25px'
                    }
                ) if LOGO_DATA else html.Div(),
                html.H1(
                    "Maritime Imports Dashboard",
                    style={
                        'color': COLORS['light_gray'],
                        'font-size': '42px',
                        'font-weight': '700',
                        'margin': '0',
                        'font-family': 'Montserrat, sans-serif'
                    }
                )
            ], style={
                'display': 'flex',
                'align-items': 'center'
            }),

            # RIGHT SIDE: Welcome + Clear All Filters + Logout (SAME SIZE)
            html.Div([
                html.Span(
                    f"Welcome, {current_user.username if current_user.is_authenticated else 'User'}",
                    style={
                        'color': COLORS['light_gray'],
                        'font-size': '16px',
                        'margin-right': '25px',
                        'font-family': 'Montserrat, sans-serif',
                        'font-weight': '500'
                    }
                ),
                html.Button(
                    "Clear All Filters",
                    id="clear-all-btn",
                    style={
                        'background': f'linear-gradient(135deg, {COLORS["light_green"]} 0%, #1E8E00 100%)',
                        'color': COLORS['night_black'],
                        'border': 'none',
                        'padding': '12px 20px',
                        'border-radius': '8px',
                        'font-weight': '600',
                        'cursor': 'pointer',
                        'font-size': '14px',
                        'font-family': 'Montserrat, sans-serif',
                        'margin-right': '15px',
                        'min-width': '140px',
                        'height': '44px'
                    }
                ),
                html.A(
                    "Logout",
                    href="/logout",
                    style={
                        'background': 'linear-gradient(135deg, #FF6B6B 0%, #FF5252 100%)',
                        'color': 'white',
                        'border': 'none',
                        'padding': '12px 20px',
                        'border-radius': '8px',
                        'font-weight': '600',
                        'cursor': 'pointer',
                        'font-size': '14px',
                        'text-decoration': 'none',
                        'font-family': 'Montserrat, sans-serif',
                        'display': 'inline-block',
                        'text-align': 'center',
                        'min-width': '140px',
                        'height': '44px',
                        'line-height': '20px'
                    }
                )
            ], style={
                'display': 'flex',
                'align-items': 'center'
            })
        ], style={
            'background': COLORS['night_black'],
            'padding': '25px 30px',
            'display': 'flex',
            'align-items': 'center',
            'justify-content': 'space-between',
            'border-bottom': f'3px solid {COLORS["dark_gray"]}',
            'box-shadow': '0 4px 20px rgba(0,0,0,0.4)',
            'font-family': 'Montserrat, sans-serif'
        }),

        # PERFECT FILTERS ROW - ALL ON SAME ROW, SMALLER TO FIT
        html.Div([
            html.Div([
                html.Div([
                    html.Label("Start Date", style={
                        'color': COLORS['light_gray'],
                        'font-weight': '600',
                        'margin-bottom': '8px',
                        'font-size': '14px',
                        'font-family': 'Montserrat, sans-serif'
                    }),
                    dcc.Input(
                        id="start-date",
                        type="text",
                        placeholder="MM/DD/YYYY",
                        value="",
                        style={
                            'width': '100%',
                            'background-color': COLORS['dark_gray'],
                            'border': f'2px solid {COLORS["dark_gray"]}',
                            'color': COLORS['light_gray'],
                            'padding': '8px 10px',
                            'border-radius': '6px',
                            'font-size': '12px',
                            'font-family': 'Montserrat, sans-serif'
                        }
                    ),
                    html.Button("Clear", id="clear-start-date", style={
                        'background': f'linear-gradient(135deg, {COLORS["light_green"]} 0%, #1E8E00 100%)',
                        'color': COLORS['night_black'],
                        'border': 'none',
                        'padding': '4px 8px',
                        'border-radius': '4px',
                        'font-weight': '600',
                        'cursor': 'pointer',
                        'font-size': '10px',
                        'margin-top': '4px',
                        'font-family': 'Montserrat, sans-serif'
                    })
                ], style={'display': 'flex', 'flex-direction': 'column'}),

                html.Div([
                    html.Label("End Date", style={
                        'color': COLORS['light_gray'],
                        'font-weight': '600',
                        'margin-bottom': '8px',
                        'font-size': '14px',
                        'font-family': 'Montserrat, sans-serif'
                    }),
                    dcc.Input(
                        id="end-date",
                        type="text",
                        placeholder="MM/DD/YYYY",
                        value="",
                        style={
                            'width': '100%',
                            'background-color': COLORS['dark_gray'],
                            'border': f'2px solid {COLORS["dark_gray"]}',
                            'color': COLORS['light_gray'],
                            'padding': '8px 10px',
                            'border-radius': '6px',
                            'font-size': '12px',
                            'font-family': 'Montserrat, sans-serif'
                        }
                    ),
                    html.Button("Clear", id="clear-end-date", style={
                        'background': f'linear-gradient(135deg, {COLORS["light_green"]} 0%, #1E8E00 100%)',
                        'color': COLORS['night_black'],
                        'border': 'none',
                        'padding': '4px 8px',
                        'border-radius': '4px',
                        'font-weight': '600',
                        'cursor': 'pointer',
                        'font-size': '10px',
                        'margin-top': '4px',
                        'font-family': 'Montserrat, sans-serif'
                    })
                ], style={'display': 'flex', 'flex-direction': 'column'}),

                html.Div([
                    html.Label("Category", style={
                        'color': COLORS['light_gray'],
                        'font-weight': '600',
                        'margin-bottom': '8px',
                        'font-size': '14px',
                        'font-family': 'Montserrat, sans-serif'
                    }),
                    dcc.Dropdown(
                        id="category-filter",
                        options=category_options,
                        value=None,
                        placeholder="Categories...",
                        searchable=True,
                        clearable=True,
                        style={
                            'background-color': COLORS['dark_gray'],
                            'color': COLORS['light_gray'],
                            'font-family': 'Montserrat, sans-serif',
                            'font-size': '12px'
                        }
                    ),
                    html.Button("Clear", id="clear-category", style={
                        'background': f'linear-gradient(135deg, {COLORS["light_green"]} 0%, #1E8E00 100%)',
                        'color': COLORS['night_black'],
                        'border': 'none',
                        'padding': '4px 8px',
                        'border-radius': '4px',
                        'font-weight': '600',
                        'cursor': 'pointer',
                        'font-size': '10px',
                        'margin-top': '4px',
                        'font-family': 'Montserrat, sans-serif'
                    })
                ], style={'display': 'flex', 'flex-direction': 'column'}),

                html.Div([
                    html.Label("Buyer", style={
                        'color': COLORS['light_gray'],
                        'font-weight': '600',
                        'margin-bottom': '8px',
                        'font-size': '14px',
                        'font-family': 'Montserrat, sans-serif'
                    }),
                    dcc.Dropdown(
                        id="buyer-filter",
                        options=buyer_options,
                        value=None,
                        placeholder="Buyers...",
                        searchable=True,
                        clearable=True,
                        style={
                            'background-color': COLORS['dark_gray'],
                            'color': COLORS['light_gray'],
                            'font-family': 'Montserrat, sans-serif',
                            'font-size': '12px'
                        }
                    ),
                    html.Button("Clear", id="clear-buyer", style={
                        'background': f'linear-gradient(135deg, {COLORS["light_green"]} 0%, #1E8E00 100%)',
                        'color': COLORS['night_black'],
                        'border': 'none',
                        'padding': '4px 8px',
                        'border-radius': '4px',
                        'font-weight': '600',
                        'cursor': 'pointer',
                        'font-size': '10px',
                        'margin-top': '4px',
                        'font-family': 'Montserrat, sans-serif'
                    })
                ], style={'display': 'flex', 'flex-direction': 'column'}),

                html.Div([
                    html.Label("Seller", style={
                        'color': COLORS['light_gray'],
                        'font-weight': '600',
                        'margin-bottom': '8px',
                        'font-size': '14px',
                        'font-family': 'Montserrat, sans-serif'
                    }),
                    dcc.Dropdown(
                        id="seller-filter",
                        options=seller_options,
                        value=None,
                        placeholder="Sellers...",
                        searchable=True,
                        clearable=True,
                        style={
                            'background-color': COLORS['dark_gray'],
                            'color': COLORS['light_gray'],
                            'font-family': 'Montserrat, sans-serif',
                            'font-size': '12px'
                        }
                    ),
                    html.Button("Clear", id="clear-seller", style={
                        'background': f'linear-gradient(135deg, {COLORS["light_green"]} 0%, #1E8E00 100%)',
                        'color': COLORS['night_black'],
                        'border': 'none',
                        'padding': '4px 8px',
                        'border-radius': '4px',
                        'font-weight': '600',
                        'cursor': 'pointer',
                        'font-size': '10px',
                        'margin-top': '4px',
                        'font-family': 'Montserrat, sans-serif'
                    })
                ], style={'display': 'flex', 'flex-direction': 'column'}),

                html.Div([
                    html.Label("HS Code", style={
                        'color': COLORS['light_gray'],
                        'font-weight': '600',
                        'margin-bottom': '8px',
                        'font-size': '14px',
                        'font-family': 'Montserrat, sans-serif'
                    }),
                    dcc.Dropdown(
                        id="hs-code-filter",
                        options=hs_code_options,
                        value=None,
                        placeholder="HS Codes...",
                        searchable=True,
                        clearable=True,
                        style={
                            'background-color': COLORS['dark_gray'],
                            'color': COLORS['light_gray'],
                            'font-family': 'Montserrat, sans-serif',
                            'font-size': '12px'
                        }
                    ),
                    html.Button("Clear", id="clear-hs-code", style={
                        'background': f'linear-gradient(135deg, {COLORS["light_green"]} 0%, #1E8E00 100%)',
                        'color': COLORS['night_black'],
                        'border': 'none',
                        'padding': '4px 8px',
                        'border-radius': '4px',
                        'font-weight': '600',
                        'cursor': 'pointer',
                        'font-size': '10px',
                        'margin-top': '4px',
                        'font-family': 'Montserrat, sans-serif'
                    })
                ], style={'display': 'flex', 'flex-direction': 'column'}),

                html.Div([
                    html.Label("Country", style={
                        'color': COLORS['light_gray'],
                        'font-weight': '600',
                        'margin-bottom': '8px',
                        'font-size': '14px',
                        'font-family': 'Montserrat, sans-serif'
                    }),
                    dcc.Dropdown(
                        id="country-filter",
                        options=country_options,
                        value=None,
                        placeholder="Countries...",
                        searchable=True,
                        clearable=True,
                        style={
                            'background-color': COLORS['dark_gray'],
                            'color': COLORS['light_gray'],
                            'font-family': 'Montserrat, sans-serif',
                            'font-size': '12px'
                        }
                    ),
                    html.Button("Clear", id="clear-country", style={
                        'background': f'linear-gradient(135deg, {COLORS["light_green"]} 0%, #1E8E00 100%)',
                        'color': COLORS['night_black'],
                        'border': 'none',
                        'padding': '4px 8px',
                        'border-radius': '4px',
                        'font-weight': '600',
                        'cursor': 'pointer',
                        'font-size': '10px',
                        'margin-top': '4px',
                        'font-family': 'Montserrat, sans-serif'
                    })
                ], style={'display': 'flex', 'flex-direction': 'column'}),
            ], style={
                'display': 'grid',
                'grid-template-columns': 'repeat(7, 1fr)',
                'gap': '15px',
                'align-items': 'start'
            })
        ], style={
            'background': COLORS['night_black'],
            'padding': '20px 30px',
            'border-bottom': f'2px solid {COLORS["dark_gray"]}'
        }),

        # KEY METRICS CARDS - THE DATA BAR YOU WANTED BACK
        html.Div(id="metric-cards", style={
            'display': 'grid',
            'grid-template-columns': 'repeat(4, 1fr)',
            'gap': '20px',
            'margin': '25px 30px',
            'background': COLORS['night_black']
        }),

        # 6 CHARTS SECTION - EXACTLY AS REQUESTED
        html.Div(id="charts-container", style={
            'display': 'grid',
            'grid-template-columns': 'repeat(3, 1fr)',
            'gap': '20px',
            'padding': '25px 30px',
            'background': COLORS['night_black']
        }),

        # Hidden div to store filtered data
        html.Div(id="filtered-data-store", style={'display': 'none'})

    ], style={
        'background-color': COLORS['night_black'],
        'color': COLORS['light_gray'],
        'font-family': 'Montserrat, sans-serif',
        'min-height': '100vh'
    })

    # MAIN APP LAYOUT WITH AUTHENTICATION
    # MAIN APP LAYOUT WITH AUTHENTICATION
    def serve_layout():
        """Serve appropriate layout based on authentication status"""
        # TEMPORARILY FORCE DASHBOARD FOR TESTING
        return create_protected_layout()  # Remove authentication check

        # Original code (comment out for now):
        # if current_user.is_authenticated:
        #     return create_protected_layout()
        # else:
        #     return create_login_layout()

    # Force layout directly
    app.layout = create_protected_layout()

    # AUTHENTICATION CALLBACKS
    @app.callback(
        [Output('login-status', 'children'),
         Output('username-input', 'value'),
         Output('password-input', 'value')],
        [Input('login-button', 'n_clicks')],
        [State('username-input', 'value'),
         State('password-input', 'value')]
    )
    def handle_login(n_clicks, username, password):
        if n_clicks and username and password:
            if username in USERS_DB:
                if check_password_hash(USERS_DB[username]['password_hash'], password):
                    user = User(username, USERS_DB[username]['role'])
                    login_user(user)
                    return [
                        html.Div("✅ Login successful! Refreshing...",
                                 style={'color': COLORS['light_green'], 'font-weight': 'bold',
                                        'font-family': 'Montserrat, sans-serif'}),
                        "", ""
                    ]
                else:
                    return [
                        html.Div("❌ Invalid password!",
                                 style={'color': '#FF6B6B', 'font-weight': 'bold',
                                        'font-family': 'Montserrat, sans-serif'}),
                        username, ""
                    ]
            else:
                return [
                    html.Div("❌ User not found!",
                             style={'color': '#FF6B6B', 'font-weight': 'bold',
                                    'font-family': 'Montserrat, sans-serif'}),
                    "", ""
                ]
        return ["", username or "", password or ""]

    # LOGOUT ROUTE
    @server.route('/logout')
    def logout():
        logout_user()
        return redirect('/')

    # FILTER DATA FUNCTION
    def filter_data(df, start_date=None, end_date=None, buyer=None, seller=None,
                    hs_code=None, country=None, category=None):
        """Apply all filters to the dataframe"""
        filtered_df = df.copy()

        if start_date:
            start_parsed = parse_date_simple(start_date)
            if start_parsed:
                filtered_df = filtered_df[filtered_df['Date'].dt.date >= start_parsed]

        if end_date:
            end_parsed = parse_date_simple(end_date)
            if end_parsed:
                filtered_df = filtered_df[filtered_df['Date'].dt.date <= end_parsed]

        if buyer:
            filtered_df = filtered_df[filtered_df['Buyer'] == buyer]

        if seller:
            filtered_df = filtered_df[filtered_df['Seller'] == seller]

        if hs_code:
            filtered_df = filtered_df[filtered_df['HS Code'].astype(str) == str(hs_code)]

        if country:
            filtered_df = filtered_df[filtered_df['Country of Origin'] == country]

        if category:
            filtered_df = filtered_df[filtered_df['Category'] == category]

        return filtered_df

    # MAIN DASHBOARD CALLBACK - UPDATES EVERYTHING
    @app.callback(
        [Output('metric-cards', 'children'),
         Output('charts-container', 'children')],
        [Input('start-date', 'value'),
         Input('end-date', 'value'),
         Input('buyer-filter', 'value'),
         Input('seller-filter', 'value'),
         Input('hs-code-filter', 'value'),
         Input('country-filter', 'value'),
         Input('category-filter', 'value'),
         Input('clear-all-btn', 'n_clicks'),
         Input('clear-start-date', 'n_clicks'),
         Input('clear-end-date', 'n_clicks'),
         Input('clear-buyer', 'n_clicks'),
         Input('clear-seller', 'n_clicks'),
         Input('clear-hs-code', 'n_clicks'),
         Input('clear-country', 'n_clicks'),
         Input('clear-category', 'n_clicks')]
    )
    def update_dashboard(start_date, end_date, buyer_filter, seller_filter, hs_code_filter,
                         country_filter, category_filter, clear_all, clear_start, clear_end,
                         clear_buyer, clear_seller, clear_hs, clear_country, clear_cat):

        try:
            # Handle clear button clicks
            if ctx.triggered:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
                if button_id in ['clear-all-btn', 'clear-start-date', 'clear-end-date', 'clear-buyer',
                                 'clear-seller', 'clear-hs-code', 'clear-country', 'clear-category']:
                    if button_id == 'clear-all-btn':
                        start_date = end_date = buyer_filter = seller_filter = None
                        hs_code_filter = country_filter = category_filter = None
                    elif button_id == 'clear-start-date':
                        start_date = None
                    elif button_id == 'clear-end-date':
                        end_date = None
                    elif button_id == 'clear-buyer':
                        buyer_filter = None
                    elif button_id == 'clear-seller':
                        seller_filter = None
                    elif button_id == 'clear-hs-code':
                        hs_code_filter = None
                    elif button_id == 'clear-country':
                        country_filter = None
                    elif button_id == 'clear-category':
                        category_filter = None

            # Filter the data
            filtered_data = filter_data(df, start_date, end_date, buyer_filter, seller_filter,
                                        hs_code_filter, country_filter, category_filter)

            # Create metric cards
            if len(filtered_data) > 0:
                total_volume = filtered_data['Metric Tons'].sum()
                total_value = filtered_data['Total calculated value ($)'].sum()
                avg_price = filtered_data['Val/KG ($)'].mean()
                transaction_count = len(filtered_data)

                metric_cards = [
                    html.Div([
                        html.H3(f"{total_volume:,.0f}",
                                style={'color': COLORS['light_blue'], 'margin': '0', 'font-size': '28px',
                                       'font-family': 'Montserrat, sans-serif'}),
                        html.P("Metric Tons", style={'color': COLORS['light_gray'], 'margin': '5px 0 0 0',
                                                     'font-family': 'Montserrat, sans-serif'})
                    ], style={'background': COLORS['dark_gray'], 'padding': '20px', 'border-radius': '12px',
                              'text-align': 'center'}),

                    html.Div([
                        html.H3(f"${total_value:,.0f}",
                                style={'color': COLORS['light_green'], 'margin': '0', 'font-size': '28px',
                                       'font-family': 'Montserrat, sans-serif'}),
                        html.P("Total Value", style={'color': COLORS['light_gray'], 'margin': '5px 0 0 0',
                                                     'font-family': 'Montserrat, sans-serif'})
                    ], style={'background': COLORS['dark_gray'], 'padding': '20px', 'border-radius': '12px',
                              'text-align': 'center'}),

                    html.Div([
                        html.H3(f"${avg_price:.2f}",
                                style={'color': COLORS['purple'], 'margin': '0', 'font-size': '28px',
                                       'font-family': 'Montserrat, sans-serif'}),
                        html.P("Avg Price/KG", style={'color': COLORS['light_gray'], 'margin': '5px 0 0 0',
                                                      'font-family': 'Montserrat, sans-serif'})
                    ], style={'background': COLORS['dark_gray'], 'padding': '20px', 'border-radius': '12px',
                              'text-align': 'center'}),

                    html.Div([
                        html.H3(f"{transaction_count:,}",
                                style={'color': COLORS['light_blue'], 'margin': '0', 'font-size': '28px',
                                       'font-family': 'Montserrat, sans-serif'}),
                        html.P("Transactions", style={'color': COLORS['light_gray'], 'margin': '5px 0 0 0',
                                                      'font-family': 'Montserrat, sans-serif'})
                    ], style={'background': COLORS['dark_gray'], 'padding': '20px', 'border-radius': '12px',
                              'text-align': 'center'})
                ]
            else:
                metric_cards = [
                    html.Div([
                        html.H3("No Data", style={'color': COLORS['light_gray'], 'margin': '0',
                                                  'font-family': 'Montserrat, sans-serif'}),
                        html.P("Apply filters", style={'color': COLORS['light_gray'], 'margin': '5px 0 0 0',
                                                       'font-family': 'Montserrat, sans-serif'})
                    ], style={'background': COLORS['dark_gray'], 'padding': '20px', 'border-radius': '12px',
                              'text-align': 'center'})
                    for _ in range(4)
                ]

            # Create the 6 charts you requested
            try:
                charts = [
                    html.Div([
                        dcc.Graph(figure=create_buyer_analysis_chart(filtered_data), config={'displayModeBar': True})
                    ], style={'background': COLORS['night_black'], 'border-radius': '12px', 'padding': '15px'}),

                    html.Div([
                        dcc.Graph(figure=create_seller_analysis_chart(filtered_data), config={'displayModeBar': True})
                    ], style={'background': COLORS['night_black'], 'border-radius': '12px', 'padding': '15px'}),

                    html.Div([
                        dcc.Graph(figure=create_category_pie_chart(filtered_data), config={'displayModeBar': True})
                    ], style={'background': COLORS['night_black'], 'border-radius': '12px', 'padding': '15px'}),

                    html.Div([
                        dcc.Graph(figure=create_country_distribution_chart(filtered_data),
                                  config={'displayModeBar': True})
                    ], style={'background': COLORS['night_black'], 'border-radius': '12px', 'padding': '15px'}),

                    html.Div([
                        dcc.Graph(figure=create_time_series_chart(filtered_data), config={'displayModeBar': True})
                    ], style={'background': COLORS['night_black'], 'border-radius': '12px', 'padding': '15px'}),

                    html.Div([
                        dcc.Graph(figure=create_hs_code_analysis_chart(filtered_data), config={'displayModeBar': True})
                    ], style={'background': COLORS['night_black'], 'border-radius': '12px', 'padding': '15px'})
                ]

            except Exception as e:
                print(f"Error creating charts: {e}")
                charts = [
                    html.Div([
                        html.H3("Error creating charts", style={'color': COLORS['light_gray'], 'text-align': 'center',
                                                                'font-family': 'Montserrat, sans-serif'}),
                        html.P(str(e), style={'color': COLORS['light_gray'], 'text-align': 'center',
                                              'font-family': 'Montserrat, sans-serif'})
                    ], style={'background': COLORS['dark_gray'], 'padding': '20px', 'border-radius': '12px'})
                    for _ in range(6)
                ]

            return metric_cards, charts

        except Exception as e:
            print(f"Dashboard error: {e}")

            error_cards = [
                html.Div([
                    html.H3("Error", style={'color': COLORS['light_gray'], 'margin': '0',
                                            'font-family': 'Montserrat, sans-serif'}),
                    html.P("Dashboard Error", style={'color': COLORS['light_gray'], 'margin': '5px 0 0 0',
                                                     'font-family': 'Montserrat, sans-serif'})
                ], style={'background': COLORS['dark_gray'], 'padding': '20px', 'border-radius': '12px',
                          'text-align': 'center'})
                for _ in range(4)
            ]

            error_charts = [
                html.Div([
                    html.H3("Error loading chart", style={'color': COLORS['light_gray'], 'text-align': 'center',
                                                          'font-family': 'Montserrat, sans-serif'})
                ], style={'background': COLORS['dark_gray'], 'padding': '20px', 'border-radius': '12px'})
                for _ in range(6)
            ]

            return error_cards, error_charts

    # CSS STYLING - FORCES NIGHT BLACK EVERYWHERE
    app.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
            <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
            <style>
                * {
                    font-family: 'Montserrat', sans-serif !important;
                    box-sizing: border-box;
                }
                body, html {
                    background-color: #191B27 !important;
                    margin: 0;
                    padding: 0;
                    color: #DCE4F2 !important;
                }
                .Select-control, .Select-menu-outer, .Select-option {
                    background-color: #2D354A !important;
                    color: #DCE4F2 !important;
                    border-color: #2D354A !important;
                }
                .dash-dropdown .Select-value-label {
                    color: #DCE4F2 !important;
                }
                .dash-dropdown .Select-placeholder {
                    color: #DCE4F2 !important;
                }
            </style>
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    '''

    # SERVER SETUP
    server = app.server

    if __name__ == '__main__':
        app.run_server(debug=False, host='0.0.0.0', port=8050)