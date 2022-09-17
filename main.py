from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
##from brotli_asgi import BrotliMiddleware
from fastapi.responses import HTMLResponse, JSONResponse


import geopandas as gpd
from shapely.geometry import Polygon, box
import os
import json
from arcgis.features import FeatureSet,GeoAccessor, GeoSeriesAccessor
import pandas as pd
from math import isnan
import warnings

from io import BytesIO
from starlette.responses import StreamingResponse
import matplotlib as mpl

warnings.filterwarnings('ignore')

import FeatureCollection_pb2
import google.protobuf

app = FastAPI()

###GZIP Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)
##app.add_middleware(BrotliMiddleware)

###CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

###Specify data folder
### Loops over files, transforms geojson and shape to geopandas dataframe and creates lists with dataframes and filenames
directory = r"./data"
services = []
filenames = []
esriServices = []


###.fillna to handle NaN values which fastapi can't json decode
for file in os.listdir(directory):
    filename = os.fsdecode(file)
    if filename.endswith(".geojson") or filename.endswith(".shp"): 
        geos= gpd.read_file(os.path.join(directory, filename))
        geosReprojected = geos.to_crs(epsg=3857).fillna(value="noData")
        esriGDF = GeoAccessor.from_geodataframe(geosReprojected,column_name="geometry")
        esriGDF.insert(0, "OBJECTID",esriGDF.index)
        services.append(geosReprojected)
        filenames.append(os.path.splitext(filename)[0])
        esriServices.append(esriGDF)
        continue
    else:
        continue

servicesDict = {filenames[i]: services[i] for i in range(len(filenames))}
esriServicesDict = {filenames[i]: esriServices[i] for i in range(len(filenames))}

###base renderer settings
pointRenderer = {
      "type": "simple",
      "symbol": {
        "color": [
          45,
          172,
          128,
          161
        ],
        "outline": {
          "color": [
            190,
            190,
            190,
            105
          ],
          "width": 0.5,
          "type": "esriSLS",
          "style": "esriSLSSolid"
        },
        "size": 7.5,
        "type": "esriSMS",
        "style": "esriSMSCircle"
      }
    }
lineRenderer = {
      "type": "simple",
      "symbol": {
        "color": [
          247,
          150,
          70,
          204
        ],
        "width": 6.999999999999999,
        "type": "esriSLS",
        "style": "esriSLSSolid"
      }
}

polygonRenderer = {
      "type": "simple",
      "symbol": {
        "type": "esriSFS",
        "style": "esriSFSSolid",
        "color": [
          75,
          172,
          198,
          161
        ],
        "outline": {
          "color": [
            150,
            150,
            150,
            155
          ],
          "width": 0.5,
          "type": "esriSLS",
          "style": "esriSLSSolid"
        }
      },
      "scaleSymbols": True,
      "transparency": 0,
      "labelingInfo": None
}
###/rest/info route -  Don't really know if needed

@app.get("/rest/info")
def root (f: str="json"):
    infoJSON = {
          "currentVersion" : 10.5, 
          "fullVersion" : "10.5", 
          "owningSystemUrl" : "https://github.com/karschmidt/KoopPy", 
          "owningTenant" : "Karsten Schmidt", 
          "authInfo" : 
          {
            "isTokenBasedSecurity" : False
          }
        }
    return infoJSON

###initial service info page for FeatureServer

@app.get("/{serviceName}/FeatureServer")
def root(serviceName:str):
    if serviceName not in servicesDict.keys():
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        if servicesDict[serviceName].geom_type[0] == "MultiPolygon":
            multiSanitized = "Polygon"
        else:
            multiSanitized = servicesDict[serviceName].geom_type[0]
        service = {
        "serviceDescription": "FastAPI ESRI FeatureServer implementation by Karsten Schmidt",
        "hasVersionedData": False,
        "supportsDisconnectedEditing": False,
        "supportsRelationshipsResource": False,
        "supportedQueryFormats": "JSON,geoJSON",
        "maxRecordCount": 2000,
        "hasStaticData": False,
        "capabilities": "Query",
        "description": "FastAPI ESRI FeatureServer implementation by Karsten Schmidt",
        "copyrightText": "Copyright information varies from provider to provider, for more information please contact the source of this data",
        "spatialReference": {
            "wkid": 102100,
            "latestWkid": 3857
        },
        "initialExtent": {
            "xmin": servicesDict[serviceName].geometry.total_bounds[0],
            "ymin": servicesDict[serviceName].geometry.total_bounds[1],
            "xmax": servicesDict[serviceName].geometry.total_bounds[2],
            "ymax": servicesDict[serviceName].geometry.total_bounds[3],
            "spatialReference": {
            "wkid": 102100,
            "latestWkid": 3857
            }
        },
        "fullExtent": {
            "xmin": servicesDict[serviceName].geometry.total_bounds[0],
            "ymin": servicesDict[serviceName].geometry.total_bounds[1],
            "xmax": servicesDict[serviceName].geometry.total_bounds[2],
            "ymax": servicesDict[serviceName].geometry.total_bounds[3],
            "spatialReference": {
            "wkid": 102100,
            "latestWkid": 3857
            }
        },
        "allowGeometryUpdates": False,
        "units": "esriDecimalDegrees",
        "syncEnabled": False,
        "layers": [{
            "name": serviceName,
            "id": 0,
            "parentLayerId": -1,
            "defaultVisibility": True,
            "subLayerIds": None,
            "minScale": 0,
            "maxScale": 0,
            "geometryType": "esriGeometry" + multiSanitized

        }],
        "tables": []
        }
        return service

