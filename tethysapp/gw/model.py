# Put your persistent store models in this file
import ujson as json
import os
import csv
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, ForeignKey, UniqueConstraint, PickleType
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import and_
from .app import Gw as app
from django.http import Http404, HttpResponse, JsonResponse
from rasterio.transform import from_bounds, from_origin
from rasterio.warp import reproject, Resampling
import rasterio
import numpy as np
import elevation
from sqlalchemy import literal

Base = declarative_base()
app_workspace = app.get_app_workspace()


# SQLAlchemy ORM definition for the timeseries table
class Well(Base):
    # SQLAlchemy Dam DB Model
    __tablename__ = 'wells'

    # Columns
    id = Column(Integer, primary_key=True)
    latitude = Column(Float)
    longitude = Column(Float)
    HydroID = Column(Integer, unique=True)
    Elevation = Column(Integer)
    Depth = Column(Integer)
    AquiferID = Column(Integer)
    FType = Column(String)
    timeseries = relationship("Timeseries")

    # Relationships
    #timeseries=relationship('Timeseries', back_populates='wells')


class Timeseries(Base):
    """SQLAlchemy Hydrograph DB Model"""
    __tablename__ = 'timeseries'

    # Columns
    id = Column(Integer, primary_key=True)
    FeatureID = Column(Integer, ForeignKey('wells.HydroID'))
    TsTime = Column(String)
    TsValue = Column(Float)
    TsValue_normalized = Column(Float)
    # Relationships
    # wells=relationship('Well', back_populates='timeseries')


class Aquifers(Base):
    """SQLAlchemy Aquifers DB Model"""
    __tablename__ = 'aquifers'

    # Columns
    id = Column(Integer, primary_key=True)
    AquiferID = Column(String)
    AquiferName = Column(String)
    AquiferFileName = Column(String)
    AquiferWellsJSON = Column(PickleType)
    AquiferShapeJSON = Column(PickleType)
    AquiferDEM = Column(PickleType)
    AquiferType = Column(String)
    RegionName = Column(String)


class Regions(Base):
    """SQLAlchemy Regions DB Model"""
    __tablename__ = 'regions'

    # Columns
    id = Column(Integer, primary_key=True)
    RegionName = Column(String)
    RegionFileName = Column(String)
    RegionJSON = Column(PickleType)
    Units = Column(String)


def init_primary_db(engine, first_time):
    # Initializer for the primary database.
    # Create all the tables
    Base.metadata.create_all(engine)
    # if first_time:
    #     # Make session
    Session = sessionmaker(bind=engine)
    session = Session()
    # dirs = next(os.walk(app_workspace.path))[1]
    # for region in dirs:
    #     print(region)
    #     aquifer_dir=os.path.join(app_workspace.path,region,'aquifers')
    #     for aquiferfile in os.listdir(aquifer_dir):
    #         print(aquiferfile)
    #         file_path = os.path.join(app_workspace.path, region,'aquifers',aquiferfile)
    #         aquiferpath=os.path.join(app_workspace.path, region,'MajorAquifers.json')
    #         if os.path.exists(file_path) and os.path.exists(aquiferpath):
    #             with open(file_path, 'r') as f:
    #                 aquifer_json = json.load(f)
    #             with open(aquiferpath) as f:
    #                 aquifer_attr=json.load(f)
    #             if 'AquiferID' in aquifer_json['features'][0]['properties']:
    #                 aquifer=Aquifers(
    #                     AquiferID=aquifer_json['features'][0]['properties']['AquiferID'],
    #                     AquiferWellsJSON=aquifer_json,
    #                     AquiferName=aquiferfile[:-5].replace("_",""),
    #                     AquiferFileName = aquiferfile[:-5],
    #                     # AquiferShapeJSON = Column(PickleType),
    #                     # AquiferDEM = Column(PickleType),
    #                     # AquiferType = Column(String),
    #                     RegionName = region.replace("_","")
    #                 )
    #                 session.add(aquifer)
    #             else:
    #                 print("No AquiferID for", aquiferfile)

    print("Added the aquifer to persistent store")
    session.commit()
    print("aquifer committed to persistent store")
    session.close()


