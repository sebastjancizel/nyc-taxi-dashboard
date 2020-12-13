import base64
import datetime
import io
import numpy as np
import pandas as pd
import calendar
import json
import markdown
import os
import vaex
# plotly components
import plotly
import plotly.graph_objs as go
import plotly.express as px
import plotly.offline as offline
from plotly.graph_objs import Scatter, Figure, Layout
# import dash components
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import dash_bootstrap_components as dbc

external_stylesheets = [dbc.themes.COSMO]

app = dash.Dash(__name__,
                external_stylesheets=external_stylesheets,
                meta_tags=[
                    {"name": "viewport", "content": "width=device-width, initial-scale=1"},
                ])

app.title = "NYC Taxi Data Dash"

server = app.server

# Mapbox access token and the map style file
TOKEN = open(".mapbox_token").read()
STYLE_FILE = "mapbox://styles/scizel/ckhhw5ql12qs219pbajeadpss"
px.set_mapbox_access_token(TOKEN)


geo_filename = 'aux_data/taxi_zones-tiny.json'
with open(geo_filename) as f:
    geo_json = json.load(f)
zone_filename = 'aux_data/zone.json'
with open(zone_filename) as f:
    zmapper = json.load(f)
with open('aux_data/borough.json', 'rb') as f:
    bmapper = json.load(f)
with open('aux_data/zone_to_borough.json', 'rb') as f:
    zbmapper = json.load(f)

data_filename = 'aux_data/zone_data.json'
with open(data_filename, 'r') as f:
    ZONE_DATA = {int(zone): data for zone, data in json.load(f).items()}


DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

CHART_LAYOUT = dict(
    title=None,
    margin={"r": 0, "l": 0, "b": 0, "t": 0},
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
)

with open("README.md", 'r') as f:
    DESCRIPTION = f.read() 

#
#   Define chart builder functions
#

# NYC MAP


def create_figure_geomap(pickup_counts, zoom=10, center={"lat": 40.7, "lon": -73.99}):
    geomap_data = {
        'count': pickup_counts,
        'log_count': np.log10(pickup_counts),
        'zone_name': list(zmapper.values())
    }
    fig = px.choropleth_mapbox(geomap_data,
                               geojson=geo_json,
                               color="log_count",
                               color_continuous_scale="RdYlBu_r",
                               locations="zone_name",
                               featureidkey="properties.zone",
                               mapbox_style=STYLE_FILE,
                               hover_data=['count'],
                               zoom=zoom,
                               center=center,
                               opacity=0.7,
                               )
    # Custom tool-tip
    hovertemplate = '<br>Zone: %{location}' \
                    '<br>Number of trips: %{customdata:.3s}'
    fig.data[0]['hovertemplate'] = hovertemplate

    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0},
                      coloraxis_showscale=False, showlegend=False, clickmode='event+select')
    return fig

# RIDES PER DAY


def create_daily_plot(daily):

    weekly_fig = px.bar(x=DAYS, y=daily)
    weekly_fig.update_yaxes(zeroline=True, showgrid=True,
                            gridwidth=.5, gridcolor='#d5d5d5')

    weekly_fig.update_layout(CHART_LAYOUT)

    weekly_fig.update_layout(
        yaxis=dict(tickformat=".1%", title=None),
        xaxis=dict(title=None),
    )
    return weekly_fig

# RIDES PER HOUR


def create_hourly_plot(hourly):
    hourly_fig = px.area(hourly)

    hourly_fig.update_yaxes(zeroline=True, showgrid=True,
                            gridwidth=.5, gridcolor='#d5d5d5')

    hourly_fig.update_layout(CHART_LAYOUT)

    hourly_fig.update_layout(
        yaxis=dict(title=None, tickformat='.1%'),
        xaxis=dict(title=None),
        showlegend=False,
    )

    return hourly_fig


def create_destination_table(destinations):
    text_style = {'font-size':13}

    table_header = [html.Thead(
        html.Tr([html.Th("Zone", style=text_style), html.Th("%", style=text_style)]))]

    rows = []

    for zone, share in destinations.items():
        if zone != 'Other':
            row = html.Tr([html.Td(f"{zone}", style=text_style), html.Td(f"{share/10:.1%}", style=text_style)])
            rows.append(row)


    table_body = [html.Tbody(rows, className="w100")]

    return table_header + table_body

# AVERAGE FARE


def create_heatmap(heatmap):

    heatmap_fig = px.imshow(heatmap, x=list(range(24)),
                            y=DAYS, color_continuous_scale='RdYlBu')

    heatmap_fig.update_layout(CHART_LAYOUT)

    heatmap_fig.update_layout(
        coloraxis=dict(reversescale=True, showscale=False)
    )

    hovertemplate = '<br>Hour: %{x}' \
                    '<br>Day: %{y}' \
                    '<br>Price: %{z}'
    heatmap_fig.data[0]['hovertemplate'] = hovertemplate

    return heatmap_fig


#
#   INITIALIZE THE CHARTS
#