###initial service info page for MapServer

@app.get("/{serviceName}/MapServer")
def root(serviceName:str, callback: str=None):
    if serviceName not in servicesDict.keys():
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        if servicesDict[serviceName].geom_type[0] == "MultiPolygon":
            multiSanitized = "Polygon"
        else:
            multiSanitized = servicesDict[serviceName].geom_type[0]
        service = {
          "currentVersion": 10.5,
          "serviceDescription": "MapServer using KoopPy by Karsten Schmidt",
          "mapName": serviceName,
          "description": "MapServer using KoopPy by Karsten Schmidt",
          "copyrightText": "",
          "supportsDynamicLayers": True,
          "layers": [{
            "name": serviceName,
            "id": 0,
            "parentLayerId": -1,
            "defaultVisibility": True,
            "subLayerIds": None,
            "minScale": 0,
            "maxScale": 0,
            "type": "Feature Layer",
            "geometryType": "esriGeometry" + multiSanitized,
            "supportsDynamicLegends": True

        }
          ],
          "supportsDatumTransformation": True,
          "tables": [],
          "spatialReference": {"wkid": 102100,
            "latestWkid": 3857},
          "singleFusedMapCache": False,
          "tileInfo": {
          },
         "initialExtent": {
            "xmin": servicesDict[serviceName].geometry.total_bounds[0],
            "ymin": servicesDict[serviceName].geometry.total_bounds[1],
            "xmax": servicesDict[serviceName].geometry.total_bounds[2],
            "ymax": servicesDict[serviceName].geometry.total_bounds[3],
            "spatialReference": {
            "wkid": 102100,
            "latestWkid": 3857
            }
        },
        "fullExtent": {
            "xmin": servicesDict[serviceName].geometry.total_bounds[0],
            "ymin": servicesDict[serviceName].geometry.total_bounds[1],
            "xmax": servicesDict[serviceName].geometry.total_bounds[2],
            "ymax": servicesDict[serviceName].geometry.total_bounds[3],
            "spatialReference": {
            "wkid": 102100,
            "latestWkid": 3857
            }
        }, 
          "units": "esriMeters",
          "supportedImageFormatTypes": "PNG32",
          "capabilities": "Map,Query,Data",
          "maxRecordCount": 1000,
          "maxImageHeight": 2048,
          "maxImageWidth": 2048,
          "minScale": 0,
          "maxScale": 0,
          "tileServers": [],
          "supportedQueryFormats": "JSON",
          "exportTilesAllowed": False,
          "maxExportTilesCount": 100000,
          "supportedExtensions": "FeatureServer",
          "resampling": False
        }
        if callback is None:
          return JSONResponse(content=service, media_type="application/json; charset=utf-8")
        else:
          return HTMLResponse(content=callback+"("+json.dumps(service)+");", media_type="application/javascript; charset=UTF-8")
### MapServer /0/ route

@app.get("/{serviceName}/MapServer/0")
def root(serviceName:str, f: str = "json", callback: str=None):
    if serviceName not in servicesDict.keys():
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        if servicesDict[serviceName].geom_type[0] == "MultiPolygon":
            rendererInfo = polygonRenderer
            multiSanitized = "Polygon"
        elif servicesDict[serviceName].geom_type[0] == "Polygon":
            rendererInfo = polygonRenderer
            multiSanitized = servicesDict[serviceName].geom_type[0]
        elif servicesDict[serviceName].geom_type[0] == "Line":
            rendererInfo = lineRenderer
            multiSanitized = servicesDict[serviceName].geom_type[0]
        elif servicesDict[serviceName].geom_type[0] == "Point":
            rendererInfo = pointRenderer
            multiSanitized = servicesDict[serviceName].geom_type[0]

        esriGDF = GeoAccessor.from_geodataframe(servicesDict[serviceName],column_name="geometry")
        interDF = FeatureSet.from_dataframe(df=esriGDF)
        case = {"sqlType" : "sqlTypeOther", "nullable" : True, "editable" : False,"domain" : None,"defaultValue" : None}

        for i in range(len(interDF.fields)):
            interDF.fields[i].update(case)

        layerSettings = {
            "currentVersion":10.5,
            "id":0,
            "name":serviceName,
            "type":"Feature Layer",
            "description":"Data served by KoopPy",
            "geometryType":"esriGeometry" + multiSanitized,
            "copyrightText":"",
            "parentLayer":None,
            "subLayers":None,
            "minScale":0,
            "maxScale":0,
            "fields": interDF.fields,
            "drawingInfo":{
                    "renderer": rendererInfo
            },
            "defaultVisibility":True,
            "extent":{
                "xmin": servicesDict[serviceName].geometry.total_bounds[0],
                "ymin": servicesDict[serviceName].geometry.total_bounds[1],
                "xmax": servicesDict[serviceName].geometry.total_bounds[2],
                "ymax": servicesDict[serviceName].geometry.total_bounds[3],
                "spatialReference":{
                    "wkid":102100,
                    "latestWkid":3857
                }
            },
            "hasAttachments":False,
            "displayField":"OBJECTID",
            "typeIdField":None,
            "relationships":[],
            "canModifyLayer":False,
            "htmlPopupType": "esriServerHTMLPopupTypeNone",
            "canScaleSymbols":False,
            "hasLabels":False,
            "capabilities":"Query",
            "maxRecordCount":1000,
            "supportsStatistics":True,
            "supportsAdvancedQueries":False,
            "supportedQueryFormats":"JSON",
            "supportsOutFieldsSqlExpression": True,
            "ownershipBasedAccessControlForFeatures":{
                "allowOthersToQuery":True
            },
            "useStandardizedQueries":True,
            "advancedQueryCapabilities":{
                "useStandardizedQueries":True,
                "supportsQueryWithResultType": True,
                "supportsStatistics":True,
                "supportsOrderBy":True,
                "supportsDistinct":True,
                "supportsPagination":True,
                "supportsTrueCurve":False,
                "supportsReturningQueryExtent":True,
                "supportsQueryWithDistance":False
            },
            "dateFieldsTimeReference":None,
            "isDataVersioned":False,
            "supportsRollbackOnFailureParameter":True,
            "hasM":False,
            "hasZ":False,
            "allowGeometryUpdates":False,
            "objectIdField":"OBJECTID",
            "uniqueIdField" : 
                {
                  "name" : "OBJECTID", 
                  "isSystemMaintained" : True
                },
            "globalIdField":"",
            "types":[
                
            ],
            "templates":[
                {
                    "name": serviceName,
                    "description": "",
                    "drawingTool" : "esriFeatureEditTool" + multiSanitized,
                    "prototype": {"attributes":{}}      
                }
            ],
            "hasStaticData":True
            }
        if callback is None:
            return JSONResponse(content=layerSettings, media_type="application/json; charset=utf-8")
        else:
            return HTMLResponse(content=callback+"("+json.dumps(layerSettings)+");", media_type="application/javascript; charset=UTF-8")

