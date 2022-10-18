### FastAPI stuff
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
##from brotli_asgi import BrotliMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

### Geo loading and conversion libs
import geopandas as gpd
from shapely.geometry import Polygon, box
import os
import json
from arcgis.features import FeatureSet,GeoAccessor, GeoSeriesAccessor
from arcgis.mapping.renderer import generate_renderer
from arcgis.mapping.symbol import create_symbol, display_colormaps, show_styles
import pandas as pd
from math import isnan
import warnings
import matplotlib


###JSON Templates
from rendererTemplates import pointRenderer, lineRenderer, polygonRenderer
from jsonTemplates import serviceFS, serviceMS, layerSettings

### MapServer image output
from io import BytesIO
from starlette.responses import StreamingResponse
import matplotlib as mpl
import ast
import base64
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

### PBF libs
import FeatureCollection_pb2
import google.protobuf

warnings.filterwarnings('ignore')

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
        serviceFS["initialExtent"]["xmin"] = servicesDict[serviceName].geometry.total_bounds[0]
        serviceFS["initialExtent"]["ymin"] = servicesDict[serviceName].geometry.total_bounds[1]
        serviceFS["initialExtent"]["xmax"] = servicesDict[serviceName].geometry.total_bounds[2]
        serviceFS["initialExtent"]["ymax"] = servicesDict[serviceName].geometry.total_bounds[3]

        serviceFS["fullExtent"]["xmin"] = servicesDict[serviceName].geometry.total_bounds[0]
        serviceFS["fullExtent"]["ymin"] = servicesDict[serviceName].geometry.total_bounds[1]
        serviceFS["fullExtent"]["xmax"] = servicesDict[serviceName].geometry.total_bounds[2]
        serviceFS["fullExtent"]["ymax"] = servicesDict[serviceName].geometry.total_bounds[3]

        serviceFS["layers"][0]["name"] = serviceName
        serviceFS["layers"][0]["geometryType"] = "esriGeometry" + multiSanitized
        
        return serviceFS

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

        serviceMS["mapName"] = serviceName
        serviceMS["layers"][0]["name"] = serviceName
        serviceMS["layers"][0]["geometryType"] = "esriGeometry" + multiSanitized
        serviceMS["initialExtent"]["xmin"] = servicesDict[serviceName].geometry.total_bounds[0]
        serviceMS["initialExtent"]["ymin"] = servicesDict[serviceName].geometry.total_bounds[1]
        serviceMS["initialExtent"]["xmax"] = servicesDict[serviceName].geometry.total_bounds[2]
        serviceMS["initialExtent"]["ymax"] = servicesDict[serviceName].geometry.total_bounds[3]

        serviceMS["fullExtent"]["xmin"] = servicesDict[serviceName].geometry.total_bounds[0]
        serviceMS["fullExtent"]["ymin"] = servicesDict[serviceName].geometry.total_bounds[1]
        serviceMS["fullExtent"]["xmax"] = servicesDict[serviceName].geometry.total_bounds[2]
        serviceMS["fullExtent"]["ymax"] = servicesDict[serviceName].geometry.total_bounds[3]

        if callback is None:
          return JSONResponse(content=serviceMS, media_type="application/json; charset=utf-8")
        else:
          return HTMLResponse(content=callback+"("+json.dumps(serviceMS)+");", media_type="application/javascript; charset=UTF-8")
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

        layerSettings["sourceSpatialReference"] = {"wkid":102100,"latestWkid":3857}
        layerSettings["name"] = serviceName
        layerSettings["geometryType"] = "esriGeometry" + multiSanitized
        layerSettings["fields"] = interDF.fields
        layerSettings["drawingInfo"]["renderer"] = rendererInfo
        layerSettings["extent"]["xmin"] = servicesDict[serviceName].geometry.total_bounds[0]
        layerSettings["extent"]["ymin"] = servicesDict[serviceName].geometry.total_bounds[1]
        layerSettings["extent"]["xmax"] = servicesDict[serviceName].geometry.total_bounds[2]
        layerSettings["extent"]["ymax"] = servicesDict[serviceName].geometry.total_bounds[3]  
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

        layerSettings["sourceSpatialReference"] = {"wkid":102100,"latestWkid":3857}
        layerSettings["name"] = serviceName
        layerSettings["geometryType"] = "esriGeometry" + multiSanitized
        layerSettings["fields"] = interDF.fields
        layerSettings["drawingInfo"]["renderer"] = rendererInfo
        layerSettings["extent"]["xmin"] = servicesDict[serviceName].geometry.total_bounds[0]
        layerSettings["extent"]["ymin"] = servicesDict[serviceName].geometry.total_bounds[1]
        layerSettings["extent"]["xmax"] = servicesDict[serviceName].geometry.total_bounds[2]
        layerSettings["extent"]["ymax"] = servicesDict[serviceName].geometry.total_bounds[3]  
        if callback is None:
          return JSONResponse(content={"layers":[layerSettings]}, media_type="application/json; charset=utf-8")
        else:
          return HTMLResponse(content=callback+"("+json.dumps({"layers":[layerSettings]})+");", media_type="application/javascript; charset=UTF-8")


