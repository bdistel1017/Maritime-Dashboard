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
server = Flask(__name__)
server.secret_key = os.environ.get('SECRET_KEY', 'pry-maritime-dashboard-secret-2024-production')

# Initialize Dash app with Flask server
app = dash.Dash(__name__, server=server, suppress_callback_exceptions=True)
app.title = "Maritime Trade Analytics - PRY Dashboard"

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = '/login'

# Color Palette
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
        # Try MM/DD/YYYY first
        return datetime.strptime(date_string.strip(), '%m/%d/%Y').date()
    except:
        try:
            # Try M/D/YYYY
            return datetime.strptime(date_string.strip(), '%m/%d/%Y').date()
        except:
            try:
                # Try MM-DD-YYYY
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
                html.H1("PRY Maritime Trade Analytics", style={
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
                        'font-family': 'Montserrat, sans-serif',
                        'transition': 'all 0.3s ease'
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


# ENHANCED CHART FUNCTIONS WITH CLICKABLE MODALS
def create_buyer_analysis_chart(data):
    """Top 8 buyers with blue-green gradient - CLICKABLE"""
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
        title="Top 8 Buyers by Volume (Click to View Full Size)",
        labels={'x': 'Buyer', 'y': 'Volume (MT)'},
        hover_data={'Total calculated value ($)': ':,.0f', 'Val/KG ($)': ':.2f'}
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
        paper_bgcolor=COLORS['dark_gray'],
        font_color=COLORS['light_gray'],
        title_font_size=16,
        title_font_color=COLORS['light_gray'],
        xaxis_tickangle=-45,
        height=400,
        margin=dict(l=50, r=50, t=60, b=50)
    )

    return fig


def create_seller_analysis_chart(data):
    """Top 8 sellers with blue-green gradient - CLICKABLE"""
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
        title="Top 8 Suppliers by Volume (Click to View Full Size)",
        labels={'x': 'Supplier', 'y': 'Volume (MT)'},
        hover_data={'Total calculated value ($)': ':,.0f', 'Val/KG ($)': ':.2f'}
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
        paper_bgcolor=COLORS['dark_gray'],
        font_color=COLORS['light_gray'],
        title_font_size=16,
        title_font_color=COLORS['light_gray'],
        xaxis_tickangle=-45,
        height=400,
        margin=dict(l=50, r=50, t=60, b=50)
    )

    return fig


def create_country_distribution_chart(data):
    """Top 8 countries with blue-green gradient - CLICKABLE"""
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
        title="Top 8 Countries by Volume (Click to View Full Size)",
        labels={'x': 'Country', 'y': 'Volume (MT)'},
        hover_data={'Total calculated value ($)': ':,.0f', 'Transactions': ':,'}
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
        paper_bgcolor=COLORS['dark_gray'],
        font_color=COLORS['light_gray'],
        title_font_size=16,
        title_font_color=COLORS['light_gray'],
        xaxis_tickangle=-45,
        height=400,
        margin=dict(l=50, r=50, t=60, b=50)
    )

    return fig


def create_category_pie_chart(data):
    """Top 3 categories EXCLUDING CATH - CLICKABLE"""
    if len(data) == 0:
        return px.pie(title="No data available")

    non_cath_data = data[data['Category'] != 'CATH']
    category_data = non_cath_data.groupby('Category')['Metric Tons'].sum().sort_values(ascending=False).head(3)

    if len(category_data) == 0:
        return px.pie(title="No non-cathode data available")

    category_labels = [CODE_TO_DESCRIPTION.get(cat, cat) for cat in category_data.index]

    fig = px.pie(
        values=category_data.values,
        names=category_labels,
        title="Top 3 Import Categories - Non-Cathode (Click to View Full Size)",
        color_discrete_sequence=CHART_COLORS[:3]
    )

    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Volume: %{value:,.1f} MT<br>Percentage: %{percent}<extra></extra>",
        textinfo='label+percent',
        textposition='inside'
    )

    fig.update_layout(
        plot_bgcolor=COLORS['night_black'],
        paper_bgcolor=COLORS['dark_gray'],
        font_color=COLORS['light_gray'],
        title_font_size=16,
        title_font_color=COLORS['light_gray'],
        height=400,
        margin=dict(l=50, r=50, t=60, b=50)
    )

    return fig