### MapServer layers route

@app.get("/{serviceName}/MapServer/layers")
def root(serviceName:str, callback: str=None):
    if serviceName not in servicesDict.keys():
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        if servicesDict[serviceName].geom_type[0] == "MultiPolygon":
            rendererInfo = polygonRenderer
            multiSanitized = "Polygon"
        elif servicesDict[serviceName].geom_type[0] == "Polygon":
            rendererInfo = polygonRenderer
            multiSanitized = servicesDict[serviceName].geom_type[0]
        elif servicesDict[serviceName].geom_type[0] == "Line":
            rendererInfo = lineRenderer
            multiSanitized = servicesDict[serviceName].geom_type[0]
        elif servicesDict[serviceName].geom_type[0] == "Point":
            rendererInfo = pointRenderer
            multiSanitized = servicesDict[serviceName].geom_type[0]

        esriGDF = GeoAccessor.from_geodataframe(servicesDict[serviceName],column_name="geometry")
        interDF = FeatureSet.from_dataframe(df=esriGDF)

        layerSettings = {
            "layers":[{
              "currentVersion":10.5,
              "id":0,
              "name":serviceName,
              "type":"Feature Layer",
              "description":"Data served by KoopPy",
              "geometryType":"esriGeometry" + multiSanitized,
              "copyrightText":" ",
              "parentLayer":None,
              "subLayers":[],
              "minScale":0,
              "maxScale":0,
              "sourceSpatialReference":{
                      "wkid":102100,
                      "latestWkid":3857
                  },
              "drawingInfo":{
                      "renderer": rendererInfo
              },
              "defaultVisibility":True,
              "extent":{
                  "xmin": servicesDict[serviceName].geometry.total_bounds[0],
                  "ymin": servicesDict[serviceName].geometry.total_bounds[1],
                  "xmax": servicesDict[serviceName].geometry.total_bounds[2],
                  "ymax": servicesDict[serviceName].geometry.total_bounds[3],
                  "spatialReference":{
                      "wkid":102100,
                      "latestWkid":3857
                  }
              },
              "hasAttachments":False,
              "htmlPopupType":"esriServerHTMLPopupTypeAsHTMLText",
              "displayField":"OBJECTID",
              "typeIdField":None,
              "fields":[],
              "relationships":[],
              "canModifyLayer":True,
              "canScaleSymbols":False,
              "hasLabels":False,
              "capabilities":"Query",
              "maxRecordCount":1000,
              "supportsStatistics":True,
              "supportsAdvancedQueries":False,
              "supportedQueryFormats":"JSON",
              "supportsOutFieldsSqlExpression": True,
              "ownershipBasedAccessControlForFeatures":{
                  "allowOthersToQuery":True
              },
              "useStandardizedQueries":True,
              "advancedQueryCapabilities":{
                  "useStandardizedQueries":True,
                  "supportsStatistics":True,
                  "supportsOrderBy":True,
                  "supportsDistinct":True,
                  "supportsPagination":True,
                  "supportsTrueCurve":False,
                  "supportsReturningQueryExtent":True,
                  "supportsQueryWithDistance":True
              },
              "dateFieldsTimeReference":None,
              "isDataVersioned":False,
              "supportsRollbackOnFailureParameter":True,
              "hasM":False,
              "hasZ":False,
              "allowGeometryUpdates":False,
              "objectIdField":"OBJECTID",
              "uniqueIdField" : 
                  {
                    "name" : "OBJECTID", 
                    "isSystemMaintained" : True
                  },
              "globalIdField":"",
              "types":[
                  
              ],
              "templates":[
                  
              ],
              "fields":interDF.fields,
              "hasStaticData":True
              }
              ]
        }
        if callback is None:
          return JSONResponse(content=layerSettings, media_type="application/json; charset=utf-8")
        else:
          return HTMLResponse(content=callback+"("+json.dumps(layerSettings)+");", media_type="application/javascript; charset=UTF-8")