### MapServer export image route - supports bbox, size and dpi.
### No statistics yet. No jpg support - just plain 32bit png
### For custom symbology layers (Points) the post request appends isCustomSymbol=True and the get /export handles the new symbology accordingly

@app.get("/{serviceName}/MapServer/export")
def root(serviceName:str, size: str=None, bbox: str=None, dpi: int=None, dynamicLayers: str="", isCustomSymbol: str=""):
    if serviceName not in servicesDict.keys():
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        if isCustomSymbol != "True":
          if dynamicLayers != "":
            dynamicLayers = json.loads(dynamicLayers)
            dynLayerFill = dynamicLayers[0]["drawingInfo"]["renderer"]["symbol"]["color"]
            dynLayerOutline = dynamicLayers[0]["drawingInfo"]["renderer"]["symbol"]["outline"]
          else:
            dynLayerFill = [75,172,198,161]
            dynLayerOutline = {"color": [150,150,150,155], "width": 0.75}
          
          boundingBox1 = bbox.split(",")
          boundingBox = []
          for element in boundingBox1:
            boundingBox.append(float(element))
          imgSize = size.split(",")
          mpl.rcParams[ 'figure.figsize' ] = (int(imgSize[0])/dpi,int(imgSize[1])/dpi)
          mpl.rcParams[ 'figure.dpi' ] = dpi
          image = servicesDict[serviceName].plot(linewidth = dynLayerOutline["width"],edgecolor=matplotlib.colors.to_hex([a/255.0 for a in dynLayerOutline["color"]]),color=matplotlib.colors.to_hex([a/255.0 for a in dynLayerFill]))
          image.set_xlim(boundingBox[0], boundingBox[2])
          image.set_ylim(boundingBox[1], boundingBox[3])
          image.set_axis_off();
          image.figure.tight_layout(pad=0)
          buf = BytesIO()
          image.figure.savefig(buf, format="png", transparent=True, pad_inches=0, dpi=dpi)
          buf.seek(0)
        else:
          dynamicLayers = ast.literal_eval(dynamicLayers)
          imageData = dynamicLayers[0]["drawingInfo"]["renderer"]["symbol"]["imageData"].replace(" ","+")
          base64_decoded = base64.b64decode(imageData)

          
          imageWidth = dynamicLayers[0]["drawingInfo"]["renderer"]["symbol"]["width"]
          imageHeight = dynamicLayers[0]["drawingInfo"]["renderer"]["symbol"]["height"]
          imageB64 = Image.open(BytesIO(base64_decoded))

          boundingBox1 = bbox.split(",")
          boundingBox = []
          for element in boundingBox1:
            boundingBox.append(float(element))
          imgSize = size.split(",")
          mpl.rcParams[ 'figure.figsize' ] = (int(imgSize[0])/dpi,int(imgSize[1])/dpi)
          mpl.rcParams[ 'figure.dpi' ] = dpi
          image = servicesDict[serviceName].plot(marker="$6$", markersize=imageWidth)
          image.set_xlim(boundingBox[0], boundingBox[2])
          image.set_ylim(boundingBox[1], boundingBox[3])

          #either get coords of all features and add image.figure on top or do something with matplotlib.path.Path as the marker symbol

          #image.figure.figimage(imageB64.resize(size=(int(imageWidth),int(imageHeight))),500,100,origin="upper")

          image.set_axis_off();
          image.figure.tight_layout(pad=0)
          buf = BytesIO()
          image.figure.savefig(buf, format="png", transparent=True, pad_inches=0, dpi=dpi)
          buf.seek(0)


        
    return StreamingResponse(buf, media_type="image/png")

### MapServer export image route for Point Layers with base64 symbols.

