import base64
import datetime
import io
import numpy as np
import pandas as pd
import calendar
import json
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
    ZONE_DATA = json.load(f)
#
#   Create Choropleth map
#


def create_figure_geomap(pickup_counts, zone=None, zoom=10, center={"lat": 40.7, "lon": -73.99}):
    geomap_data = {
        'count': pickup_counts,
        'log_count': np.log10(pickup_counts),
        'zone_name': list(zmapper.values())
    }
    fig = px.choropleth_mapbox(geomap_data,
                               geojson=geo_json,
                               color="log_count",
                               color_continuous_scale="magma",
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

    if zone is not None:
        # draw the selected zone
        geo_json_selected = geo_json.copy()
        geo_json_selected['features'] = [
            feature for feature in geo_json_selected['features'] if feature['properties']['zone'] == zone_index_to_name[zone]
        ]

        geomap_data_selected = {
            'zone_name': [
                geo_json_selected['features'][0]['properties']['zone'],
            ],
            'default_value': ['start'],
            'log_count': [geomap_data['log_count'][zone]],
            'count': [geomap_data['count'][zone]],
        }
        fig_temp = px.choropleth_mapbox(geomap_data_selected,
                                        geojson=geo_json_selected,
                                        color='default_value',
                                        locations="zone_name",
                                        featureidkey="properties.zone",
                                        mapbox_style=STYLE_FILE,
                                        hover_data=['count'],
                                        zoom=9,
                                        center={"lat": 40.7, "lon": -73.99},
                                        opacity=1.,
                                        )
        fig.add_trace(fig_temp.data[0])
        # Custom tool-tip
        hovertemplate = '<br>Zone: %{location}' \
                        '<br>Number of trips: %{customdata:.3s}' \
                        '<extra></extra>'
        fig.data[1]['hovertemplate'] = hovertemplate

    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0},
                      coloraxis_showscale=False, showlegend=False, clickmode='event+select', height=700)
    return fig


def create_daily_plot(daily):

    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    weekly_fig = px.bar(x=days, y=daily)
    weekly_fig.update_yaxes(zeroline=True, showgrid=True,
                            gridwidth=.5, gridcolor='#d5d5d5')
    weekly_fig.update_layout(
        yaxis=dict(tickformat=".1%", title=None),
        xaxis=dict(title=None),
        title='Distribution of rides per weekday',
        margin={"r": 0, "l": 0},
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    return weekly_fig


def create_hourly_plot(hourly):
    hourly_fig = px.area(hourly)

    hourly_fig.update_yaxes(zeroline=True, showgrid=True,
                            gridwidth=.5, gridcolor='#d5d5d5')

    hourly_fig.update_layout(
        yaxis=dict(title=None, tickformat='.1%'),
        xaxis=dict(title=None),
        title='Distribution of rides per weekday',
        margin={"r": 0, "l": 0, "b": 0},
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
    )

    return hourly_fig


#
#   Create charts
#

data = ZONE_DATA['-1']
pickup_counts = data.get('pickup_counts')
chart = create_figure_geomap(pickup_counts, zone=None)


daily = create_daily_plot(data.get('daily'))

hourly = create_hourly_plot(data.get('hourly'))

#
#   App layout
#
map = dbc.Card(
    dbc.CardBody(
        dcc.Graph(
            id='nyc_map',
            figure=chart
        ))
)


graphs = dbc.Card(
    [
        dbc.CardHeader(
            children=[html.H4("Zone Name", id='zone-stats-header')],
        ),
        dbc.CardBody(
            dbc.CardGroup(
            [
                dbc.Card(
                dcc.Graph(
                    id='daily',
                    figure=daily
                ), 
                color='light',
                outline=True
                ),
                dbc.Card(
                dcc.Graph(
                    id='hourly',
                    figure=hourly
                ))
            ])
        )
    ]
)

# the styles for the main content position it to the right of the sidebar and
# add some padding.


content = html.Div(
    dbc.Card(
        [
            dbc.CardHeader(
                html.H1("NYC Taxi Dataset"),
                # style={"background-color":"#2780E3", "opacity":0.3}
            ),
            dbc.CardBody(
                dbc.CardDeck(
                    [
                        map, graphs
                    ]
                ))
        ],
        id='content'
    )
)

selected = html.Div([
    dcc.Markdown("""
                **Click Data**

                Click on points in the graph.
            """),
    html.Pre(id='click-data'),
])

app.layout = html.Div(children=[dcc.Location(id="url"), content, selected])


@app.callback(
    Output('click-data', 'children'),
    Input('nyc_map', 'clickData')
)
def display_selected_data(clickData):
    return json.dumps(clickData, indent=2)


@app.callback(
    Output('zone-stats-header', 'children'),
    Output('daily', 'figure'),
    Output('hourly', 'figure'),
    Input('nyc_map', 'clickData')
)
def update_hourly(clickData):
    zone = str(clickData['points'][0]['pointNumber']
               ) if clickData is not None else '-1'
    data = ZONE_DATA[zone]
    daily = create_daily_plot(data['daily'])
    hourly = create_hourly_plot(data['hourly'])

    zone_name = data['name'] if clickData is not None else "New York City"
    return zone_name, daily, hourly


if __name__ == '__main__':
    app.run_server(debug=True, port=8080)