### MapServer export image route - supports bbox, size and dpi. Currently outputs blue colormap but can be adjusted as a dynamicLayer.
### No statistics yet. No jpg support - just plain 32bit png

@app.get("/{serviceName}/MapServer/export")
def root(serviceName:str, size: str=None, bbox: str=None, dpi: int=None):
    if serviceName not in servicesDict.keys():
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        boundingBox1 = bbox.split(",")
        boundingBox = []
        for element in boundingBox1:
           boundingBox.append(float(element))
        imgSize = size.split(",")
        mpl.rcParams[ 'figure.figsize' ] = (int(imgSize[0])/dpi,int(imgSize[1])/dpi)
        mpl.rcParams[ 'figure.dpi' ] = dpi
        image = servicesDict[serviceName].plot(cmap="Blues")
        image.set_xlim(boundingBox[0], boundingBox[2])
        image.set_ylim(boundingBox[1], boundingBox[3])
        image.set_axis_off();
        image.figure.tight_layout(pad=0)
        buf = BytesIO()
        image.figure.savefig(buf, format="png", transparent=True, pad_inches=0, dpi=dpi)
        buf.seek(0)
        
    return StreamingResponse(buf, media_type="image/png")

### MapServer dynamicLayer route - allows to adjust basic symbology inside MapViewer

@app.get("/{serviceName}/MapServer/dynamicLayer")
def root(serviceName:str, callback: str=None):
  if serviceName not in servicesDict.keys():
      raise HTTPException(status_code=404, detail="Item not found")
  else:
      if servicesDict[serviceName].geom_type[0] == "MultiPolygon":
          rendererInfo = polygonRenderer
          multiSanitized = "Polygon"
      elif servicesDict[serviceName].geom_type[0] == "Polygon":
          rendererInfo = polygonRenderer
          multiSanitized = servicesDict[serviceName].geom_type[0]
      elif servicesDict[serviceName].geom_type[0] == "Line":
          rendererInfo = lineRenderer
          multiSanitized = servicesDict[serviceName].geom_type[0]
      elif servicesDict[serviceName].geom_type[0] == "Point":
          rendererInfo = pointRenderer
          multiSanitized = servicesDict[serviceName].geom_type[0]

      esriGDF = GeoAccessor.from_geodataframe(servicesDict[serviceName],column_name="geometry")
      interDF = FeatureSet.from_dataframe(df=esriGDF)
      case = {"sqlType" : "sqlTypeOther", "nullable" : True, "editable" : False,"domain" : None,"defaultValue" : None}

      for i in range(len(interDF.fields)):
          interDF.fields[i].update(case)

      layerSettings = {
          "currentVersion":10.5,
          "name":serviceName + "_0",
          "type":"Feature Layer",
          "description":"Data served by KoopPy",
          "geometryType":"esriGeometry" + multiSanitized,
          "copyrightText":"",
          "parentLayer":None,
          "subLayers":None,
          "minScale":0,
          "maxScale":0,
          "sourceSpatialReference":{
                      "wkid":102100,
                      "latestWkid":3857
                  },
          "fields": interDF.fields,
          "drawingInfo":{
                  "renderer": rendererInfo
          },
          "defaultVisibility":True,
          "extent":{
              "xmin": servicesDict[serviceName].geometry.total_bounds[0],
              "ymin": servicesDict[serviceName].geometry.total_bounds[1],
              "xmax": servicesDict[serviceName].geometry.total_bounds[2],
              "ymax": servicesDict[serviceName].geometry.total_bounds[3],
              "spatialReference":{
                  "wkid":102100,
                  "latestWkid":3857
              }
          },
          "hasAttachments":False,
          "displayField":"OBJECTID",
          "typeIdField":None,
          "relationships":[],
          "canModifyLayer":False,
          "htmlPopupType": "esriServerHTMLPopupTypeNone",
          "canScaleSymbols":False,
          "hasLabels":False,
          "capabilities":"Query",
          "maxRecordCount":1000,
          "supportsStatistics":True,
          "supportsAdvancedQueries":False,
          "supportedQueryFormats":"JSON",
          "supportsOutFieldsSqlExpression": True,
          "ownershipBasedAccessControlForFeatures":{
              "allowOthersToQuery":True
          },
          "useStandardizedQueries":True,
          "advancedQueryCapabilities":{
              "useStandardizedQueries":True,
              "supportsQueryWithResultType": True,
              "supportsStatistics":True,
              "supportsOrderBy":True,
              "supportsDistinct":True,
              "supportsPagination":True,
              "supportsTrueCurve":False,
              "supportsReturningQueryExtent":True,
              "supportsQueryWithDistance":False
          },
          "dateFieldsTimeReference":None,
          "isDataVersioned":False,
          "supportsRollbackOnFailureParameter":True,
          "hasM":False,
          "hasZ":False,
          "allowGeometryUpdates":False,
          "objectIdField":"OBJECTID",
          "uniqueIdField" : 
              {
                "name" : "OBJECTID", 
                "isSystemMaintained" : True
              },
          "globalIdField":"",
          "types":[
              
          ],
          "templates":[
              {
                  "name": serviceName,
                  "description": "",
                  "drawingTool" : "esriFeatureEditTool" + multiSanitized,
                  "prototype": {"attributes":{}}      
              }
          ],
          "hasStaticData":True
          }
      if callback is None:
          return JSONResponse(content=layerSettings, media_type="application/json; charset=utf-8")
      else:
          return HTMLResponse(content=callback+"("+json.dumps(layerSettings)+");", media_type="application/javascript; charset=UTF-8")




