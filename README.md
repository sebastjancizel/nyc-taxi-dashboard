# NYC Taxi Dashboard

The NYC Taxi & Limousine commission publishes the [trip records](https://www1.nyc.gov/site/tlc/about/tlc-trip-record-data.page) of yellow and green cab pickups in New York City. The data is updated monthly and a year's worth of data includes over 120 million distinct rides. 

## Description
Given the volume of the data, the analysis with Pandas was slow. I first encountered the data set on Kaggle and when looking at an efficient way to deal with the amount of data I came across [Vaex](https://vaex.readthedocs.io/en/latest/index.html). Vaex is able to deal with much larger datasets that don't fit in memory and make Pandas stumble. It's able to do this by leveraging super quick backend, lazy evaluation and generally being very clever. The result is quite amazing. The computations which would be excruciatingly slow in Pandas are tend to be quick very quick using Vaex. 
 
Due to technical limitations and lack of online storage I decided to use the preexisting dataset in the optimized HDF5 format provided in the [tutorial](https://medium.com/plotly/interactive-and-scalable-dashboards-with-vaex-and-dash-9b104b2dc9f0). This dataset contains the taxi rides from the year 2012. The app in the tutorial was also the starting point for this dashboard. I originally planned to have the app query the interactively from the Amazon S3 bucket and deploy it to Heroku. However, to keep it suitable for the free tier of Heroku with its 512mb RAM I had to pre-filter the data and upload the condensed data for the visualizations. That's why this dashboard has two main components.
### Getting the data
The file `getdata.py` extracts the data form the S3 bucket and stores the data relevant for visualizations to a json file in `aux_data`.

### Visualizing the data
The data visualizations are built with Plotly and Dash with Dash Bootstrap Components.