@app.post("/{serviceName}/MapServer/export")
async def root(serviceName:str, request: Request):
    if serviceName not in servicesDict.keys():
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        req_info = await request.form()
        dynamicLayers = json.loads(req_info["dynamicLayers"])
        postInfos = req_info
        postAnswer = {
          "href": "https://"+request.client.host+"/"+serviceName+"/MapServer/export?bbox="+postInfos["bbox"][1:-1]+"&dpi="+postInfos["dpi"]+"&size="+postInfos["size"][1:-1]+"&dynamicLayers="+str(dynamicLayers)+"&isCustomSymbol=True",
          "width": int(postInfos["size"].split(",")[0][1:100]),
          "height": int(postInfos["size"].split(",")[1][0:-1]),
          "extent": {
            "xmin":postInfos["bbox"].split(",")[0][1:100],
            "ymin":postInfos["bbox"].split(",")[1],
            "xmax":postInfos["bbox"].split(",")[2],
            "ymax":postInfos["bbox"].split(",")[3][0:-1]
          },
          "scale": "is this even necessary?"
        }
        
    return postAnswer

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

      
      layerSettings["sourceSpatialReference"] = {"wkid":102100,"latestWkid":3857}
      layerSettings["name"] = serviceName
      layerSettings["geometryType"] = "esriGeometry" + multiSanitized
      layerSettings["fields"] = interDF.fields
      layerSettings["drawingInfo"]["renderer"] = rendererInfo
      layerSettings["extent"]["xmin"] = servicesDict[serviceName].geometry.total_bounds[0]
      layerSettings["extent"]["ymin"] = servicesDict[serviceName].geometry.total_bounds[1]
      layerSettings["extent"]["xmax"] = servicesDict[serviceName].geometry.total_bounds[2]
      layerSettings["extent"]["ymax"] = servicesDict[serviceName].geometry.total_bounds[3]        

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

        layerSettings["name"] = serviceName
        layerSettings["geometryType"] = "esriGeometry" + multiSanitized
        layerSettings["fields"] = interDF.fields
        layerSettings["drawingInfo"]["renderer"] = rendererInfo
        layerSettings["extent"]["xmin"] = servicesDict[serviceName].geometry.total_bounds[0]
        layerSettings["extent"]["ymin"] = servicesDict[serviceName].geometry.total_bounds[1]
        layerSettings["extent"]["xmax"] = servicesDict[serviceName].geometry.total_bounds[2]
        layerSettings["extent"]["ymax"] = servicesDict[serviceName].geometry.total_bounds[3]        

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

        layerSettings["name"] = serviceName
        layerSettings["geometryType"] = "esriGeometry" + multiSanitized
        layerSettings["fields"] = interDF.fields
        layerSettings["drawingInfo"]["renderer"] = rendererInfo
        layerSettings["extent"]["xmin"] = servicesDict[serviceName].geometry.total_bounds[0]
        layerSettings["extent"]["ymin"] = servicesDict[serviceName].geometry.total_bounds[1]
        layerSettings["extent"]["xmax"] = servicesDict[serviceName].geometry.total_bounds[2]
        layerSettings["extent"]["ymax"] = servicesDict[serviceName].geometry.total_bounds[3]
        if callback is None:
            return JSONResponse(content=layerSettings, media_type="application/json; charset=utf-8")
        else:
            return HTMLResponse(content=callback+"("+json.dumps(layerSettings)+");", media_type="application/javascript; charset=UTF-8")

@app.get("/{serviceName}/FeatureServer/0/generateRenderer")
def root(serviceName:str, f: str = "json", callback: str=None, classificationDef: str=None):
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
        clasDef = json.loads(classificationDef)
        r = generate_renderer(
          geometry_type = multiSanitized,
          sdf_or_series = esriGDF,
          label =  serviceName,
          renderer_type = clasDef["type"][0]
        )
        if callback is None:
            return JSONResponse(content=r, media_type="application/json; charset=utf-8")
        else:
            return HTMLResponse(content=callback+"("+json.dumps(r)+");", media_type="application/javascript; charset=UTF-8")


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
          count = {"count": len(esriServicesDict[serviceName].index)}
          if callback is None:
              return JSONResponse(content=count,media_type="application/json; charset=utf-8")
          else:
              return HTMLResponse(content=callback+"("+json.dumps(count)+")", media_type="application/javascript; charset=utf-8")

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
          if callback is None:
              return JSONResponse(content=esriJSON,media_type="application/json; charset=utf-8")
          else:
              return HTMLResponse(content=callback+"("+json.dumps(esriJSON)+")", media_type="application/javascript; charset=utf-8")

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
            if callback is None:
                return JSONResponse(content=statReturn,media_type="application/json; charset=utf-8")
            else:
                return HTMLResponse(content=callback+"("+json.dumps(statReturn)+")", media_type="application/javascript; charset=utf-8")

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

            if callback is None:
                return JSONResponse(content=statReturn,media_type="application/json; charset=utf-8")
            else:
                return HTMLResponse(content=callback+"("+json.dumps(statReturn)+")", media_type="application/javascript; charset=utf-8")

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
              if callback is None:
                return JSONResponse(content=esriJSON,media_type="application/json; charset=utf-8")
              else:
                return HTMLResponse(content=callback+"("+json.dumps(esriJSON)+")", media_type="application/javascript; charset=utf-8")
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