### FeatureServer layers route - not sure if actually needed

@app.get("/{serviceName}/FeatureServer/layers")
def root(serviceName:str):
    if serviceName not in servicesDict.keys():
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        if servicesDict[serviceName].geom_type[0] == "MultiPolygon":
            rendererInfo = polygonRenderer
            multiSanitized = "Polygon"
        elif servicesDict[serviceName].geom_type[0] == "Polygon":
            rendererInfo = polygonRenderer
            multiSanitized = servicesDict[serviceName].geom_type[0]
        elif servicesDict[serviceName].geom_type[0] == "Line":
            rendererInfo = lineRenderer
            multiSanitized = servicesDict[serviceName].geom_type[0]
        elif servicesDict[serviceName].geom_type[0] == "Point":
            rendererInfo = pointRenderer
            multiSanitized = servicesDict[serviceName].geom_type[0]

        esriGDF = GeoAccessor.from_geodataframe(servicesDict[serviceName],column_name="geometry")
        interDF = FeatureSet.from_dataframe(df=esriGDF)

        layerSettings = {
            "currentVersion":10.5,
            "id":0,
            "name":serviceName,
            "type":"Feature Layer",
            "description":"Data served by KoopPy",
            "geometryType":"esriGeometry" + multiSanitized,
            "copyrightText":" ",
            "parentLayer":None,
            "subLayers":None,
            "minScale":0,
            "maxScale":0,
            "drawingInfo":{
                    "renderer": rendererInfo
            },
            "defaultVisibility":True,
            "extent":{
                "xmin": servicesDict[serviceName].geometry.total_bounds[0],
                "ymin": servicesDict[serviceName].geometry.total_bounds[1],
                "xmax": servicesDict[serviceName].geometry.total_bounds[2],
                "ymax": servicesDict[serviceName].geometry.total_bounds[3],
                "spatialReference":{
                    "wkid":3857,
                    "latestWkid":3857
                }
            },
            "hasAttachments":False,
            "htmlPopupType":"esriServerHTMLPopupTypeAsHTMLText",
            "displayField":"OBJECTID",
            "typeIdField":None,
            "fields":[],
            "relationships":[],
            "canModifyLayer":False,
            "canScaleSymbols":False,
            "hasLabels":False,
            "capabilities":"Query",
            "maxRecordCount":1000,
            "supportsStatistics":True,
            "supportsAdvancedQueries":False,
            "supportedQueryFormats":"JSON",
            "supportsOutFieldsSqlExpression": True,
            "ownershipBasedAccessControlForFeatures":{
                "allowOthersToQuery":True
            },
            "useStandardizedQueries":True,
            "advancedQueryCapabilities":{
                "useStandardizedQueries":True,
                "supportsStatistics":True,
                "supportsOrderBy":True,
                "supportsDistinct":True,
                "supportsPagination":True,
                "supportsTrueCurve":False,
                "supportsReturningQueryExtent":True,
                "supportsQueryWithDistance":True
            },
            "dateFieldsTimeReference":None,
            "isDataVersioned":False,
            "supportsRollbackOnFailureParameter":True,
            "hasM":False,
            "hasZ":False,
            "allowGeometryUpdates":False,
            "objectIdField":"OBJECTID",
            "uniqueIdField" : 
                {
                  "name" : "OBJECTID", 
                  "isSystemMaintained" : True
                },
            "globalIdField":"",
            "types":[
                
            ],
            "templates":[
                
            ],
            "fields":[
              interDF.fields
            ],
            "hasStaticData":True
            }

        return layerSettings

### FeatureServer layer service page