# Select the data for the entire city
data = ZONE_DATA.get(-1)  # -1 is code for the entire city
pickup_counts = data.get('pickup_counts')

# Create initial plot
chart = create_figure_geomap(pickup_counts)
daily = create_daily_plot(data.get('daily'))
hourly = create_hourly_plot(data.get('hourly'))
destinations = create_destination_table(data.get('destinations'))
heatmap = create_heatmap(data.get('heatmap'))


def build_graph_element(figure, title=None, id='', style=dict(), **kwargs):

    graph = dcc.Graph(
        figure=figure,
        id=id,
        style=style,
    )

    if title is not None:
        title_element = html.H6(title)
        content = [title_element, graph]
    else:
        content = graph

    return dbc.Card(
        dbc.CardBody(
            content
        ),
        color='light',
        outline=False,
    )


#
#   App layout
#
map = dbc.Card(
    dbc.CardBody(
        dcc.Graph(
            id='nyc_map',
            figure=chart,
            style={'height': '85vh'}
        ))
)

table = dbc.Card(
    [
        dbc.CardBody([
            html.H6("Top destination zones"),
            dbc.Table(
                destinations, bordered=False, size='sm', id='destinations', striped=True,
            )]
        )
    ], 
    color='light', outline=False
)


main_dash = dbc.Card(
    [
        dbc.CardHeader(
            children=[
                html.H4("New York City", id='zone-stats-header',
                        style={"float": "left"}),
                dbc.Button("Reset", id='reset-button', outline=True,
                           color='secondary', style={"float": "right"})
            ],
        ),
        dbc.CardBody(
            [
                dbc.CardDeck(
                    [
                        build_graph_element(
                            daily, id='daily', title="Rides per day compared to average", style={
                                'height': '25vh'}),
                        build_graph_element(
                            hourly, id='hourly', title="Ride frequency throughout the day", style={'height': '25vh'})
                    ],
                    className="mb-3"
                ),
                dbc.CardDeck([
                    build_graph_element(
                        heatmap, id='heatmap', title='Average total fare', style={'height': '25vh'}),
                    table]),
            ]
        )
    ]
)

BUTTON_STYLE = dict(style={"color": "grey"})


# Navigation buttons
navbar = dbc.Navbar([
    dbc.NavbarBrand(html.H2("NYC Taxi Dashboard")),
    dbc.NavbarToggler(id="navbar-toggler"),
    dbc.Collapse(dbc.Nav(
        [
            dbc.NavItem(dbc.NavLink("Description", id='description-button',
                                    active=True, href="#", **BUTTON_STYLE)),
            dbc.NavItem(dbc.NavLink("Dataset", href="#", **BUTTON_STYLE)),
            dbc.NavItem(dbc.NavLink(
                "Repository", href="https://github.com/sebastjancizel/nyc-taxi-dashboard", **BUTTON_STYLE)),
        ],
        style={'color': 'grey'}, fill=True, 
    ),
    id='navbar-collapse', navbar=True) 
])
description = dbc.Modal(
    [
        dbc.ModalHeader("Description"),
        dbc.ModalBody(dcc.Markdown(DESCRIPTION)),
        dbc.ModalFooter(
            dbc.Button("Close", id="close-description")
        )
    ],
    id="description",
    size="xl"
)

content = html.Div(
    dbc.Card(
        [
            dbc.CardBody(
                dbc.CardDeck(
                    [
                        map,
                        main_dash
                    ]
                ))
        ],
        id='content'
    )
)


app.layout = html.Div(children=[dcc.Location(
    id="url"), navbar, content, description])

#
# CALLBACKS
#

# Chart update
@app.callback(
    Output('zone-stats-header', 'children'),
    Output('daily', 'figure'),
    Output('hourly', 'figure'),
    Output('destinations', 'children'),
    Output('heatmap', 'figure'),
    Input('nyc_map', 'clickData'),
    Input('reset-button', 'n_clicks')
)
def update_content(clickData, n_clicks):

    changed_id = dash.callback_context.triggered[0]

    if 'reset-button.n_clicks' == changed_id.get('prop_id', ''):
        zone = -1  # Get aggregate data
    else:
        zone = clickData['points'][0]['pointNumber'] if clickData is not None else -1
    data = ZONE_DATA.get(zone)
    daily = create_daily_plot(data.get('daily'))
    hourly = create_hourly_plot(data.get('hourly'))
    destinations = create_destination_table(data.get('destinations'))
    heatmap = create_heatmap(data.get('heatmap'))

    zone_name = data['name'] if clickData is not None else "New York City"
    return zone_name, daily, hourly, destinations, heatmap

# Toggle description 
@app.callback(
    Output('description', 'is_open'),
    [Input('description-button', 'n_clicks'),
     Input('close-description', 'n_clicks')],
    [State('description', 'is_open')]
)
def toggle_description(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

# Control the collapse of navbar on small screens
@app.callback(
    Output("navbar-collapse", "is_open"),
    [Input("navbar-toggler", "n_clicks")],
    [State("navbar-collapse", "is_open")],
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


if __name__ == '__main__':
    app.run_server(debug=True, port=8080)