def create_time_series_chart(data):
    """Time series analysis - CLICKABLE"""
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
        title="Volume and Value Trends Over Time (Click to View Full Size)",
        plot_bgcolor=COLORS['night_black'],
        paper_bgcolor=COLORS['dark_gray'],
        font_color=COLORS['light_gray'],
        title_font_size=16,
        title_font_color=COLORS['light_gray'],
        xaxis=dict(title="Month", color=COLORS['light_gray']),
        yaxis=dict(title="Volume (MT)", side="left", color=COLORS['light_gray']),
        yaxis2=dict(title="Value ($M)", side="right", overlaying="y", color=COLORS['light_gray']),
        legend=dict(x=0.01, y=0.99),
        height=400,
        margin=dict(l=50, r=50, t=60, b=50)
    )

    return fig


def create_waterfall_chart(data):
    """Waterfall chart showing cumulative value by category - CLICKABLE"""
    if len(data) == 0:
        return go.Figure().add_annotation(text="No data available", x=0.5, y=0.5)

    category_data = data.groupby('Category')['Total calculated value ($)'].sum().sort_values(ascending=False).head(6)

    if len(category_data) == 0:
        return go.Figure().add_annotation(text="No category data available", x=0.5, y=0.5)

    category_labels = [CODE_TO_DESCRIPTION.get(cat, cat) for cat in category_data.index]
    categories = category_labels + ['Total']
    values = list(category_data.values) + [category_data.sum()]

    fig = go.Figure(go.Waterfall(
        name="Value Flow",
        orientation="v",
        measure=["relative"] * len(category_data) + ["total"],
        x=categories,
        textposition="outside",
        text=[f"${v / 1000000:.1f}M" for v in values],
        y=values,
        connector={"line": {"color": COLORS['light_gray']}},
        increasing={"marker": {"color": COLORS['light_green']}},
        decreasing={"marker": {"color": "#FF6B6B"}},
        totals={"marker": {"color": COLORS['light_blue']}},
        hovertemplate="<b>%{x}</b><br>Value: $%{y:,.0f}<extra></extra>"
    ))

    fig.update_layout(
        title="Value Waterfall by Category (Click to View Full Size)",
        plot_bgcolor=COLORS['night_black'],
        paper_bgcolor=COLORS['dark_gray'],
        font_color=COLORS['light_gray'],
        title_font_size=16,
        title_font_color=COLORS['light_gray'],
        xaxis_tickangle=-45,
        yaxis_title="Value ($)",
        height=400,
        margin=dict(l=50, r=50, t=60, b=50)
    )

    return fig


