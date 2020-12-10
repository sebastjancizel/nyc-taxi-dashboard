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
                'pickup_hour',
                'pickup_day',
                'dropoff_borough',
                'dropoff_zone',
                'pickup_borough',
                'pickup_zone']

df.categorize(df.pickup_day, labels=[
                       'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], inplace=True)
df.categorize(df.pickup_zone, inplace=True)
df.categorize(df.dropoff_zone, inplace=True)
df.categorize(df.pickup_hour, inplace=True)

def extract_zone_data(zone=None):
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
    daily_data = np.around(daily_data - np.mean(daily_data), decimals=4)

    hourly_data = np.around(1/sum(hourly_data) * hourly_data, decimals=4)

    name = zone_index_to_name[zone] if zone is not None else "All"

    data = {"name": name, "daily": daily_data.tolist(), "hourly": hourly_data.tolist()}

    return data

DATA = dict()

for zone in tqdm(zone_index_to_name):
    DATA[int(zone)] = extract_zone_data(zone = zone)

## Store total data 
DATA[-1] = extract_zone_data()
DATA[-1]['pickup_counts'] = df.count(binby=df.pickup_zone).tolist()



OUT_PATH = "./aux_data/zone_data.json"

with open(OUT_PATH, 'w') as f:
    json.dump(DATA, f)



    

