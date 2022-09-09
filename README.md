# KoopPy

A FeatureServer/MapServer implementation based on FastAPI, Geopandas and ArcGIS API for Python. The name is an homage to [KoopJS]. KoopPy tries to achieve same functionality as KoopJS (sometime ... maybe).

Currently serves ```.geojson``` and ```.shp``` files inside ```./data``` and should support usage in MapViewer Classic and the new MapViewer.


**Momentarily does not support dynamic MapServices i.e. no adjustig the colors/renderer**

The API serves the data using the following routes:
1. http\://localhost:8000/```DATANAME```/FeatureServer
2. http\://localhost:8000/```DATANAME```/FeatureServer/0
3. http\://localhost:8000/```DATANAME```/MapServer

## Example
For the example file inside the data folder ```ne_10m_admin_0_countries.shp``` the routes would be:
1. http\://localhost:8000/```ne_10m_admin_0_countries```/FeatureServer
2. http\://localhost:8000/```ne_10m_admin_0_countries```/FeatureServer/0
3. http\://localhost:8000/```ne_10m_admin_0_countries```/MapServer

# How to use

- Clone this repository
- Create a new conda environment using the ```environment.yml```
- Run the conda environment
- Serve using ```uvicorn``` (e.g. ```uvicorn main:app```)


# TODO:

- Implement MapServer styling
- Implement PBF output
- Clean up code
- etc.


[//]: #

[koopjs]: <https://github.com/koopjs>