@app.get("/{serviceName}/FeatureServer/0")
def root(serviceName:str, f: str = "json", callback: str=None):
    if serviceName not in servicesDict.keys():
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        if servicesDict[serviceName].geom_type[0] == "MultiPolygon":
            rendererInfo = polygonRenderer
            multiSanitized = "Polygon"
        elif servicesDict[serviceName].geom_type[0] == "Polygon":
            rendererInfo = polygonRenderer
            multiSanitized = servicesDict[serviceName].geom_type[0]
        elif servicesDict[serviceName].geom_type[0] == "Line":
            rendererInfo = lineRenderer
            multiSanitized = servicesDict[serviceName].geom_type[0]
        elif servicesDict[serviceName].geom_type[0] == "Point":
            rendererInfo = pointRenderer
            multiSanitized = servicesDict[serviceName].geom_type[0]

        esriGDF = GeoAccessor.from_geodataframe(servicesDict[serviceName],column_name="geometry")
        interDF = FeatureSet.from_dataframe(df=esriGDF)
        case = {"sqlType" : "sqlTypeOther", "nullable" : True, "editable" : False,"domain" : None,"defaultValue" : None}

        for i in range(len(interDF.fields)):
            interDF.fields[i].update(case)

        layerSettings = {
            "currentVersion":10.5,
            "id":0,
            "name":serviceName,
            "type":"Feature Layer",
            "description":"Data served by KoopPy",
            "geometryType":"esriGeometry" + multiSanitized,
            "copyrightText":"",
            "parentLayer":None,
            "subLayers":None,
            "minScale":0,
            "maxScale":0,
            "fields": interDF.fields,
            "drawingInfo":{
                    "renderer": rendererInfo
            },
            "defaultVisibility":True,
            "extent":{
                "xmin": servicesDict[serviceName].geometry.total_bounds[0],
                "ymin": servicesDict[serviceName].geometry.total_bounds[1],
                "xmax": servicesDict[serviceName].geometry.total_bounds[2],
                "ymax": servicesDict[serviceName].geometry.total_bounds[3],
                "spatialReference":{
                    "wkid":102100,
                    "latestWkid":3857
                }
            },
            "hasAttachments":False,
            "displayField":interDF.fields[1]["name"],
            "typeIdField":None,
            "relationships":[],
            "canModifyLayer":False,
            "htmlPopupType": "esriServerHTMLPopupTypeNone",
            "canScaleSymbols":False,
            "hasLabels":False,
            "capabilities":"Query",
            "maxRecordCount":1000,
            "supportsStatistics":True,
            "supportsAdvancedQueries":False,
            "supportedQueryFormats":"JSON",
            "supportsOutFieldsSqlExpression": True,
            "ownershipBasedAccessControlForFeatures":{
                "allowOthersToQuery":True
            },
            "useStandardizedQueries":True,
            "advancedQueryCapabilities":{
                "useStandardizedQueries":True,
                "supportsQueryWithResultType": True,
                "supportsStatistics":True,
                "supportsOrderBy":True,
                "supportsDistinct":True,
                "supportsPagination":True,
                "supportsTrueCurve":False,
                "supportsReturningQueryExtent":True,
                "supportsQueryWithDistance":False
            },
            "dateFieldsTimeReference":None,
            "isDataVersioned":False,
            "supportsRollbackOnFailureParameter":True,
            "hasM":False,
            "hasZ":False,
            "allowGeometryUpdates":False,
            "objectIdField":"OBJECTID",
            "uniqueIdField" : 
                {
                  "name" : "OBJECTID", 
                  "isSystemMaintained" : True
                },
            "globalIdField":"",
            "types":[
                
            ],
            "templates":[
                {
                    "name": serviceName,
                    "description": "",
                    "drawingTool" : "esriFeatureEditTool" + multiSanitized,
                    "prototype": {"attributes":{}}      
                }
            ],
            "hasStaticData":True
            }
        if callback is None:
            return JSONResponse(content=layerSettings, media_type="application/json; charset=utf-8")
        else:
            return HTMLResponse(content=callback+"("+json.dumps(layerSettings)+");", media_type="application/javascript; charset=UTF-8")

### FeatureServer query operation route - Supports basic visualization and querying of data

### query data magic
### conversion for to GEOJSON and ESRI JSON

###TODO: Implement pbf see: https://community.esri.com/t5/arcgis-api-for-javascript-questions/protocolbuffer-binary-format-pbf-documentation-or/td-p/464691
### geometry for pbf: quantizationParamters -> tolerance is x y scale; use following formula to calculate x y: xWorld = x * scale.x + translate.x; yWorld = translate.y - y * scale.y;
### x = xWorld/tolerance - xmin
### y = yWorld/tolerance + ymax
### coords: [256, 256, 2, 0, 0, 2, -2, 0, 0, -2, 56, 56, 2, 0, 0, 2, -2, 0, 0, -2]
### lengths: [5, 5]

