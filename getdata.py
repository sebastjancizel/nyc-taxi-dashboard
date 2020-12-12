import vaex
import json
import numpy as np
from tqdm import tqdm

zone_filename = 'aux_data/zone.json'
with open(zone_filename) as f:
    zmapper = json.load(f)

zone_index_to_name = {int(index): name for index, name in zmapper.items()}

# Open the main data
TAXI_PATH = 's3://vaex/taxi/yellow_taxi_2012_zones.hdf5?anon=true'
df = vaex.open(TAXI_PATH)

used_columns = ['total_amount',
                'trip_duration_min',
                'trip_speed_mph',
                'trip_distance',
                'pickup_hour',
                'pickup_day',
                'dropoff_zone',
                'pickup_zone']

df.categorize(df.pickup_day, labels=[
    'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], inplace=True)
df.categorize(df.pickup_zone, inplace=True)
df.categorize(df.dropoff_zone, inplace=True)
df.categorize(df.pickup_hour, inplace=True)


def extract_ride_statistics(zone=None):

    selection = False

    if zone is not None:
        df.select(df.pickup_zone == zone)
        selection = True

    # Compute relative share of rides for each day compared to the mean
    daily_data = df.count(binby=df.pickup_day, selection=selection)
    daily_data = 1/sum(daily_data) * daily_data
    daily_data = np.around(daily_data - np.mean(daily_data), decimals=3)

    # Compute relative share of pickups each hour
    hourly_data = df.count(binby=df.pickup_hour, selection=selection)
    hourly_data = np.around(1/sum(hourly_data) * hourly_data, decimals=3)

    # Compute top 5 destination zones
    dropoff_count = df.count(binby=df.dropoff_zone, selection=selection)
    dropoff_count = 1/sum(dropoff_count) * dropoff_count
    # - is because we want the maximum elements
    sorted_args = np.argsort(-dropoff_count)
    max_args = sorted_args[:5]
    top_destinations = {
        zone_index_to_name[zone]: np.round(dropoff_count[zone], 3) for zone in max_args}
    top_destinations['Other'] = 10 * \
        np.round(np.sum([dropoff_count[zone] for zone in sorted_args[5:]]), 3)

    name = zone_index_to_name[zone] if zone is not None else "New York City"

    heatmap_data = df.total_amount.mean(binby=['pickup_day', 'pickup_hour'], selection=selection)
    heatmap_data = np.round(heatmap_data, 3) # this puts Monday on top

    data = {
        "name": name,
        "daily": daily_data.tolist(),
        "hourly": hourly_data.tolist(),
        "destinations": top_destinations,
        "heatmap": heatmap_data.tolist()
    }

    return data


ZONE_DATA = dict()

for zone in tqdm(zone_index_to_name):
    ZONE_DATA[int(zone)] = extract_ride_statistics(zone=zone)

# Store total data
ZONE_DATA[-1] = extract_ride_statistics()
ZONE_DATA[-1]['pickup_counts'] = df.count(binby=df.pickup_zone).tolist()


OUT_PATH = "./aux_data/zone_data.json"

with open(OUT_PATH, 'w') as f:
    json.dump(ZONE_DATA, f)