# PROTECTED MAIN LAYOUT
}def create_protected_layout():
    """Main dashboard layout - only accessible after login"""

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
        # Enhanced CSS with clickable graphs
        html.Style(children='''
            * { 
                font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, sans-serif !important;
                box-sizing: border-box;
            }
            # ... (lots more CSS) ...
        '''),
        ```

          ** REPLACE THE ENTIRE `html.Style(children='''` section with just:**
    ```python
    return html.Div([
        # Header with user info
    ```

    ## **OR EASIER - REPLACE THE WHOLE FUNCTION:**

    **Replace your entire `create_protected_layout` function with this:**

    ```python
    def create_protected_layout():
        """Main dashboard layout - only accessible after login"""

        # Create filter options with proper data handling
        try:
            buyer_options = [{'label': buyer, 'value': buyer} for buyer in sorted(df['Buyer'].dropna().unique()) if buyer != 'Unknown' and str(buyer) != 'nan']
            seller_options = [{'label': seller, 'value': seller} for seller in sorted(df['Seller'].dropna().unique()) if str(seller) != 'nan']

            hs_codes = [str(hs) for hs in df['HS Code'].dropna().unique() if str(hs) != 'nan']
            hs_code_options = [{'label': hs, 'value': hs} for hs in sorted(hs_codes)]

            country_options = [{'label': country, 'value': country} for country in sorted(df['Country of Origin'].dropna().unique()) if str(country) != 'nan']

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
            # Header with user info
            html.Div([
                html.Div([
                    html.Img(src=LOGO_DATA, style={'height': '70px', 'width': 'auto', 'margin-right': '25px'}) if LOGO_DATA else html.Div(),
                    html.H1("PRY Maritime Trade Analytics", style={'color': COLORS['light_gray'], 'font-size': '42px', 'font-weight': '700', 'margin': '0'})
                ], style={'display': 'flex', 'align-items': 'center'}),
                html.Div([
                    html.Span(f"Welcome, {current_user.username if current_user.is_authenticated else 'User'}", style={'color': COLORS['light_gray'], 'font-size': '14px', 'margin-right': '20px'}),
                    html.A("Logout", href="/logout", style={'background': 'linear-gradient(135deg, #FF6B6B 0%, #FF5252 100%)', 'color': 'white', 'border': 'none', 'padding': '10px 20px', 'border-radius': '8px', 'font-weight': '600', 'cursor': 'pointer', 'font-size': '14px', 'text-decoration': 'none', 'margin-left': '10px'}),
                    html.Button("Clear All Filters", id="clear-all-btn", style={'background': 'linear-gradient(135deg, #22C70C 0%, #1E8E00 100%)', 'color': COLORS['night_black'], 'border': 'none', 'padding': '15px 30px', 'border-radius': '12px', 'font-weight': '700', 'cursor': 'pointer', 'font-size': '16px'})
                ], style={'display': 'flex', 'align-items': 'center'})
            ], style={'background': COLORS['night_black'], 'padding': '25px 30px', 'display': 'flex', 'align-items': 'center', 'justify-content': 'space-between', 'border-bottom': f'3px solid {COLORS["dark_gray"]}'}),

            # Filters Section
            html.Div([
                html.Div([
                    html.Div([
                        html.Label("Start Date", style={'color': COLORS['light_gray'], 'font-weight': '600', 'margin-bottom': '10px', 'font-size': '16px'}),
                        dcc.Input(id="start-date", type="text", placeholder="MM/DD/YYYY", value="", style={'width': '100%', 'background-color': COLORS['dark_gray'], 'border': f'2px solid {COLORS["dark_gray"]}', 'color': COLORS['light_gray'], 'padding': '12px 15px', 'border-radius': '8px', 'font-size': '14px'}),
                        html.Button("Clear", id="clear-start-date", style={'background': 'linear-gradient(135deg, #22C70C 0%, #1E8E00 100%)', 'color': COLORS['night_black'], 'border': 'none', 'padding': '8px 16px', 'border-radius': '6px', 'font-weight': '600', 'cursor': 'pointer', 'font-size': '12px', 'margin-top': '8px'})
                    ], style={'display': 'flex', 'flex-direction': 'column'}),

                    html.Div([
                        html.Label("End Date", style={'color': COLORS['light_gray'], 'font-weight': '600', 'margin-bottom': '10px', 'font-size': '16px'}),
                        dcc.Input(id="end-date", type="text", placeholder="MM/DD/YYYY", value="", style={'width': '100%', 'background-color': COLORS['dark_gray'], 'border': f'2px solid {COLORS["dark_gray"]}', 'color': COLORS['light_gray'], 'padding': '12px 15px', 'border-radius': '8px', 'font-size': '14px'}),
                        html.Button("Clear", id="clear-end-date", style={'background': 'linear-gradient(135deg, #22C70C 0%, #1E8E00 100%)', 'color': COLORS['night_black'], 'border': 'none', 'padding': '8px 16px', 'border-radius': '6px', 'font-weight': '600', 'cursor': 'pointer', 'font-size': '12px', 'margin-top': '8px'})
                    ], style={'display': 'flex', 'flex-direction': 'column'}),

                    html.Div([
                        html.Label("Category", style={'color': COLORS['light_gray'], 'font-weight': '600', 'margin-bottom': '10px', 'font-size': '16px'}),
                        dcc.Dropdown(id="category-filter", options=category_options, value=None, placeholder="Search categories...", searchable=True, clearable=True),
                        html.Button("Clear", id="clear-category", style={'background': 'linear-gradient(135deg, #22C70C 0%, #1E8E00 100%)', 'color': COLORS['night_black'], 'border': 'none', 'padding': '8px 16px', 'border-radius': '6px', 'font-weight': '600', 'cursor': 'pointer', 'font-size': '12px', 'margin-top': '8px'})
                    ], style={'display': 'flex', 'flex-direction': 'column'}),

                    html.Div([
                        html.Label("Buyer", style={'color': COLORS['light_gray'], 'font-weight': '600', 'margin-bottom': '10px', 'font-size': '16px'}),
                        dcc.Dropdown(id="buyer-filter", options=buyer_options, value=None, placeholder="Search buyers...", searchable=True, clearable=True),
                        html.Button("Clear", id="clear-buyer", style={'background': 'linear-gradient(135deg, #22C70C 0%, #1E8E00 100%)', 'color': COLORS['night_black'], 'border': 'none', 'padding': '8px 16px', 'border-radius': '6px', 'font-weight': '600', 'cursor': 'pointer', 'font-size': '12px', 'margin-top': '8px'})
                    ], style={'display': 'flex', 'flex-direction': 'column'}),

                    html.Div([
                        html.Label("Seller", style={'color': COLORS['light_gray'], 'font-weight': '600', 'margin-bottom': '10px', 'font-size': '16px'}),
                        dcc.Dropdown(id="seller-filter", options=seller_options, value=None, placeholder="Search sellers...", searchable=True, clearable=True),
                        html.Button("Clear", id="clear-seller", style={'background': 'linear-gradient(135deg, #22C70C 0%, #1E8E00 100%)', 'color': COLORS['night_black'], 'border': 'none', 'padding': '8px 16px', 'border-radius': '6px', 'font-weight': '600', 'cursor': 'pointer', 'font-size': '12px', 'margin-top': '8px'})
                    ], style={'display': 'flex', 'flex-direction': 'column'}),

                    html.Div([
                        html.Label("HS Code", style={'color': COLORS['light_gray'], 'font-weight': '600', 'margin-bottom': '10px', 'font-size': '16px'}),
                        dcc.Dropdown(id="hs-code-filter", options=hs_code_options, value=None, placeholder="Search HS codes...", searchable=True, clearable=True),
                        html.Button("Clear", id="clear-hs-code", style={'background': 'linear-gradient(135deg, #22C70C 0%, #1E8E00 100%)', 'color': COLORS['night_black'], 'border': 'none', 'padding': '8px 16px', 'border-radius': '6px', 'font-weight': '600', 'cursor': 'pointer', 'font-size': '12px', 'margin-top': '8px'})
                    ], style={'display': 'flex', 'flex-direction': 'column'}),

                    html.Div([
                        html.Label("Country of Origin", style={'color': COLORS['light_gray'], 'font-weight': '600', 'margin-bottom': '10px', 'font-size': '16px'}),
                        dcc.Dropdown(id="country-filter", options=country_options, value=None, placeholder="Search countries...", searchable=True, clearable=True),
                        html.Button("Clear", id="clear-country", style={'background': 'linear-gradient(135deg, #22C70C 0%, #1E8E00 100%)', 'color': COLORS['night_black'], 'border': 'none', 'padding': '8px 16px', 'border-radius': '6px', 'font-weight': '600', 'cursor': 'pointer', 'font-size': '12px', 'margin-top': '8px'})
                    ], style={'display': 'flex', 'flex-direction': 'column'}),
                ], style={'display': 'grid', 'grid-template-columns': 'repeat(7, 1fr)', 'gap': '20px', 'align-items': 'start'})
            ], style={'background': COLORS['night_black'], 'padding': '25px 30px', 'border-bottom': f'2px solid {COLORS["dark_gray"]}'}),

            # Key Metrics Cards
            html.Div(id="metric-cards", style={'display': 'grid', 'grid-template-columns': 'repeat(4, 1fr)', 'gap': '25px', 'margin': '30px'}),

            # Charts Section
            html.Div(id="charts-container", style={'display': 'grid', 'grid-template-columns': 'repeat(3, 1fr)', 'gap': '25px', 'padding': '25px', 'background': COLORS['night_black']}),

            # Hidden div to store filtered data
            html.Div(id="filtered-data-store", style={'display': 'none'})
        ], style={'background-color': COLORS['night_black'], 'color': COLORS['light_gray'], 'font-family': 'Montserrat, sans-serif'})


# MAIN APP LAYOUT WITH AUTHENTICATION
def serve_layout():
    """Serve appropriate layout based on authentication status"""
    if current_user.is_authenticated:
        return create_protected_layout()
    else:
        return create_login_layout()


app.layout = serve_layout


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
                    html.Div("✅ Login successful! Redirecting...",
                             style={'color': COLORS['light_green'], 'font-weight': 'bold'}),
                    "", ""
                ]
            else:
                return [
                    html.Div("❌ Invalid password!",
                             style={'color': '#FF6B6B', 'font-weight': 'bold'}),
                    username, ""
                ]
        else:
            return [
                html.Div("❌ User not found!",
                         style={'color': '#FF6B6B', 'font-weight': 'bold'}),
                "", ""
            ]

    return ["", username or "", password or ""]


# ENHANCED PROTECTED CALLBACKS WITH BETTER ERROR HANDLING
@app.callback(
    [Output("filtered-data-store", "children"),
     Output("metric-cards", "children")],
    [Input("start-date", "value"),
     Input("end-date", "value"),
     Input("category-filter", "value"),
     Input("buyer-filter", "value"),
     Input("seller-filter", "value"),
     Input("hs-code-filter", "value"),
     Input("country-filter", "value")]
)
def update_filtered_data_and_metrics(start_date, end_date, category, buyer, seller, hs_code, country):
    """Enhanced filtering with proper validation"""
    if not current_user.is_authenticated:
        return "", []

    try:
        filtered_df = df.copy()

        # Apply date filters with enhanced validation
        if start_date and start_date.strip():
            try:
                start_parsed = parse_date_simple(start_date)
                if start_parsed:
                    filtered_df = filtered_df[filtered_df['Date'].dt.date >= start_parsed]
            except Exception as e:
                print(f"Error parsing start date: {e}")

        if end_date and end_date.strip():
            try:
                end_parsed = parse_date_simple(end_date)
                if end_parsed:
                    filtered_df = filtered_df[filtered_df['Date'].dt.date <= end_parsed]
            except Exception as e:
                print(f"Error parsing end date: {e}")

        # Apply categorical filters with validation
        if category and category in filtered_df['Category'].values:
            filtered_df = filtered_df[filtered_df['Category'] == category]

        # Smart buyer/seller logic with validation
        if buyer and seller:
            if buyer in filtered_df['Buyer'].values and seller in filtered_df['Seller'].values:
                filtered_df = filtered_df[(filtered_df['Buyer'] == buyer) & (filtered_df['Seller'] == seller)]
        elif buyer and buyer in filtered_df['Buyer'].values:
            filtered_df = filtered_df[filtered_df['Buyer'] == buyer]
        elif seller and seller in filtered_df['Seller'].values:
            filtered_df = filtered_df[filtered_df['Seller'] == seller]

        if hs_code and hs_code in filtered_df['HS Code'].astype(str).values:
            filtered_df = filtered_df[filtered_df['HS Code'].astype(str) == hs_code]

        if country and country in filtered_df['Country of Origin'].values:
            filtered_df = filtered_df[filtered_df['Country of Origin'] == country]

        # Calculate metrics with proper error handling
        total_transactions = len(filtered_df)
        total_volume = filtered_df['Metric Tons'].sum() if len(filtered_df) > 0 else 0
        total_value = filtered_df['Total calculated value ($)'].sum() if len(filtered_df) > 0 else 0
        avg_price = filtered_df['Val/KG ($)'].mean() if len(filtered_df) > 0 else 0

        # Handle NaN values
        if pd.isna(total_volume):
            total_volume = 0
        if pd.isna(total_value):
            total_value = 0
        if pd.isna(avg_price):
            avg_price = 0

        # Create enhanced metric cards
        metric_cards = [
            html.Div([
                html.H3(f"{total_transactions:,}", className="metric-value"),
                html.P("Total Transactions", className="metric-label")
            ], className="metric-card"),

            html.Div([
                html.H3(f"{total_volume:,.1f}", className="metric-value"),
                html.P("Metric Tons", className="metric-label")
            ], className="metric-card"),

            html.Div([
                html.H3(f"${total_value:,.0f}", className="metric-value"),
                html.P("Total Value", className="metric-label")
            ], className="metric-card"),

            html.Div([
                html.H3(f"${avg_price:.2f}", className="metric-value"),
                html.P("Avg Price/KG", className="metric-label")
            ], className="metric-card")
        ]

        return filtered_df.to_json(date_format='iso', orient='split'), metric_cards

    except Exception as e:
        print(f"Error in filtering: {e}")
        return df.to_json(date_format='iso', orient='split'), []


@app.callback(
    Output("charts-container", "children"),
    Input("filtered-data-store", "children")
)
def update_charts(filtered_data_json):
    """Update all charts with enhanced error handling"""
    if not current_user.is_authenticated:
        return []

    try:
        if not filtered_data_json:
            return create_default_charts()

        filtered_data = pd.read_json(filtered_data_json, orient='split')
        filtered_data['Date'] = pd.to_datetime(filtered_data['Date'])

        if len(filtered_data) == 0:
            return [html.Div("No data matches your current filters. Try adjusting your filter settings.",
                             style={
                                 'color': COLORS['light_gray'],
                                 'text-align': 'center',
                                 'padding': '50px',
                                 'grid-column': '1 / -1',
                                 'font-size': '18px',
                                 'background': f'linear-gradient(135deg, {COLORS["dark_gray"]} 0%, {COLORS["night_black"]} 100%)',
                                 'border-radius': '15px',
                                 'border': f'2px dashed {COLORS["light_blue"]}'
                             })]

        # Create all charts with error handling
        charts = []
        try:
            charts.append(html.Div([
                dcc.Graph(
                    figure=create_buyer_analysis_chart(filtered_data),
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToAdd': ['downloadPlot'],
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'buyer_analysis',
                            'height': 800,
                            'width': 1200,
                            'scale': 2
                        }
                    }
                )
            ], className="chart-item"))

            charts.append(html.Div([
                dcc.Graph(
                    figure=create_seller_analysis_chart(filtered_data),
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToAdd': ['downloadPlot'],
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'seller_analysis',
                            'height': 800,
                            'width': 1200,
                            'scale': 2
                        }
                    }
                )
            ], className="chart-item"))

            charts.append(html.Div([
                dcc.Graph(
                    figure=create_country_distribution_chart(filtered_data),
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToAdd': ['downloadPlot'],
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'country_distribution',
                            'height': 800,
                            'width': 1200,
                            'scale': 2
                        }
                    }
                )
            ], className="chart-item"))

            charts.append(html.Div([
                dcc.Graph(
                    figure=create_category_pie_chart(filtered_data),
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToAdd': ['downloadPlot'],
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'category_analysis',
                            'height': 800,
                            'width': 1200,
                            'scale': 2
                        }
                    }
                )
            ], className="chart-item"))

            charts.append(html.Div([
                dcc.Graph(
                    figure=create_time_series_chart(filtered_data),
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToAdd': ['downloadPlot'],
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'time_series',
                            'height': 800,
                            'width': 1200,
                            'scale': 2
                        }
                    }
                )
            ], className="chart-item"))

            charts.append(html.Div([
                dcc.Graph(
                    figure=create_waterfall_chart(filtered_data),
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToAdd': ['downloadPlot'],
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'waterfall_analysis',
                            'height': 800,
                            'width': 1200,
                            'scale': 2
                        }
                    }
                )
            ], className="chart-item"))

        except Exception as e:
            print(f"Error creating individual chart: {e}")
            charts.append(html.Div(f"Error creating chart: {str(e)}", style={'color': COLORS['light_gray']}))

        return charts

    except Exception as e:
        print(f"Error in update_charts: {e}")
        return [html.Div("Error loading charts. Please try refreshing the page.",
                         style={'color': '#FF6B6B', 'text-align': 'center', 'padding': '50px'})]


def create_default_charts():
    """Create default charts with full dataset"""
    if len(df) == 0:
        return [html.Div("No data available. Please check your data file.",
                         style={'color': COLORS['light_gray'], 'text-align': 'center', 'grid-column': '1 / -1'})]

    try:
        return [
            html.Div([dcc.Graph(figure=create_buyer_analysis_chart(df),
                                config={'displayModeBar': True, 'displaylogo': False})], className="chart-item"),
            html.Div([dcc.Graph(figure=create_seller_analysis_chart(df),
                                config={'displayModeBar': True, 'displaylogo': False})], className="chart-item"),
            html.Div([dcc.Graph(figure=create_country_distribution_chart(df),
                                config={'displayModeBar': True, 'displaylogo': False})], className="chart-item"),
            html.Div([dcc.Graph(figure=create_category_pie_chart(df),
                                config={'displayModeBar': True, 'displaylogo': False})], className="chart-item"),
            html.Div(
                [dcc.Graph(figure=create_time_series_chart(df), config={'displayModeBar': True, 'displaylogo': False})],
                className="chart-item"),
            html.Div(
                [dcc.Graph(figure=create_waterfall_chart(df), config={'displayModeBar': True, 'displaylogo': False})],
                className="chart-item")
        ]
    except Exception as e:
        print(f"Error creating default charts: {e}")
        return [html.Div("Error creating charts.", style={'color': COLORS['light_gray']})]


# CLEAR FILTER CALLBACKS
@app.callback(Output("start-date", "value"), Input("clear-start-date", "n_clicks"))
def clear_start_date(n_clicks):
    if n_clicks: return ""
    return dash.no_update


@app.callback(Output("end-date", "value"), Input("clear-end-date", "n_clicks"))
def clear_end_date(n_clicks):
    if n_clicks: return ""
    return dash.no_update


@app.callback(Output("category-filter", "value"), Input("clear-category", "n_clicks"))
def clear_category(n_clicks):
    if n_clicks: return None
    return dash.no_update


@app.callback(Output("buyer-filter", "value"), Input("clear-buyer", "n_clicks"))
def clear_buyer(n_clicks):
    if n_clicks: return None
    return dash.no_update


@app.callback(Output("seller-filter", "value"), Input("clear-seller", "n_clicks"))
def clear_seller(n_clicks):
    if n_clicks: return None
    return dash.no_update


@app.callback(Output("hs-code-filter", "value"), Input("clear-hs-code", "n_clicks"))
def clear_hs_code(n_clicks):
    if n_clicks: return None
    return dash.no_update


@app.callback(Output("country-filter", "value"), Input("clear-country", "n_clicks"))
def clear_country(n_clicks):
    if n_clicks: return None
    return dash.no_update


@app.callback(
    [Output("start-date", "value", allow_duplicate=True),
     Output("end-date", "value", allow_duplicate=True),
     Output("category-filter", "value", allow_duplicate=True),
     Output("buyer-filter", "value", allow_duplicate=True),
     Output("seller-filter", "value", allow_duplicate=True),
     Output("hs-code-filter", "value", allow_duplicate=True),
     Output("country-filter", "value", allow_duplicate=True)],
    Input("clear-all-btn", "n_clicks"),
    prevent_initial_call=True
)
def clear_all_filters(n_clicks):
    if n_clicks:
        return "", "", None, None, None, None, None
    return dash.no_update


# LOGOUT ROUTE
@server.route('/logout')
def logout():
    logout_user()
    return redirect('/')


# RUN THE APP
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))

    print("🌊 PRY MARITIME TRADE ANALYTICS DASHBOARD")
    print("🔐 HEROKU-READY WITH AUTHENTICATION")
    print("🖱️  CLICKABLE CHARTS WITH DOWNLOAD OPTIONS")
    print("=" * 60)
    print("👥 Your Custom Accounts:")
    print("   • bdistel17$$ / bad_bunny1017$$")
    print("   • cbarnard2025 / admin_equityinsight!")
    print("   • PRY_Admin / 382716!")
    print("=" * 60)
    print(f"🚀 Starting on port {port}")

    if len(df) > 0:
        print(f"✅ Loaded {len(df):,} transactions")
        print(f"📊 Date range: {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}")
        print(f"🌍 Countries: {len(df['Country of Origin'].unique())}")
        print(f"🏢 Buyers: {len(df['Buyer'].unique())}")
        print(f"🚢 Sellers: {len(df['Seller'].unique())}")
    else:
        print("⚠️  No data loaded - check PRY_Dash.xlsx file")

    app.run_server(debug=False, host='0.0.0.0', port=port)