def add_region(region, units):

    Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
    session = Session()
    q = session.query(Regions).filter(Regions.RegionFileName == region)
    exists = session.query(literal(True)).filter(q.exists()).scalar()

    if exists == None:
        regionfile = os.path.join(app_workspace.path, region + '/'+region+'_State_Boundary.json')
        with open(regionfile, 'r') as f:
            regionfile = json.load(f)
        myregion = Regions(
            RegionName=region.replace("_", " "),
            RegionFileName=region,
            RegionJSON=regionfile,
            Units=units
        )
        session.add(myregion)
        print("Added the region to persistent store")
        session.commit()
        print("region committed to persistent store")
    session.close()
    return


def add_aquifer(points, region, name, myaquifer, units):
    Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
    session = Session()
    q = session.query(Aquifers).filter(Aquifers.AquiferName == name)
    exists = session.query(literal(True)).filter(q.exists()).scalar()
    print(name)

    if exists == None:

        # Download and Set up the DEM for the aquifer
        dem_json = download_DEM(region, myaquifer, units)
        minorfile = os.path.join(app_workspace.path, region + '/MinorAquifers.json')
        majorfile = os.path.join(app_workspace.path, region + '/MajorAquifers.json')
        regionfile = os.path.join(app_workspace.path, region, region + '_State_Boundary.json')

        aquiferShape = {
            'type': 'FeatureCollection',
            'features': []
        }
        fieldname = 'Aquifer_Name'
        match = False
        region_override = False
        if os.path.exists(minorfile):
            with open(minorfile, 'r') as f:
                minor = json.load(f)
            for i in minor['features']:
                if fieldname in i['properties']:
                    if i['properties'][fieldname] == myaquifer['CapsName']:
                        i['properties']['Name'] = i['properties'][fieldname]
                        i['properties']['Id'] = myaquifer['Id']
                        aquiferShape['features'].append(i)
                        mytype = "Minor"
                        match = True
        if os.path.exists(majorfile) and match == False:
            with open(majorfile, 'r') as f:
                major = json.load(f)
            for i in major['features']:
                if fieldname in i['properties']:
                    if i['properties'][fieldname] == myaquifer['CapsName']:
                        i['properties']['Name'] = i['properties'][fieldname]
                        i['properties']['Id'] = myaquifer['Id']
                        aquiferShape['features'].append(i)
                        mytype = "Major"
                        match = True
        if os.path.exists(regionfile) and match == False:
            with open(regionfile, 'r') as f:
                aquiferShape = json.load(f)
                region_override = True
            mytype = "Region"
            # id=-999
        if len(aquiferShape['features']) > 0:
            if 'AquiferID' in points['features'][0]['properties'] or region_override:
                aquifer = Aquifers(
                    AquiferID=myaquifer['Id'],
                    AquiferWellsJSON=points,
                    AquiferName=name,
                    AquiferFileName=name.replace(" ", "_"),
                    AquiferShapeJSON=aquiferShape,
                    AquiferDEM=dem_json,
                    AquiferType=mytype,
                    RegionName=region.replace("_", " ")
                )
                session.add(aquifer)
                print("Added the aquifer to persistent store")
                session.commit()
                print("aquifer committed to persistent store")

        else:
            print("No AquiferID for", name)
    else:
        print("No Aquifer named ", name)
    session.close()
    return


def get_aquifer_wells(request):
    return_obj = {
        'success': False
    }
    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        aquifer_id = request.GET.get('aquifer_id')
        region = request.GET.get('region')

        Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
        session = Session()
        all_wells = session.query(Aquifers).filter(Aquifers.AquiferID == aquifer_id,
                                                   Aquifers.RegionName == region.replace("_", " "))
        for well in all_wells:
            return_obj['data'] = well.AquiferWellsJSON
        session.close()
    return JsonResponse(return_obj)