@app.get("/{serviceName}/FeatureServer/0/query")
def root(serviceName:str, f: str = "geojson", geometry: str="", where: str="1=1", maxAllowableOffset: float=None, returnCountOnly: str=None, resultOffset : int=None, resultRecordCount: int=None, outFields: str=None, callback: str=None, quantizationParameters: str=None, returnGeometry: str=None,groupByFieldsForStatistics: str=None,outStatistics: str=None):
    if serviceName not in servicesDict.keys():
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        if servicesDict[serviceName].geom_type[0] == "MultiPolygon":
          multiSanitized = "Polygon"
        else:
          multiSanitized = servicesDict[serviceName].geom_type[0]
        
        #### Sanitize where case
        if "<" in where or ">" in where:
          pass
        elif "=" in where:
          where = where.replace("=", "="*2)
          if [x for x in where.lstrip()][0].isnumeric() and [x for x in where.rstrip()][-1].isnumeric():
            where="OBJECTID>=0"
          else:
            pass
        else:
          pass


        #### Format geojson - currently not working
        if f == "geojson":
            geometryParsed = json.loads(geometry)
            clippingExtent = gpd.GeoSeries(Polygon([[geometryParsed["xmin"],geometryParsed["ymin"]],[geometryParsed["xmin"],geometryParsed["ymax"]],[geometryParsed["xmax"],geometryParsed["ymax"]],[geometryParsed["xmax"],geometryParsed["ymin"]]]),crs="EPSG:3857")
            clippedGDF = gpd.clip(gdf=servicesDict[serviceName],mask=clippingExtent).to_crs(epsg=3857)
            return json.loads(clippedGDF.to_json())

        ### Handle format json and returnCountOnly
        elif f== "json" and returnCountOnly == "true":
          return {"count": len(esriServicesDict[serviceName].index)}

        #### Handle format json, resultOffset and resutlRecordCount
        elif f== "json" and resultOffset != None and resultRecordCount != None:
          interDF = FeatureSet.from_dataframe(df=esriServicesDict[serviceName].iloc[resultOffset:resultOffset + resultRecordCount])
          esriJSON = {
                "objectIdFieldName" : "OBJECTID",
                "uniqueIdField" : 
                {
                  "name" : "OBJECTID", 
                  "isSystemMaintained" : True
                },
                "geometryProperties": {
                  "shapeAreaFieldName": "Shape__Area",
                  "shapeLengthFieldName": "Shape__Length",
                  "units": "esriMeters"
                },
                "geometryType":"esriGeometry" + multiSanitized,
                "globalIdFieldName" : "",
                "hasZ": False,
                "hasM": False,
                "spatialReference" : {"wkid" : 102100, "latestWkid" : 3857},
                "fields" : interDF.fields,
                "features" : interDF.to_dict()["features"],
                "exceededTransferLimit": False
              }
          return esriJSON

        ###Handle format json and whole statistics shenanigangs
        elif f== "json" and outStatistics !=None:
          statRequest = json.loads(outStatistics)
          if groupByFieldsForStatistics != None:
            fields = []
            tempFields = {
              "defaultValue": None,
              "name": statRequest[0]["outStatisticFieldName"],
              "alias": statRequest[0]["outStatisticFieldName"],
              "type": "esriFieldTypeInteger"
            }
            fields.append(tempFields)
            tempFields = {
              "defaultValue": None,
              "name": groupByFieldsForStatistics,
              "alias": groupByFieldsForStatistics,
              "type": "esriFieldTypeString"
            }
            fields.append(tempFields)

            features =[]
            groupedService = esriServicesDict[serviceName].groupby([statRequest[0]["onStatisticField"]])
            for row in groupedService.count().itertuples():
              tempFeatures = {
                "attributes": {
                  statRequest[0]["onStatisticField"]: row[0],
                  statRequest[0]["outStatisticFieldName"]: row[1]
                }

              }
              features.append(tempFeatures)

            statReturn = {
              "features": features,
              "fields": fields
            }
            return statReturn
          else:  
            stats = {}
            i = 0
            for field in statRequest:
              function = statRequest[i]["statisticType"]
              querySan = statRequest[i]["onStatisticField"] + "!= 'noData'"
              if function == "avg":
                function = "mean"
              if function == "stddev":
                function = "std"
              if function == "percentile_cont":
                function = "quantile"
              serviceSanitized = esriServicesDict[serviceName].query(querySan)
              statCalc = {
                statRequest[i]["statisticType"]+"_value": float(getattr(serviceSanitized[statRequest[i]["onStatisticField"]], function)())
              }
              stats.update(statCalc)
              i+= 1

            fields = []
            i = 0
            for field, val in zip(statRequest, stats.values()):
              if isinstance(val, int):
                val = "esriFieldTypeInteger"
              elif isinstance(val, float):
                val = "esriFieldTypeDouble"
              elif isinstance(val, str):
                val = "esriFieldTypeString"
              tempFields = {
                "defaultValue": None,
                "name": statRequest[i]["outStatisticFieldName"],
                "alias": statRequest[i]["outStatisticFieldName"],
                "type": val
              }
              fields.append(tempFields)
              i+= 1
            
            statReturn = {
              "features": {"attributes":stats},
              "fields": fields
            }

            return statReturn

        #### whole format json query handling
        elif f == "json":
            if geometry == "":
              interDF = FeatureSet.from_dataframe(df=esriServicesDict[serviceName])
              esriJSON = {
              "objectIdFieldName" : "OBJECTID",
              "uniqueIdField" : 
              {
                "name" : "OBJECTID", 
                "isSystemMaintained" : True
              },
              "geometryType":"esriGeometry" + multiSanitized,
              "globalIdFieldName" : "",
              "hasZ": False,
              "hasM": False,
              "fields" : interDF.fields,
              "spatialReference" : {"wkid" : 102100, "latestWkid" : 3857},
              "features" : interDF.to_dict()["features"],
              "exceededTransferLimit": False
            }
              return esriJSON
            else:
              geometryParsed = json.loads(geometry)
              try:
                #clippingExtent = gpd.GeoSeries(Polygon([[geometryParsed["xmin"],geometryParsed["ymin"]],[geometryParsed["xmin"],geometryParsed["ymax"]],[geometryParsed["xmax"],geometryParsed["ymax"]],[geometryParsed["xmax"],geometryParsed["ymin"]]]),crs="EPSG:3857")
                clippingExtent = gpd.GeoSeries(Polygon([[geometryParsed["xmax"],geometryParsed["ymin"]],[geometryParsed["xmax"],geometryParsed["ymax"]],[geometryParsed["xmin"],geometryParsed["ymax"]],[geometryParsed["xmin"],geometryParsed["ymin"]],[geometryParsed["xmax"],geometryParsed["ymin"]]]),crs="EPSG:3857")
                #clippingExtent = gpd.Geoseries(box(geometryParsed["xmin"],geometryParsed["ymin"],geometryParsed["xmax"],geometryParsed["ymax"]),crs="EPSG:3857")
                envgdf = gpd.GeoDataFrame(geometry=clippingExtent)
                esrienv = GeoAccessor.from_geodataframe(envgdf,column_name="geometry")
                ##Create Spatial Index and use said index for the intersection of the geometry parameter. Why? Because all other ArcGIS API for Python methods (spatial.select, overlay, relationship) don't return the correct number.
                ##GeoAccessorSeries.generalize for generalization of Geometry using the maxAllowableOffset Parameter
                si = esriServicesDict[serviceName].spatial.sindex()
                esriGDFClipped = esriServicesDict[serviceName].iloc[si.intersect([geometryParsed["xmin"], geometryParsed["ymin"], geometryParsed["xmax"], geometryParsed["ymax"]])]
                ###if statement to catch point layers which will not be generalized
                if maxAllowableOffset == None:
                  pass
                else:
                  esriGDFClipped.geometry = esriGDFClipped.geometry.geom.generalize(maxAllowableOffset)
                  ### Why does geom.generalize mess with the crs? nobody except ESRI knows
                  esriGDFClipped.spatial.sr = {"wkid":3857}

                #esriGDFClipped.insert(0, "OBJECTID",esriGDFClipped.index)

                if outFields == "*":
                  queriedFields = None
                if outFields == "":
                  queriedFields = ["OBJECTID","geometry"]
                if outFields == "OBJECTID":
                  queriedFields = ["OBJECTID","geometry"]
                  
                if "OBJECTID" in outFields:
                  outFieldsStr = outFields.replace(" ","")
                  sanitizedOutFields = outFieldsStr.split(",")
                  queriedFields = ["geometry"]
                  for item in sanitizedOutFields:
                      queriedFields.append(item)
                elif len(outFields) >= 1:
                  outFieldsStr = outFields.replace(" ","")
                  sanitizedOutFields = outFieldsStr.split(",")
                  queriedFields = ["OBJECTID","geometry"]
                  for item in sanitizedOutFields:
                      queriedFields.append(item)
                else:
                  pass

                try:
                  esriGDFClipped = esriGDFClipped[queriedFields]
                except:
                  pass
                try:
                  interDF = FeatureSet.from_dataframe(df=esriGDFClipped.query(where))
                  esriJSON = {
                  "objectIdFieldName" : "OBJECTID",
                  "uniqueIdField" : 
                  {
                    "name" : "OBJECTID", 
                    "isSystemMaintained" : True
                  },
                  "geometryType":"esriGeometry" + multiSanitized,
                  "globalIdFieldName" : "",
                  "hasZ": False,
                  "hasM": False,
                  "fields" : interDF.fields,
                  "spatialReference" : {"wkid" : 102100, "latestWkid" : 3857},
                  "features" : interDF.to_dict()["features"],
                  "exceededTransferLimit": False
                }
                except:
                  {"objectIdFieldName":"OBJECTID","uniqueIdField":{"name":"OBJECTID","isSystemMaintained":True},"globalIdFieldName":"","geometryProperties":{"shapeAreaFieldName":"Shape__Area","shapeLengthFieldName":"Shape__Length","units":"esriMeters"},"fields":interDF.fields,"features":[]}
              except:
                interDF = FeatureSet.from_dataframe(df=esriServicesDict[serviceName])
                if callback is None:
                  return {"objectIdFieldName":"OBJECTID","uniqueIdField":{"name":"OBJECTID","isSystemMaintained":True},"globalIdFieldName":"","geometryProperties":{"shapeAreaFieldName":"Shape__Area","shapeLengthFieldName":"Shape__Length","units":"esriMeters"},"fields":interDF.fields,"features":[]}
                else:
                  return HTMLResponse(content=callback+"("+json.dumps({"objectIdFieldName":"OBJECTID","uniqueIdField":{"name":"OBJECTID","isSystemMaintained":True},"globalIdFieldName":"","fields":interDF.fields,"features":[]})+");", media_type="application/javascript; charset=utf-8")
              if callback is None:
                  return JSONResponse(content=esriJSON,media_type="application/json; charset=utf-8")
              else:
                  return HTMLResponse(content=callback+"("+json.dumps(esriJSON)+")", media_type="application/javascript; charset=utf-8")
        
        ### handle pbf format - not working!
        elif f == "pbf":
            quantParam = json.loads(quantizationParameters)
            clippedGDF =  servicesDict[serviceName]
            esriGDF = GeoAccessor.from_geodataframe(clippedGDF,column_name="geometry")
            interDF = FeatureSet.from_dataframe(df=esriGDF)
            esriJSON = {
              "objectIdFieldName" : "OBJECTID",
              "uniqueIdField" : 
              {
                "name" : "OBJECTID", 
                "isSystemMaintained" : True
              },
              "geometryProperties": {
                "shapeAreaFieldName": "Shape__Area",
                "shapeLengthFieldName": "Shape__Length",
                "units": "esriMeters"
              },
              "transform":{
                "originPosition":"upperLeft",
                "scale": {
                  "0": quantParam["tolerance"],
                  "1": quantParam["tolerance"]
                },
                "translate": {
                  "0": quantParam["extent"]["xmin"],
                  "1": quantParam["extent"]["ymax"]
                }
              },
              "geometryType":"esriGeometry" + multiSanitized,
              "globalIdFieldName" : "",
              "hasZ": False,
              "hasM": False,
              "spatialReference" : {"wkid" : 102100, "latestWkid" : 3857},
              "fields" : interDF.fields,
              "features" : interDF.to_dict()["features"],
              "exceededTransferLimit": False
            }
            ###TODO: Find out why pbf is read-only & transform geometry
            pbf = FeatureCollection_pb2.FeatureCollectionPBuffer()
            #pbf.GeometryType = "esriGeometry" + multiSanitized
            #pbf.Field = [interDF.fields]
            #pbf.Transform = esriJSON["transform"]
            #pbf.Geometry = interDF.features
            return JSONResponse(content={"not yet":"implemented"})
        else:
            return {"keine":"Daten"}