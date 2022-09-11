# KoopPy

A FeatureServer/MapServer implementation based on FastAPI, Geopandas and ArcGIS API for Python. The name is an homage to [KoopJS]. KoopPy tries to achieve same functionality as KoopJS (sometime ... maybe).

Currently serves ```.geojson``` and ```.shp``` files inside ```./data``` and should support usage in MapViewer Classic and the new MapViewer.


**Momentarily does not support dynamic MapServices i.e. no adjustig the colors/renderer**

The API serves the data using the following routes:
1. http:<nolink>//127.0.0.1:8000/```DATANAME```/FeatureServer
2. http:<nolink>//127.0.0.1:8000/```DATANAME```/FeatureServer/0
3. http:<nolink>//127.0.0.1:8000/```DATANAME```/MapServer

## Example
For the example file inside the data folder ```ne_10m_admin_0_countries.shp``` the routes would be:
1. http:<nolink>//127.0.0.1:8000/```ne_10m_admin_0_countries```/FeatureServer
2. http:<nolink>//127.0.0.1:8000/```ne_10m_admin_0_countries```/FeatureServer/0
3. http:<nolink>//127.0.0.1:8000/```ne_10m_admin_0_countries```/MapServer

**To view all possible API endpoints refer to the following URL:** http:<nolink>//127.0.0.1:8000/docs

# How to use

- Clone this repository
- Create a new conda environment using the ```environment.yml``` (Windows) or use the ```requirements.txt``` (Windows/Linux).
- Run the conda environment
- Serve using ```uvicorn``` (e.g. ```uvicorn main:app```)


# TODO:

- Implement MapServer styling
- Implement PBF output
- Clean up code
- Dockerize
- etc.


[//]: #

[koopjs]: <https://github.com/koopjs>
