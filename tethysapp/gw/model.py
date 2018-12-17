# Put your persistent store models in this file
import ujson as json
import os
import csv
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import and_
from.app import Gw as app
from django.http import Http404, HttpResponse, JsonResponse

Base=declarative_base()
csv_file="csv/Wells_time.csv"
app_workspace = app.get_app_workspace()

def read_well_data():
    geolayer="Wells1.json"
    geofile = os.path.join(app_workspace.path, geolayer)
    with open(geofile, 'r') as f:
        allwells = ''
        wells = f.readlines()
        for i in range(0, len(wells)):
            allwells += wells[i]
    wells_json = json.loads(allwells)
    return wells_json

def read_time_data():

    file_path = os.path.join(app_workspace.path, csv_file)
    time_csv=[]

    with open(file_path) as csvfile:
        reader=csv.DictReader(csvfile)
        for row in reader:
            timestep=((row['FeatureID']),(row['TsTime']),(row['TsValue']),(row['TsValue_normalized']))
            time_csv.append(timestep)

    return time_csv



# SQLAlchemy ORM definition for the timeseries table
class Well(Base):
    #SQLAlchemy Dam DB Model
    __tablename__='wells'

    # Columns
    id=Column(Integer, primary_key=True)
    latitude=Column(Float)
    longitude=Column(Float)
    HydroID=Column(Integer, unique=True)
    Elevation=Column(Integer)
    Depth=Column(Integer)
    AquiferID=Column(Integer)
    FType=Column(String)
    timeseries=relationship("Timeseries")

    #Relationships
    #timeseries=relationship('Timeseries', back_populates='wells')

class Timeseries(Base):
    """SQLAlchemy Hydrograph DB Model"""
    __tablename__='timeseries'

    # Columns
    id=Column(Integer, primary_key=True)
    FeatureID=Column(Integer, ForeignKey('wells.HydroID'))
    TsTime=Column(String)
    TsValue=Column(Float)
    TsValue_normalized=Column(Float)


    #Relationships
    #wells=relationship('Well', back_populates='timeseries')

def init_primary_db(engine, first_time):
    # Initializer for the primary database.
    # Create all the tables
    Base.metadata.create_all(engine)

    if first_time:
        # Make session
        Session=sessionmaker(bind=engine)
        session=Session()

        time_data=read_time_data()
        well_data=read_well_data()

        for well in well_data['features']:
            well=Well(
                latitude=well['geometry']['coordinates'][1],
                longitude=well['geometry']['coordinates'][0],
                HydroID=well['properties']['HydroID'],
                Elevation=well['properties']['LandElev'],
                Depth=well['properties']['WellDepth'],
                AquiferID=well['properties']['AquiferID'],
                FType=well['properties']['FType']
            )

            session.add(well)

        print("Added the well_data to persistent store")
        session.commit()
        print("well_data committed to persistent store")

        for item in time_data:
            print(item[0])
            if item[0]!='':
                data=Timeseries(
                FeatureID=item[0],
                )
                if item[1]!='':
                    data.TsTime=item[1]
                if item[2]!='':
                    data.TsValue=item[2]
                if item[3]!='':
                    data.TsValue_normalized=item[3]
                if data:
                    session.add(data)


        print("Time data added")
        session.commit()
        print("Time data committed")
        session.close()



def retrieve_Wells(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        geolayer = request.GET.get('geolayer')
        min_num=request.GET.get('min_num')
        return_obj['geolayer'] = geolayer
        return_obj['min_num']=min_num
        Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
        session = Session()
        n=int(geolayer)
        min_num=int(min_num)
        if min_num>0:
            all_wells = session.query(Well).filter(and_(Well.AquiferID == n,Well.timeseries))
        else:
            all_wells = session.query(Well).filter(Well.AquiferID==n)

        # features=[]
        #
        # for well in all_wells:
        #     if well.timeseries:
        #         TsTime=[]
        #         TsValue=[]
        #         TsValue_normalized=[]
        #         for point in well.timeseries:
        #             TsTime.append(point.TsTime)
        #             TsValue.append(point.TsValue)
        #             TsValue_normalized.append(point.TsValue_normalized)
        #         well_feature={
        #             'type': 'Feature',
        #             'geometry':{
        #                 'type':'Point',
        #                 'coordinates':[well.longitude,well.latitude]
        #             },
        #             'properties':{
        #                 'HydroID':well.HydroID,
        #                 'LandElev':well.Elevation,
        #                 'WellDepth':well.Depth,
        #                 'AquiferID':well.AquiferID,
        #                 'FType':well.FType
        #             },
        #             'timeseries':{
        #                 'TsTime':TsTime,
        #                 'TsValue':TsValue,
        #                 'TsValue_normalized':TsValue_normalized
        #             }
        #         }
        #     else:
        #         well_feature = {
        #             'type': 'Feature',
        #             'geometry': {
        #                 'type': 'Point',
        #                 'coordinates': [well.longitude, well.latitude]
        #             },
        #             'properties': {
        #                 'HydroID': well.HydroID,
        #                 'LandElev': well.Elevation,
        #                 'WellDepth': well.Depth,
        #                 'AquiferID': well.AquiferID,
        #                 'FType': well.FType
        #             }
        #         }
        #     features.append(well_feature)
        #     print(well_feature['properties']['HydroID'])
        # json_string=json.dumps(features)

        json_string='{"type":"FeatureCollection", "features": ['
        for well in all_wells:
            json_string+='{"type":"Feature","geometry":{"type":"Point","coordinates":['+str(well.longitude)+','+str(well.latitude)+']},'\
                         +'"properties":{"HydroID":'+str(well.HydroID)+',"LandElev":'+str(well.Elevation)+',"WellDepth":'+str(well.Depth)\
                         +',"AquiferID":'+str(well.AquiferID)+',"FType":"'+str(well.FType)+'"}'
            if well.timeseries:
                json_string+=',"timeseries":{"TsTime":'
                time='['
                tsvalue=',"TsValue":['
                tsvaluenorm=',"TsValue_normalized":['
                for point in well.timeseries:
                    time+='"'+str(point.TsTime)+'",'
                    tsvalue+=str(point.TsValue)+','
                    tsvaluenorm+=str(point.TsValue_normalized)+','
                time=time[:-1]
                tsvalue=tsvalue[:-1]
                tsvaluenorm=tsvaluenorm[:-1]
                time+=']'
                tsvalue+=']'
                tsvaluenorm+=']'
                json_string+=time
                json_string+=tsvalue
                if point.TsValue_normalized:
                    json_string+=tsvaluenorm
                json_string+='}},'
            else:
                json_string+='},'
        json_string=json_string[:-1]
        json_string+=']}'

        return_obj=json.loads(json_string)
        session.close()
    return JsonResponse(return_obj)

#