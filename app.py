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

zone_index_to_name = {int(index): name for index, name in zmapper.items()}
zone_name_to_index = {name: int(index) for index, name in zmapper.items()}
borough_index_to_name = {int(index): name for index, name in bmapper.items()}
borough_name_to_index = {name: int(index) for index, name in bmapper.items()}
zone_index_to_borough_index = {int(
    index): borough_name_to_index[zbmapper[name]] for index, name in zmapper.items()}

# Open the main data
taxi_path = 's3://vaex/taxi/yellow_taxi_2012_zones.hdf5?anon=true'
taxi_path = os.environ.get('TAXI_PATH', taxi_path)
df_original = vaex.open(taxi_path)

used_columns = ['total_amount',
                'trip_duration_min',
                'trip_speed_mph',
                'pickup_hour',
                'pickup_day',
                # 'dropoff_borough',
                'dropoff_zone',
                # 'pickup_borough',
                'pickup_zone']

df_original.categorize(df_original.pickup_day, labels=[
                       'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], inplace=True)
df_original.categorize(df_original.pickup_zone, inplace=True)
df_original.categorize(df_original.dropoff_zone, inplace=True)
df_original.categorize(df_original.pickup_hour, inplace=True)

df = df_original[used_columns]

#
#   Data processing
#


def extract_zone_data(df, zone=None):
    if zone == None:
        daily_data = df.count(binby=df.pickup_day)
        hourly_data = df.count(binby=df.pickup_hour)
        # price_data  = df.count(binby=df.total_amount)

    else:
        zone_df = df[df.pickup_zone == zone]
        daily_data = zone_df.count(binby=df.pickup_day)
        hourly_data = zone_df.count(binby=df.pickup_hour)
        # price_data  = zone_df.count(binby=df.total_amount)

    daily_data = 1/sum(daily_data) * daily_data
    daily_data = daily_data - np.mean(daily_data)

    hourly_data = 1/sum(hourly_data) * hourly_data

    data = {"daily": daily_data, "hourly": hourly_data}

    return data

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
                      coloraxis_showscale=False, showlegend=False, clickmode='event+select')
    return fig


def create_daily_plot(daily):

    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    weekly_fig = px.bar(x=days, y=daily)
    weekly_fig.update_yaxes(zeroline = True, showgrid=True, gridwidth=.5, gridcolor='#d5d5d5')
    weekly_fig.update_layout(
        yaxis=dict(tickformat=".1%", title=None),
        xaxis=dict(title=None),
        title='Distribution of rides per weekday',
        margin={"r": 0, "l": 0},
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=300
    )

    return weekly_fig


def create_hourly_plot(hourly):
    hourly_fig = px.area(hourly)

    hourly_fig.update_yaxes(zeroline = True, showgrid=True, gridwidth=.5, gridcolor='#d5d5d5')

    hourly_fig.update_layout(
        yaxis=dict(title=None, tickformat='.1%'),
        xaxis=dict(title=None),
        title='Distribution of rides per weekday',
        margin={"r": 0, "l": 0, "b": 0},
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        height=300
    )

    return hourly_fig


#
#   Create charts
#
pickup_counts = df_original.count(binby=df_original.pickup_zone)
chart = create_figure_geomap(pickup_counts, zone=None)

data = extract_zone_data(df, zone=None)

daily = create_daily_plot(data['daily'])

hourly = create_hourly_plot(data['hourly'])

#
#   App layout
#
graphs = dbc.Card(
    [
    dbc.CardHeader(
        children=[html.H4("Zone Name", id='zone-stats-header')],
    ),
    dbc.CardBody(
        [
            dcc.Graph(
                id='daily',
                figure=daily
            ),

            dcc.Graph(
                id='hourly',
                figure=hourly
            )
        ]
    )
    ]
)

# the styles for the main content position it to the right of the sidebar and
# add some padding.


content = html.Div(
    dbc.Container(
        [
            html.H1("NYC Taxi Dataset"),
            dbc.Row(
                [
                    dbc.Col(dbc.Card(
                            dbc.CardBody(
                                dcc.Graph(
                                    id='nyc_map',
                                    figure=chart
                                ))), 
                            ),

                    dbc.Col(
                        graphs, md=4
                    )

                ]
            )
        ],
        fluid=True,
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
    zone = clickData['points'][0]['pointNumber'] if clickData is not None else None
    data = extract_zone_data(df, zone=zone)
    daily = create_daily_plot(data['daily'])
    hourly = create_hourly_plot(data['hourly'])

    zone_name = clickData['points'][0]['location'] if clickData is not None else "All Data"
    return zone_name, daily, hourly

if __name__ == '__main__':
    app.run_server()