# The explode and bbox functions are used to get the bounding box of a geoJSON object


def explode(coords):
    """Explode a GeoJSON geometry's coordinates object and yield coordinate tuples.
    As long as the input is conforming, the type of the geometry doesn't matter."""
    for e in coords:
        if isinstance(e, (float, int, long)):
            yield coords
            break
        else:
            for f in explode(e):
                yield f


def bbox(f):
    x, y = zip(*list(explode(f['geometry']['coordinates'])))
    return round(np.min(x)-.05, 1), round(np.min(y)-.05, 1), round(np.max(x)+.05, 1), round(np.max(y)+.05, 1)


def download_DEM(region, myaquifer, units):
    # Download and Set up the DEM for the aquifer
    app_workspace = app.get_app_workspace()
    name = myaquifer['Name']
    directory = os.path.join(app_workspace.path, region + '/DEM')
    if not os.path.exists(directory):
        os.makedirs(directory)
    minorfile = os.path.join(app_workspace.path, region + '/MinorAquifers.json')
    majorfile = os.path.join(app_workspace.path, region + '/MajorAquifers.json')
    regionfile = os.path.join(app_workspace.path, region, region + '_State_Boundary.json')
    aquiferShape = {
        'type': 'FeatureCollection',
        'features': []
    }
    fieldname = 'Aquifer_Name'
    print("Setting up DEM")
    match = False
    if os.path.exists(minorfile):
        with open(minorfile, 'r') as f:
            minor = json.load(f)
        for i in minor['features']:
            if fieldname in i['properties']:
                if i['properties'][fieldname] == myaquifer['CapsName']:
                    aquiferShape['features'].append(i)
                    match = True
    if os.path.exists(majorfile) and match == False:
        with open(majorfile, 'r') as f:
            major = json.load(f)
        for i in major['features']:
            if fieldname in i['properties']:
                if i['properties'][fieldname] == myaquifer['CapsName']:
                    aquiferShape['features'].append(i)
                    match = True
    if os.path.exists(regionfile) and match == False:
        with open(regionfile, 'r') as f:
            aquiferShape = json.load(f)
    try:
        lonmin, latmin, lonmax, latmax = bbox(aquiferShape['features'][0])
    except:
        long = 0
        answer = 0
        for f in range(len(aquiferShape['features'])):
            if aquiferShape['features'][f]['geometry'] != None:
                x, y = zip(*list(explode(aquiferShape['features'][f]['geometry']['coordinates'])))
                if len(x) > long:
                    long = len(x)
                    answer = f
        lonmin, latmin, lonmax, latmax = bbox(aquiferShape['features'][answer])

    bounds = (lonmin - .1, latmin - .1, lonmax + .1, latmax + .1)
    dem_path = name.replace(' ', '_') + '_DEM.tif'
    demfile = os.path.join(app_workspace.path, region + '/DEM.tif')
    if(os.path.exists(demfile)):
        output = demfile
    else:
        output = os.path.join(directory, dem_path)
        elevation.clip(bounds=bounds, output=output, product='SRTM3')
    print("90 m DEM successfully downloaded for ", name)

    if units:
        # Reproject DEM to 0.01 degree resolution using rasterio
        resolution = .01
        with rasterio.open(output) as dem_raster:
            src_crs = dem_raster.crs
            src_shape = src_height, src_width = dem_raster.shape
            src_transform = dem_raster.transform  # from_bounds(lonmin, latmin, lonmax, latmax, src_width, src_height)
            source = dem_raster.read(1)
            dem_json = {'source': source,
                        'src_crs': src_crs,
                        'src_transform': src_transform}
        return dem_json
