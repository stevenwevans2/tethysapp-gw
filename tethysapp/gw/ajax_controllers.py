from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from django.http import Http404, HttpResponse, JsonResponse
import netCDF4
import numpy as np
import time as t
from operator import itemgetter
from shapely.geometry import Point
from shapely.geometry import shape
from hs_restclient import HydroShare, HydroShareAuthBasic
from .uploadnetcdf import *

#We will now use a PostGIS database instead of the workspace and work on the branch

#Check if the user is superuser or staff. Only the superuser or staff have the permission to add and manage watersheds.
def user_permission_test(user):
    return user.is_superuser or user.is_staff


#displaygeojson is an Ajax function that reads a specified JSON File (geolayer) in a specified region (region)
# and returns the JSON object from that file.
def displaygeojson(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        geolayer = request.GET.get('geolayer')
        region=request.GET.get('region')
        return_obj['geolayer'] = geolayer
        app_workspace = app.get_app_workspace()
        geofile = os.path.join(app_workspace.path, region+"/"+geolayer)
        aquiferlist = getaquiferlist(app_workspace, region)
        fieldnames=[]
        for i in aquiferlist:
            fieldnames.append(i['FieldName'])
        if os.path.exists(geofile):
            with open(geofile, 'r') as f:
                return_obj['state']=json.load(f)
            #     allwells = ''
            #     wells = f.readlines()
            #     for i in range(0, len(wells)):#len(wells)
            #         allwells += wells[i]
            # return_obj['state'] = json.loads(allwells)
        minorfile = os.path.join(app_workspace.path, region + '/MinorAquifers.json')
        majorfile = os.path.join(app_workspace.path, region + '/MajorAquifers.json')
        if os.path.exists(minorfile):
            with open(minorfile, 'r') as f:
                minor=''
                entry=f.readlines()
                for i in range(0, len(entry)):
                    minor += entry[i]
                minoraquifers = json.loads(minor)
                for j in fieldnames:
                    if j in minoraquifers['features'][0]['properties']:
                        fieldname=j
                for k in minoraquifers['features']:
                    for l in aquiferlist:
                        if k['properties'][fieldname]==l['CapsName']:
                            k['properties']['Id']=l['Id']
                            k['properties']['Name']=l["Name"]
            return_obj['minor'] = minoraquifers
        if os.path.exists(majorfile):
            with open(majorfile, 'r') as f:
                major=''
                entry=f.readlines()
                for i in range(0, len(entry)):
                    major += entry[i]
                majoraquifers = json.loads(major)
                for j in fieldnames:
                    if j in majoraquifers['features'][0]['properties']:
                        fieldname=j
                for k in majoraquifers['features']:
                    for l in aquiferlist:
                        if k['properties'][fieldname]==l['CapsName']:
                            k['properties']['Id']=l['Id']
                            k['properties']['Name']=l['Name']
            return_obj['major']=majoraquifers

    return JsonResponse(return_obj)

#loadjson Ajax function takes an aquifer_id number (aquifer_number) and a region (region) and opens the aquifer JSON files for that region
# and returns the GeoJSON object for the specified aquifer number in that region.
def loadjson(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        aquifer_number = request.GET.get('aquifer_number')
        region=request.GET.get('region')
        app_workspace = app.get_app_workspace()
        aquiferlist=getaquiferlist(app_workspace,region)

        for i in aquiferlist:
            if i['Id'] == int(aquifer_number):
                myaquifer = i
        minorfile = os.path.join(app_workspace.path, region+'/MinorAquifers.json')
        majorfile = os.path.join(app_workspace.path, region+'/MajorAquifers.json')
        aquiferShape = []
        fieldname=myaquifer['FieldName']

        if os.path.exists(minorfile):
            with open(minorfile, 'r') as f:
                minor = ''
                entry = f.readlines()
                for i in range(0, len(entry)):
                    minor += entry[i]
            minor = json.loads(minor)
            for i in minor['features']:
                if fieldname in i['properties']:
                    if i['properties'][fieldname]==myaquifer['CapsName']:
                        aquiferShape.append(i)

        if os.path.exists(majorfile):
            with open(majorfile, 'r') as f:
                major = ''
                entry = f.readlines()
                for i in range(0, len(entry)):
                    major += entry[i]
            major=json.loads(major)
            for i in major['features']:
                if fieldname in i['properties']:
                    if i['properties'][fieldname]==myaquifer['CapsName']:
                        aquiferShape.append(i)

        return_obj['data']=aquiferShape
        return_obj['aquifer']=myaquifer
    return JsonResponse(return_obj)




#The loadaquiferlist ajax function takes a region as a parameter and returns a JSON object with the list of Aquifers in that region
def loadaquiferlist(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        region=request.GET.get('region')

        app_workspace = app.get_app_workspace()
        aquiferlist=getaquiferlist(app_workspace,region)
        return_obj['aquiferlist']=aquiferlist
    return JsonResponse(return_obj)

#The loadaquiferlist ajax function takes a region as a parameter and returns a JSON object with the list of Aquifers in that region
def loadtimelist(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        region=request.GET.get('region')
        aquifer=request.GET.get('aquifer')

        timelist=gettimelist(region,aquifer)
        return_obj['timelist']=timelist
    return JsonResponse(return_obj)

def gettotalvolume(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        region=request.GET.get('region')
        name=request.GET.get('name')
        directory = os.path.join(thredds_serverpath, region)
        nc_file=os.path.join(directory,name)
        h = netCDF4.Dataset(nc_file, 'r+')
        volumelist=np.array(h.variables['totalvolume'][:]).tolist()
        timelist=np.array(h.variables['time'][:]).tolist()
        h.close()

        return_obj['volumelist']=volumelist
        return_obj['timelist']=timelist
    return JsonResponse(return_obj)

#This Ajax Controller ckecks whether a specified NetCDF file contains total aquifer storage volume.
def checktotalvolume(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        region=request.GET.get('region')
        name=request.GET.get('name')
        exists=False
        directory = os.path.join(thredds_serverpath, region)
        nc_file=os.path.join(directory,name)
        if os.path.exists(nc_file):
            h = netCDF4.Dataset(nc_file, 'r+')
            if 'totalvolume' in h.variables:
                exists=True
            aquifer=name.split('.')[0].replace('_',' ')
            return_obj['abstract']='This resource contains a NetCDF file containing groundwater elevation, depth to groundwater, and groundwater drawdown in the '+aquifer+' aquifer, located in '+region.replace("_"," ")+', between '+str(h.start_date)+' and '+str(h.end_date)+', at '+str(h.resolution)+' degree resolution. The NetCDF file was created using the Tethys Groundwater Level Mapping Tool.'
            return_obj['filepath']=os.path.join(thredds_serverpath, region+'/'+name)
            return_obj['keywords']="Groundwater,"+region.replace("_"," ")
            return_obj['title']="Groundwater levels for "+aquifer+" in "+region.replace("_"," ")
            return_obj['type']='GenericResource'
            return_obj['metadata'] = '[{"coverage":{"type":"period", "value":{"start":'+str(h.start_date)+', "end":'+str(h.end_date)+'}}},{"creator":{"name":"stevenwevans2@gmail.com"}}]'
            h.close()

        return_obj['exists']=exists
    return JsonResponse(return_obj)

def deletenetcdf(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        region=request.GET.get('region')
        name=request.GET.get('name')

        directory = os.path.join(thredds_serverpath, region)
        file=os.path.join(directory,name)
        os.remove(file)

    return JsonResponse(return_obj)

def addoutlier(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        region=request.GET.get('region')
        aquifer=request.GET.get('aquifer')
        hydroId=request.GET.get('hydroId')
        edit=request.GET.get('edit')

        app_workspace=app.get_app_workspace()

        aquifer=aquifer.replace(" ","_")
        file = os.path.join(app_workspace.path, region + '/aquifers/'+aquifer+'.json')
        if os.path.exists(file):
            with open(file, 'r') as f:
                wells = ''
                entry = f.readlines()
                for i in range(0, len(entry)):
                    wells += entry[i]
            wells = json.loads(wells)
            for i in wells['features']:
                if i['properties']['HydroID']==int(hydroId):
                    if edit=="add":
                        i['properties']['Outlier']=True
                    elif edit=="remove":
                        i['properties']['Outlier']=False
            with open(file, 'w') as outfile:
                json.dump(wells, outfile)

    return JsonResponse(return_obj)

def defaultnetcdf(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        region=request.GET.get('region')
        aquifer=request.GET.get('aquifer')
        name=request.GET.get('name')

        aquifer=aquifer.replace(" ","_")
        directory = os.path.join(thredds_serverpath, region)
        for filename in os.listdir(directory):
            if filename.startswith(aquifer+'.'):
                nc_file = os.path.join(directory, filename)
                #os.chmod(nc_file, 0o777)
                h = netCDF4.Dataset(nc_file, 'r+', format="NETCDF4")
                if filename==name and h.default !=1:
                    h.default=1
                elif filename!=name:
                    h.default=0
                h.close()

    return JsonResponse(return_obj)

#The loaddata ajax function takes id, name, interpolation type, and region as parameters.
#The function checks whether the NetCDF interpolation file already exists, and checks whether the region is already divided by aquifer
#If the region is not divided, it calls functions to divide the aquifer. Then the JSON file for the specified aquifer is opened.
#If the NetCDF file does not already exist, the upoad_netcdf function is called to interpolate and upload to the server
def loaddata(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        aquiferid = request.GET.get('id')
        region=request.GET.get('region')
        start_date=request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        interval = request.GET.get('interval')
        resolution = request.GET.get('resolution')
        length=request.GET.get('length')
        interpolation_type=request.GET.get('interpolation_type')
        make_default=request.GET.get("make_default")
        min_samples=request.GET.get("min_samples")
        min_ratio=request.GET.get("min_ratio")
        time_tolerance=request.GET.get('time_tolerance')
        from_wizard=request.GET.get("from_wizard")
        units=request.GET.get("units")

        return_obj['id'] = aquiferid
        app_workspace = app.get_app_workspace()
        aquiferid=int(aquiferid)

        make_default = int(make_default)
        from_wizard=int(from_wizard)

        if interpolation_type:
            start_date=int(start_date)
            end_date=int(end_date)
            interval=float(interval)
            resolution=float(resolution)
            length=int(length)
            min_samples=int(min_samples)
            min_ratio=float(min_ratio)
            time_tolerance=int(time_tolerance)


        if aquiferid==9999:
            for i in range(1,length):
                aquiferid=i
                points,returnmessage=interp_wizard(app_workspace, aquiferid, region, interpolation_type, start_date, end_date, interval, resolution, make_default, min_samples, min_ratio, time_tolerance, from_wizard, units)
        else:
            points,returnmessage=interp_wizard(app_workspace, aquiferid, region, interpolation_type, start_date, end_date, interval, resolution, make_default, min_samples, min_ratio, time_tolerance,  from_wizard, units)

        return_obj['data']=points
        return_obj['message']=returnmessage
    return JsonResponse(return_obj)


#This function takes a region and aquiferid number and writes a new JSON file with data for the specified aquifer
#This function uses data from the Wells.json file for the region.
def divideaquifers(region,app_workspace,aquiferid):
    aquiferlist = getaquiferlist(app_workspace, region)
    for i in aquiferlist:
        if i['Id'] == int(aquiferid):
            myaquifer = i
    minorfile = os.path.join(app_workspace.path, region + '/MinorAquifers.json')
    majorfile = os.path.join(app_workspace.path, region + '/MajorAquifers.json')
    aquiferShape = []
    fieldname = myaquifer['FieldName']

    if os.path.exists(minorfile):
        with open(minorfile, 'r') as f:
            minor = ''
            entry = f.readlines()
            for i in range(0, len(entry)):
                minor += entry[i]
        minor = json.loads(minor)
        for i in minor['features']:
            if fieldname in i['properties']:
                if i['properties'][fieldname] == myaquifer['CapsName']:
                    aquiferShape.append(i)

    if os.path.exists(majorfile):
        with open(majorfile, 'r') as f:
            major = ''
            entry = f.readlines()
            for i in range(0, len(entry)):
                major += entry[i]
        major = json.loads(major)
        for i in major['features']:
            if fieldname in i['properties']:
                if i['properties'][fieldname] == myaquifer['CapsName']:
                    aquiferShape.append(i)

    filename=region+"/Wells.json"
    json_file=os.path.join(app_workspace.path,filename)
    with open(json_file, 'r') as f:
        allwells = ''
        wells = f.readlines()
        for i in range(0, len(wells)):
            allwells += wells[i]
    all_points = json.loads(allwells)

    if len(aquiferShape)>0:
        polygon = shape(aquiferShape[0]['geometry'])
        points = {
            'type': 'FeatureCollection',
            'features': []
        }
        aquifermin=0.0
        for well in all_points['features']:
            point=Point(well['geometry']['coordinates'])
            if polygon.contains(point):
                well['properties']['AquiferID']=int(aquiferid)
                points['features'].append(well)
                for i in well['TsValue']:
                    if i<aquifermin:
                        aquifermin=i
        print len(points['features'])
        points['aquifermin'] = aquifermin
    else:
        points=all_points

    name = myaquifer['Name']
    directory = os.path.join(app_workspace.path, region + '/aquifers')
    if not os.path.exists(directory):
        os.makedirs(directory)
    # Write a json file to the app workspace for the specified aquifer.
    # This file includes all the geographical, time series, and properties data for the aquifer.
    filename = name.replace(' ', '_') + '.json'
    filename = os.path.join(app_workspace.path, region + '/aquifers/' + filename)

    with open(filename, 'w') as outfile:
        json.dump(points, outfile)
    # Download and Set up the DEM for the aquifer
    download_DEM(region, myaquifer)

    return points

#This function takes a region and aquiferid number and writes a new JSON file with data for the specified aquifer.
# This function divides the data from a CSV and JSON file combination.
def subdivideaquifers(region,app_workspace,aquiferid):
    aquiferlist = getaquiferlist(app_workspace, region)

    wellfile = region+"/Wells1.json"
    well_file=os.path.join(app_workspace.path,wellfile)
    aquifer = int(aquiferid)

    for i in aquiferlist:
        if i['Id'] == aquifer:
            myaquifer = i
    #Check stuff with i['Contains']
    aquifer_id_number=int(aquifer)
    aquifer_id_numbers=[aquifer_id_number]
    if 'Contains' in myaquifer:
        if len(myaquifer['Contains'])>1:
            aquifer_id_numbers=myaquifer['Contains']
    if myaquifer['Name']!=region:
        with open(well_file, 'r') as f:
            allwells = ''
            wells = f.readlines()
            for i in range(0, len(wells)):
                allwells += wells[i]
        wells_json = json.loads(allwells)
        points = {
            'type': 'FeatureCollection',
            'features': []
        }
        for feature in wells_json['features']:
            feature['properties']['HydroID']=str(feature['properties']['HydroID'])
            if feature['properties']['AquiferID'] == aquifer_id_number or feature['properties']['AquiferID'] in aquifer_id_numbers:
                points['features'].append(feature)
        points['features'].sort(key=lambda x: x['properties']['HydroID'])
        time_csv = []
        mycsv=region+'/Wells_Master.csv'
        the_csv=os.path.join(app_workspace.path,mycsv)
        aquifer_id_number = str(aquifer_id_number)
        with open(the_csv) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['AquiferID'] == aquifer_id_number or int(row['AquiferID']) in aquifer_id_numbers:
                    if row['TsValue_normalized'] != '':
                        timestep = ((str(row['FeatureID']).strip()), (row['TsTime']), (float(row['TsValue'])),
                                    (float(row['TsValue_normalized'])))
                        time_csv.append(timestep)
    else:
        with open(well_file, 'r') as f:
            allwells = ''
            wells = f.readlines()
            for i in range(0, len(wells)):
                allwells += wells[i]
        wells_json = json.loads(allwells)
        points = {
            'type': 'FeatureCollection',
            'features': []
        }
        for feature in wells_json['features']:
            points['features'].append(feature)
        points['features'].sort(key=lambda x: x['properties']['HydroID'])
        print len(points['features'])

        time_csv = []
        mycsv = region+'/Wells_Master.csv'
        the_csv = os.path.join(app_workspace.path, mycsv)
        with open(the_csv) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['TsValue_normalized'] != '':
                    timestep = ((str(row['FeatureID']).strip()), (row['TsTime']), (float(row['TsValue'])),
                                (float(row['TsValue_normalized'])))
                    time_csv.append(timestep)
    time_csv.sort(key=lambda x:x[0])
    number = 0
    aquifermin = 0.0
    max_number = len(points['features'])
    for i in time_csv:
        while number < max_number:
            if i[0] == str(points['features'][number]['properties']['HydroID']):
                if 'TsTime' not in points['features'][number]:
                    points['features'][number]['TsTime'] = []
                    points['features'][number]['TsValue'] = []
                    points['features'][number]['TsValue_norm'] = []

                points['features'][number]['TsTime'].append(i[1])
                points['features'][number]['TsValue'].append(i[2])
                points['features'][number]['TsValue_norm'].append(i[3])
                if i[2] < aquifermin:
                    aquifermin = i[2]
                break
            number += 1
        if number==max_number:
            number=0
            continue




    for i in points['features']:
        if 'LandElev' not in i['properties']:
            i['properties']['LandElev']=-9999
        if 'TsValue' in i:
            array = []
            for j in range(0, len(i['TsTime'])):
                this_time = i['TsTime'][j]
                pos = this_time.find("/")
                pos2 = this_time.find("/", pos + 1)
                month = this_time[0:pos]
                day = this_time[pos + 1:pos2]
                year = this_time[pos2 + 1:pos2 + 5]
                month = int(month)
                year = int(year)
                day = int(day)
                this_time = calendar.timegm(datetime.datetime(year, month, day).timetuple())
                i['TsTime'][j] = this_time
            # The following code sorts the timeseries entries for each well so they are in chronological order
            length = len(i['TsTime'])
            for j in range(0, len(i['TsTime'])):
                array.append((i['TsTime'][j], i['TsValue'][j], i['TsValue_norm'][j]))
            array.sort(key=itemgetter(0))
            i['TsTime'] = []
            i['TsValue'] = []
            i['TsValue_norm'] = []
            #This portion of the sorting code checks to see if the dates are duplicates and does not add them if they are
            oldtime=-9999.5555
            for j in range(0, length):
                if oldtime!=array[j][0]:
                    i['TsTime'].append(array[j][0])
                    i['TsValue'].append(array[j][1])
                    i['TsValue_norm'].append(array[j][2])
                    oldtime=array[j][0]

    points['aquifermin']=aquifermin


    name = myaquifer['Name']

    directory = os.path.join(app_workspace.path, region + '/aquifers')
    if not os.path.exists(directory):
        os.makedirs(directory)
    #Write a json file to the app workspace for the specified aquifer.
    # This file includes all the geographical, time series, and properties data for the aquifer.
    filename = name.replace(' ', '_') + '.json'
    filename=os.path.join(app_workspace.path,region+'/aquifers/'+filename)
    with open(filename, 'w') as outfile:
        json.dump(points, outfile)

    # Download and Set up the DEM for the aquifer
    download_DEM(region,myaquifer)
    return [points,aquifermin]


#This function opens the Aquifers.csv file for the specified region and returns a JSON object listing the aquifers
def gettimelist(region,aquifer):

    list = []
    timelist=[]
    directory=os.path.join(thredds_serverpath,region)
    aquifer=aquifer.replace(" ","_")
    for filename in os.listdir(directory):
        if filename.startswith(aquifer+"."):
            list.append(filename)
    for item in list:
        nc_file = os.path.join(directory, item)
        #os.chmod(nc_file, 0o777)
        h = netCDF4.Dataset(nc_file, 'r+', format="NETCDF4")
        components = item.split('.')
        mytime={
            'Full_Name':item,
            'Aquifer':components[0].replace("_"," "),
            'Start_Date':h.start_date,
            'End_Date':h.end_date,
            'Interval':h.interval,
            'Resolution':h.resolution,
            'Min_Samples':h.min_samples,
            'Min_Ratio':h.min_ratio,
            'Time_Tolerance':h.time_tolerance,
            'Default':h.default,
            'Interpolation':h.interpolation,
            'Units':h.units,
        }
        h.close()

        timelist.append(mytime)
    return timelist

def interp_wizard(app_workspace, aquiferid, region, interpolation_type, start_date, end_date, interval, resolution, make_default, min_samples, min_ratio, time_tolerance, from_wizard, units):
    if from_wizard==True:
        interpolate = 1
    else:
        interpolate=0



    aquiferlist = getaquiferlist(app_workspace, region)

    for i in aquiferlist:
        if i['Id'] == aquiferid:
            myaquifer = i
    name = myaquifer['Name'].replace(' ', '_')
    aquifer=name
    if interpolation_type:
        date_name=aquifer+"."+str(start_date)+"."+str(end_date)+"."+str(interval)+"."+str(int(resolution*100))+"."+str(min_samples)+"."+str(int(min_ratio*100))+"."+str(time_tolerance)+"."+interpolation_type[0]
    else:
        date_name="Nothing will be named this"
    netcdf_directory = os.path.join(thredds_serverpath, region)
    for filename in os.listdir(netcdf_directory):
        #filename = str(filename)
        if filename.startswith(date_name):
            interpolate=0
            if make_default==1:
                nc_file = os.path.join(netcdf_directory, filename)
                #os.chmod(nc_file, 0o777)
                h = netCDF4.Dataset(nc_file, 'r+', format="NETCDF4")
                h.default=1
                h.close()
        elif filename.startswith(name+'.'):
            if make_default==1:
                nc_file = os.path.join(netcdf_directory, filename)
                #os.chmod(nc_file, 0o777)
                h = netCDF4.Dataset(nc_file, 'r+', format="NETCDF4")
                if h.default==1:
                    h.default=0
                h.close()



    start = t.time()

    # Check whether the region has been divided. If not, then divide it
    directory = os.path.join(app_workspace.path, region + '/aquifers')
    if not os.path.exists(directory):
        os.makedirs(directory)

    filename = name + '.json'
    filename = os.path.join(app_workspace.path, region + '/aquifers/' + filename)
    well_file = os.path.join(app_workspace.path, region + '/Wells.json')
    if not os.path.exists(filename):

        for i in range(1, len(aquiferlist) + 1):
            if os.path.exists(well_file):
                divideaquifers(region, app_workspace, i)
            else:
                subdivideaquifers(region, app_workspace, i)
    with open(filename, 'r') as f:
        allwells = ''
        wells = f.readlines()
        for i in range(0, len(wells)):
            allwells += wells[i]
    points = json.loads(allwells)
    print len(points['features'])

    returnmessage=''
    # Execute the following function to interpolate groundwater levels and create a netCDF File and upload it to the server
    if interpolate == 1:

        returnmessage=upload_netcdf(points, name, app_workspace, aquiferid, region, interpolation_type, start_date, end_date,
                      interval, resolution, min_samples, min_ratio, time_tolerance, date_name, make_default, units)

    end = t.time()
    print(end - start)

    return points,returnmessage

# This Ajax controller uploads the NetCDF file to HydroShare
def upload_to_hydroshare(request):

    try:
        return_json = {}
        if request.method == 'POST':
            get_data = request.POST

            name = str(get_data['name'])
            region = str(get_data['region'])
            r_title = str(get_data['r_title'])
            r_type = str(get_data['r_type'])
            r_abstract = str(get_data['r_abstract'])
            r_keywords_raw = str(get_data['r_keywords'])
            r_keywords = r_keywords_raw.split(',')

            auth = HydroShareAuthBasic(username='stevenwe', password='bruno222')
            #hs = get_oauth_hs(request)
            hs = HydroShare(auth=auth)
            directory = os.path.join(thredds_serverpath, region)
            nc_file = os.path.join(directory, name)
            if os.path.exists(nc_file):
                h = netCDF4.Dataset(nc_file, 'r+')
                metadata = '[{"coverage":{"type":"period", "value":{"start":' + str(h.start_date) + ', "end":' + str(h.end_date) + '}}},{"creator":{"name":"stevenwevans2@gmail.com"}}]'
                h.close()

            #upload the file to HydroShare
            if os.path.exists(nc_file):
                resource_id = hs.createResource(r_type, r_title, resource_file=nc_file, resource_filename=nc_file, keywords=r_keywords, abstract=r_abstract)
                return_json['success'] = 'File uploaded successfully!'
                return_json['newResource'] = resource_id
                return_json['hs_domain'] = hs.hostname

    except Exception as e:
        print e
    finally:
        return JsonResponse(return_json)