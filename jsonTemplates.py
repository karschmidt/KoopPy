serviceFS = {
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
            "xmin": None,
            "ymin": None,
            "xmax": None,
            "ymax": None,
            "spatialReference": {
            "wkid": 102100,
            "latestWkid": 3857
            }
        },
        "fullExtent": {
            "xmin": None,
            "ymin": None,
            "xmax": None,
            "ymax": None,
            "spatialReference": {
            "wkid": 102100,
            "latestWkid": 3857
            }
        },
        "allowGeometryUpdates": False,
        "units": "esriDecimalDegrees",
        "syncEnabled": False,
        "layers": [{
            "name": None,
            "id": 0,
            "parentLayerId": -1,
            "defaultVisibility": True,
            "subLayerIds": None,
            "minScale": 0,
            "maxScale": 0,
            "geometryType": None

        }],
        "tables": []
        }

serviceMS = {
          "currentVersion": 10.5,
          "serviceDescription": "MapServer using KoopPy by Karsten Schmidt",
          "mapName": None,
          "description": "MapServer using KoopPy by Karsten Schmidt",
          "copyrightText": "",
          "supportsDynamicLayers": True,
          "layers": [{
            "name": None,
            "id": 0,
            "parentLayerId": -1,
            "defaultVisibility": True,
            "subLayerIds": None,
            "minScale": 0,
            "maxScale": 0,
            "type": "Feature Layer",
            "geometryType": None,
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
            "xmin": None,
            "ymin": None,
            "xmax": None,
            "ymax": None,
            "spatialReference": {
            "wkid": 102100,
            "latestWkid": 3857
            }
        },
        "fullExtent": {
            "xmin": None,
            "ymin": None,
            "xmax": None,
            "ymax": None,
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

layerSettings = {
        "currentVersion":10.5,
        "id":0,
        "name": None,
        "type":"Feature Layer",
        "description":"Data served by KoopPy",
        "geometryType":None,
        "copyrightText":"",
        "parentLayer":None,
        "subLayers":None,
        "minScale":0,
        "maxScale":0,
        "fields": None,
        "drawingInfo":{
                "renderer": None
        },
        "defaultVisibility":True,
        "extent":{
            "xmin": None,
            "ymin": None,
            "xmax": None,
            "ymax": None,
            "spatialReference":{
                "wkid":102100,
                "latestWkid":3857
            }
        },
        "hasAttachments":False,
        "displayField":"OBJECTID",
        "typeIdField":None,
        "relationships":[],
        "canModifyLayer":True,
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
        "hasStaticData":True
    }