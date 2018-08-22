from __future__ import division
from pykrige.ok import OrdinaryKriging
from django.http import Http404, HttpResponse, JsonResponse
import os
import json
import netCDF4
import datetime
import numpy as np
from .app import Gw as app
import csv
import time as t
import calendar
from operator import itemgetter
import subprocess
import urllib
import pandas as pd
from shapely.geometry import Point
from shapely.geometry import shape
import tempfile, shutil
from scipy.interpolate import UnivariateSpline

#global variables
thredds_serverpath='/home/tethys/Thredds/groundwater/'
#thredds_serverpath = "/home/student/tds/apache-tomcat-8.5.30/content/thredds/public/testdata/groundwater/"

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
        with open(geofile, 'r') as f:
            allwells = ''
            wells = f.readlines()
            for i in range(0, len(wells)):#len(wells)
                allwells += wells[i]
        return_obj = json.loads(allwells)
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
        interpolation_type=request.GET.get('interpolation_type')

        timelist=gettimelist(region,aquifer,interpolation_type)
        return_obj['timelist']=timelist
    return JsonResponse(return_obj)


def deletenetcdf(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        region=request.GET.get('region')
        aquifer=request.GET.get('aquifer')
        interpolation_type=request.GET.get('interpolation_type')
        name=request.GET.get('name')

        directory = os.path.join(thredds_serverpath, region + '/' + interpolation_type)
        file=os.path.join(directory,name)
        os.remove(file)

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
        interpolation_type=request.GET.get('interpolation_type')
        name=request.GET.get('name')

        aquifer=aquifer.replace(" ","_")
        directory = os.path.join(thredds_serverpath, region + '/' + interpolation_type)
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
                # if filename==name and ".Default.nc" not in filename:
                #     newname = filename[:-3] + ".Default.nc"
                #     src = os.path.join(directory, filename)
                #     dst = os.path.join(directory, newname)
                #     os.rename(src, dst)
                # elif ".Default" in filename and filename!=name:
                #     newname = filename.replace(".Default", "")
                #     src = os.path.join(directory, filename)
                #     dst = os.path.join(directory, newname)
                #     os.rename(src, dst)


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
        return_obj['id'] = aquiferid
        return_obj['interpolation_type']=interpolation_type
        app_workspace = app.get_app_workspace()
        aquiferid=int(aquiferid)

        make_default = int(make_default)
        from_wizard=int(from_wizard)
        if start_date and end_date and interval and resolution:
            start_date=int(start_date)
            end_date=int(end_date)
            interval=int(interval)
            resolution=float(resolution)
            length=int(length)
            min_samples=int(min_samples)
            min_ratio=float(min_ratio)
            time_tolerance=int(time_tolerance)
        else:
            start_date=1950
            end_date=2015
            interval=5
            resolution=.05
            make_default=0
            min_samples=25
            time_tolerance=5
            if interpolation_type=="IDW":
                min_ratio=.75
            else:
                min_ratio=1

        if aquiferid==9999:
            for i in range(1,length):
                aquiferid=i
                points=interp_wizard(app_workspace, aquiferid, region, interpolation_type, start_date, end_date, interval, resolution, make_default, min_samples, min_ratio, time_tolerance, from_wizard)
        else:
            points=interp_wizard(app_workspace, aquiferid, region, interpolation_type, start_date, end_date, interval, resolution, make_default, min_samples, min_ratio, time_tolerance,  from_wizard)

        return_obj['data']=points
    return JsonResponse(return_obj)

# This function takes a set of well points from a specified aquifer in a region and interpolates the data through time and space
# and writes a NetCDF file for the interpolated data, clips the netCDF file to the boundaries of the specified aquifer,
# and then uploads this file to the server.
def upload_netcdf(points,name,app_workspace,aquifer_number,region,interpolation_type,start_date,end_date,interval,resolution, min_samples, min_ratio, time_tolerance, date_name, make_default):
    # Execute the following code to interpolate groundwater levels and create a netCDF File and upload it to the server

    spots = []
    lons = []
    lats = []
    values = []
    elevations = []
    aquifermin=points['aquifermin']
    iterations=int((end_date-start_date)/interval+1)
    start_time=calendar.timegm(datetime.datetime(start_date, 1, 1).timetuple())
    end_time=calendar.timegm(datetime.datetime(end_date, 1, 1).timetuple())
    # min_ratio=1.0
    # if interpolation_type=="IDW":
    #     min_ratio=0.75
    # if min_samples<30:
    #     min_ratio=0.0


    #old method of interpolation that uses all data
    if min_samples==1 and min_ratio==0:
        for v in range(0, iterations):
            targetyear = start_date + interval * v
            target_time = calendar.timegm(datetime.datetime(targetyear, 1, 1).timetuple())
            fiveyears = 157766400 * 2
            myspots = []
            mylons = []
            mylats = []
            myvalues = []
            myelevations = []
            slope = 0
            number = 0
            timevalue = 0

            for i in points['features']:
                if 'TsTime' in i and 'LandElev' in i['properties']:
                    tlocation = 0
                    stop_location = 0
                    listlength = len(i['TsTime'])
                    for j in range(0, listlength):
                        if i['TsTime'][j] >= target_time and stop_location == 0:
                            tlocation = j
                            stop_location = 1

                    # target time is larger than max date
                    if tlocation == 0 and stop_location == 0:
                        tlocation = -999

                    # target time is smaller than min date
                    if tlocation == 0 and stop_location == 1:
                        tlocation = -888

                    # for the case where the target time is in the middle
                    if tlocation > 0:
                        timedelta = target_time - i['TsTime'][tlocation - 1]
                        slope = (i['TsValue'][tlocation] - i['TsValue'][tlocation - 1]) / (
                                i['TsTime'][tlocation] - i['TsTime'][tlocation - 1])
                        timevalue = i['TsValue'][tlocation - 1] + slope * timedelta

                    # for the case where the target time is before
                    if tlocation == -888:
                        timedelta = i['TsTime'][0] - target_time
                        if abs(timedelta) > fiveyears:
                            timevalue = 9999
                        elif listlength > 1:
                            if (i['TsTime'][1] - i['TsTime'][0]) != 0:
                                slope = (i['TsValue'][1] - i['TsValue'][0]) / (i['TsTime'][1] - i['TsTime'][0])
                                if abs(slope) > (1.0 / (24 * 60 * 60)):
                                    timevalue = i['TsValue'][0]
                                else:
                                    timevalue = i['TsValue'][0] - slope * timedelta
                                if (timevalue > 0 and timevalue != 9999) or timevalue < aquifermin:
                                    timevalue = i['TsValue'][0]
                            else:
                                timevalue = i['TsValue'][0]
                        else:
                            timevalue = i['TsValue'][0]

                    # for the case where the target time is after
                    if tlocation == -999:
                        timedelta = target_time - i['TsTime'][listlength - 1]
                        if abs(timedelta) > fiveyears:

                            timevalue = 9999
                        elif listlength > 1:
                            if (i['TsTime'][listlength - 1] - i['TsTime'][listlength - 2]) != 0:
                                slope = (i['TsValue'][listlength - 1] - i['TsValue'][listlength - 2]) / (
                                        i['TsTime'][listlength - 1] - i['TsTime'][listlength - 2])
                                if abs(slope) > (1.0 / (24 * 60 * 60)):
                                    timevalue = i['TsValue'][listlength - 1]
                                else:
                                    timevalue = i['TsValue'][listlength - 1] + slope * timedelta
                                if (timevalue > 0 and timevalue != 9999) or timevalue < aquifermin:
                                    timevalue = i['TsValue'][listlength - 1]
                            else:
                                timevalue = i['TsValue'][listlength - 1]
                        else:
                            timevalue = i['TsValue'][listlength - 1]
                    if timevalue != 9999:
                        the_elevation = i['properties']['LandElev'] + timevalue
                        myelevations.append(the_elevation)
                        myvalues.append(timevalue)
                        myspots.append(i['geometry']['coordinates'])
                        mylons.append(i['geometry']['coordinates'][0])
                        mylats.append(i['geometry']['coordinates'][1])
            values.append(myvalues)
            elevations.append(myelevations)
            spots.append(myspots)
            lons.append(mylons)
            lats.append(mylats)
            print len(myvalues)
        lons = np.array(lons)
        lats = np.array(lats)
        values = np.array(values)
        elevations = np.array(elevations)

    #New method for interpolation that uses least squares fit and filters data
    else:
        for v in range(0, iterations):
            targetyear = start_date + interval * v
            target_time = calendar.timegm(datetime.datetime(targetyear, 1, 1).timetuple())
            fiveyears = (157766400/5)*time_tolerance
            myspots = []
            mylons = []
            mylats = []
            myvalues = []
            myelevations = []
            timevalue = 0

            for i in points['features']:
                if 'TsTime' in i and 'LandElev' in i['properties']:
                    listlength = len(i['TsTime'])
                    length_time = end_time - start_time
                    mylength_time = min(i['TsTime'][listlength - 1] - i['TsTime'][0], i['TsTime'][listlength - 1] - start_time, end_time-i['TsTime'][0])

                    ratio = float(mylength_time / length_time)
                    if ratio > min_ratio:
                        tlocation = 0
                        stop_location = 0
                        for j in range(0, listlength):
                            if i['TsTime'][j] >= target_time and stop_location == 0:
                                tlocation = j
                                stop_location = 1

                        # target time is larger than max date
                        if tlocation == 0 and stop_location == 0:
                            tlocation = -999

                        # target time is smaller than min date
                        if tlocation == 0 and stop_location == 1:
                            tlocation = -888

                        # for the case where the target time is in the middle
                        if tlocation > 0:
                            if listlength > min_samples and listlength > 1:

                                timedelta = target_time - i['TsTime'][tlocation - 1]
                                slope = (i['TsValue'][tlocation] - i['TsValue'][tlocation - 1]) / (
                                        i['TsTime'][tlocation] - i['TsTime'][tlocation - 1])
                                timevalue = i['TsValue'][tlocation - 1] + slope * timedelta


                            else:
                                timevalue = 9999

                        # for the case where the target time is before
                        if tlocation == -888:
                            if listlength > min_samples:
                                consistent = False
                                if listlength > 10:
                                    consistent = True
                                    for step in range(0, 6):
                                        if (i['TsTime'][step+1] - i['TsTime'][step]) > (fiveyears / 2.5):
                                            consistent = False
                                            break
                                if (i['TsTime'][0] - target_time) < fiveyears or (consistent and (i['TsTime'][0]-target_time)<(fiveyears*3)):
                                    y_data = np.array(i['TsValue'])
                                    x_data = np.array(i['TsTime'])
                                    ymax = np.amax(y_data)
                                    ymin = np.amin(y_data)
                                    yrange = ymax - ymin
                                    toplim = y_data[0] + yrange / 2
                                    botlim = y_data[0] - yrange / 2
                                    #sp1 = UnivariateSpline(x_data, y_data, k=1)
                                    if listlength<2:
                                        slope=0
                                    elif (i['TsTime'][1]-i['TsTime'][0])!=0:
                                        slope=(i['TsValue'][1]-i['TsValue'][0])/(i['TsTime'][1]-i['TsTime'][0])
                                    else:
                                        slope=0
                                    slope_val=i['TsValue'][0]+slope*(timevalue-i['TsValue'][0])

                                    average = y_data[0]
                                    timevalue = (slope_val + 4 * average) / 5
                                    if timevalue > toplim:
                                        timevalue = toplim
                                    if timevalue < botlim:
                                        timevalue = botlim
                                else:
                                    timevalue = 9999

                            else:
                                timevalue = 9999
                            # for the case where the target time is after
                        if tlocation == -999:
                            if listlength > min_samples:
                                consistent=False
                                if listlength>10:
                                    consistent=True
                                    for step in range(listlength-1,listlength-6,-1):
                                        if (i['TsTime'][step]-i['TsTime'][step-1])>(fiveyears/2.5):
                                            consistent=False
                                            break
                                if (target_time - i['TsTime'][listlength - 1])<(fiveyears/5):
                                    timevalue=i['TsValue'][listlength-1]
                                elif (target_time - i['TsTime'][listlength - 1]) < fiveyears or (consistent and (target_time - i['TsTime'][listlength - 1]) < (fiveyears*3)):
                                    y_data = np.array(i['TsValue'])
                                    x_data = np.array(i['TsTime'])
                                    ymax = np.amax(y_data)
                                    ymin = np.amin(y_data)
                                    yrange = ymax - ymin
                                    toplim = y_data[listlength-1] + yrange / 2
                                    botlim = y_data[listlength-1] - yrange / 2
                                    if listlength<2:
                                        slope=0
                                    elif (i['TsTime'][listlength-1]-i['TsTime'][listlength-2])!=0:
                                        slope=(i['TsValue'][listlength-1]-i['TsValue'][listlength-2])/(i['TsTime'][listlength-1]-i['TsTime'][listlength-2])
                                    else:
                                        slope=0
                                    slope_val=i['TsValue'][listlength-1]+slope*(timevalue-i['TsValue'][listlength-1])

                                    average = y_data[listlength-1]
                                    timevalue = (slope_val + 4 * average) / 5
                                    if timevalue > toplim:
                                        timevalue = toplim
                                    if timevalue < botlim:
                                        timevalue = botlim
                                else:
                                    timevalue = 9999
                            else:
                                timevalue = 9999
                        if i['properties']['HydroID']==403900112022701:
                            print timevalue, targetyear
                        if timevalue != 9999:
                            the_elevation = i['properties']['LandElev'] + timevalue
                            myelevations.append(the_elevation)
                            myvalues.append(timevalue)
                            myspots.append(i['geometry']['coordinates'])
                            mylons.append(i['geometry']['coordinates'][0])
                            mylats.append(i['geometry']['coordinates'][1])
            values.append(myvalues)
            elevations.append(myelevations)
            spots.append(myspots)
            lons.append(mylons)
            lats.append(mylats)
            print len(myvalues)
        lons = np.array(lons)
        lats = np.array(lats)
        values = np.array(values)
        elevations = np.array(elevations)

    lonmin = 360.0
    latmin = 90.0
    lonmax = -360.0
    latmax = -90.0
    for i in points['features']:
        if i['geometry']['coordinates'][0] < lonmin:
            lonmin = i['geometry']['coordinates'][0]
        if i['geometry']['coordinates'][0] > lonmax:
            lonmax = i['geometry']['coordinates'][0]
        if i['geometry']['coordinates'][1] < latmin:
            latmin = i['geometry']['coordinates'][1]
        if i['geometry']['coordinates'][1] > latmax:
            latmax = i['geometry']['coordinates'][1]
    lonmin = round(lonmin - .05, 1)
    latmin = round(latmin - .05, 1)
    lonmax = round(lonmax + .05, 1)
    latmax = round(latmax + .05, 1)

    latgrid = np.mgrid[latmin:latmax:resolution]
    longrid = np.mgrid[lonmin:lonmax:resolution]

    latrange = (latmax - latmin) / resolution + 1
    lonrange = (lonmax - lonmin) / resolution + 1
    latrange = int(latrange)
    lonrange = int(lonrange)

    def iwd(x, y, v, grid, power):
        for i in xrange(grid.shape[0]):
            for j in xrange(grid.shape[1]):
                distance = np.sqrt((x - ((i * resolution) + lonmin)) ** 2 + (y - ((j * resolution) + latmin)) ** 2)
                if (distance ** power).min() == 0:
                    grid[i, j] = v[(distance ** power).argmin()]
                else:
                    total = np.sum(1 / (distance ** power))
                    grid[i, j] = np.sum(v / (distance ** power) / total)
        return grid

    # GMS Method of IDW interpolation
    def gms(x, y, v, grid, power):
        for i in xrange(grid.shape[0]):
            for j in xrange(grid.shape[1]):
                distance = np.sqrt((x - ((i * resolution) + lonmin)) ** 2 + (y - ((j * resolution) + latmin)) ** 2)
                if (distance ** power).min() == 0:
                    grid[i, j] = v[(distance ** power).argmin()]
                else:
                    R = np.amax(distance)
                    w = ((R - distance) / (R * distance)) ** 2
                    wtotal = np.sum(w)
                    grid[i, j] = np.sum(v * w / wtotal)
        return grid

    grid = np.zeros((lonrange, latrange), dtype='float32')

    aquiferlist=getaquiferlist(app_workspace,region)
    for i in aquiferlist:
        if i['Id'] == int(aquifer_number):
            myaquifer = i
    myaquifercaps=myaquifer['CapsName']
    fieldname = myaquifer['FieldName']

    AquiferShape = {
        'type': 'FeatureCollection',
        'features': []
    }

    MajorAquifers = os.path.join(app_workspace.path, region + '/MajorAquifers.json')
    if os.path.exists(MajorAquifers):
        with open(MajorAquifers, 'r') as f:
            allwells = ''
            wells = f.readlines()
            for i in range(0, len(wells)):
                allwells += wells[i]
        major = json.loads(allwells)
        for i in major['features']:
            if fieldname in i['properties']:
                if i['properties'][fieldname] == myaquifercaps:
                    AquiferShape['features'].append(i)

    MinorAquifers = os.path.join(app_workspace.path, region + '/MinorAquifers.json')
    if os.path.exists(MinorAquifers):
        with open(MinorAquifers, 'r') as f:
            allwells = ''
            wells = f.readlines()
            for i in range(0, len(wells)):
                allwells += wells[i]
        minor = json.loads(allwells)
        for i in minor['features']:
            if fieldname in i['properties']:
                if i['properties'][fieldname] == myaquifercaps:
                    AquiferShape['features'].append(i)

    State_Boundary = os.path.join(app_workspace.path, region + '/'+region+'_State_Boundary.json')
    with open(State_Boundary, 'r') as f:
        allwells = ''
        wells = f.readlines()
        for i in range(0, len(wells)):
            allwells += wells[i]
    state = json.loads(allwells)

    if myaquifercaps == region or myaquifercaps == 'NONE':
        AquiferShape['features'].append(state['features'][0])

    temp_dir=tempfile.mkdtemp()


    myshapefile = os.path.join(temp_dir, "shapefile.json")
    with open(myshapefile, 'w') as outfile:
        json.dump(AquiferShape, outfile)
    #end if statement

    latlen = len(latgrid)
    lonlen = len(longrid)

    # name=name.replace(' ','_')
    # name=name+'.nc'
    # filename = name
    filename=date_name+".nc"
    nc_file = os.path.join(temp_dir, filename)
    h = netCDF4.Dataset(nc_file, 'w', format="NETCDF4")

    #Global Attributes
    h.start_date=start_date
    h.end_date=end_date
    h.interval=interval
    h.resolution=resolution
    h.min_samples=min_samples
    h.min_ratio=min_ratio
    h.time_tolerance=time_tolerance
    h.default=make_default

    time = h.createDimension("time", 0)
    lat = h.createDimension("lat", latlen)
    lon = h.createDimension("lon", lonlen)
    latitude = h.createVariable("lat", np.float64, ("lat"))
    longitude = h.createVariable("lon", np.float64, ("lon"))
    time = h.createVariable("time", np.float64, ("time"), fill_value="NaN")
    depth = h.createVariable("depth", np.float64, ('time', 'lon', 'lat'), fill_value=-9999)
    elevation = h.createVariable("elevation", np.float64, ('time', 'lon', 'lat'), fill_value=-9999)
    elevation.long_name = "Elevation of Water Table"
    elevation.units = "ft"
    elevation.grid_mapping = "WFS84"
    elevation.cell_measures = "area: area"
    elevation.coordinates = "time lat lon"

    depth.long_name = "Depth to Water Table"
    depth.units = "ft"
    depth.grid_mapping = "WGS84"
    depth.cell_measures = "area: area"
    depth.coordinates = "time lat lon"

    drawdown = h.createVariable("drawdown", np.float64, ('time', 'lon', 'lat'), fill_value=-9999)
    drawdown.long_name = "Well Drawdown Since "+str(start_date)
    drawdown.units = "ft"
    drawdown.grid_mapping = "WGS84"
    drawdown.cell_measures = "area: area"
    drawdown.coordinates = "time lat lon"

    latitude.long_name = "Latitude"
    latitude.units = "degrees_north"
    latitude.axis = "Y"
    longitude.long_name = "Longitude"
    longitude.units = "degrees_east"
    longitude.axis = "X"
    time.axis = "T"
    time.units = 'days since 0001-01-01 00:00:00 UTC'
    latitude[:] = latgrid[:]
    longitude[:] = longrid[:]
    year = start_date
    timearray = []  # [datetime.datetime(2000,1,1).toordinal()-1,datetime.datetime(2002,1,1).toordinal()-1]
    for i in range(0, iterations):
        a = lons[i]
        b = lats[i]
        c = values[i]
        d = elevations[i]
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)
        d = np.array(d)
        krigeable=True
        interpolatable=True
        if len(c)<3 or len(d) <3:
            krigeable=False
            if len(c)<1 or len(d)<1:
                interpolatable=False
        if interpolatable==False:
            timearray.append(datetime.datetime(year, 1, 1).toordinal() - 1)
            year += interval
            time[i] = timearray[i]
            for x in range(0, len(longrid)):
                for y in range(0, len(latgrid)):
                    depth[i, x, y] = -9999
                    elevation[i,x,y]=-9999
                    drawdown[i,x,y]=-9999
        elif interpolation_type == 'IDW' or krigeable==False:
            grids = gms(a, b, c, grid, 2)
            timearray.append(datetime.datetime(year, 1, 1).toordinal() - 1)
            year += interval
            time[i] = timearray[i]
            for x in range(0, len(longrid)):
                for y in range(0, len(latgrid)):
                    depth[i, x, y] = grids[x, y]
                    if i == 0:
                        drawdown[i, x, y] = 0
                    else:
                        for f in range(0, i):
                            if depth[f, x, y] != -9999:
                                drawdown[i, x, y] = depth[i, x, y] - depth[f, x, y]
                                break
                            else:
                                drawdown[i, x, y] = 0

            grid2 = gms(a, b, d, grid, 2)
            for x in range(0, len(longrid)):
                for y in range(0, len(latgrid)):
                    elevation[i, x, y] = grid2[x, y]


        elif interpolation_type == 'Kriging':
            OK = OrdinaryKriging(a, b, c, variogram_model='gaussian', coordinates_type='geographic', verbose=True, enable_plotting=False)
            EK = OrdinaryKriging(a, b, d, variogram_model='gaussian', coordinates_type='geographic')
            if len(a) > 500:
                elev, error = EK.execute('grid', longrid, latgrid, backend='C', n_closest_points=25)
                krig, ss = OK.execute('grid', longrid, latgrid, backend='C', n_closest_points=25)
            else:
                elev, error = EK.execute('grid', longrid, latgrid)
                krig, ss = OK.execute('grid', longrid, latgrid)
            timearray.append(datetime.datetime(year, 1, 1).toordinal() - 1)
            year += interval
            time[i] = timearray[i]
            for x in range(0, len(longrid)):
                for y in range(0, len(latgrid)):
                    depth[i, x, y] = krig[y, x]
                    elevation[i, x, y] = elev[y, x]
                    if i == 0:
                        drawdown[i, x, y] = 0
                    else:
                        for f in range(0,i):
                            if depth[f,x,y]!=-9999:
                                drawdown[i, x, y] = depth[i, x, y] - depth[f, x, y]
                                break
                            else:
                                drawdown[i,x,y]=0

    h.close()

    # Calls a shellscript that uses NCO to clip the NetCDF File created above to aquifer boundaries
    myshell = 'aquifersubset.sh'
    directory = temp_dir
    print temp_dir
    shellscript = os.path.join(app_workspace.path, myshell)
    subprocess.call([shellscript, filename, directory, interpolation_type, region, str(resolution), app_workspace.path])


#The pullnwis function pulls data from the web for a specified region and writes the data to a JSON file named Wells.JSON in the appropriate folder.
def pullnwis(state, app_workspace,region):
    link = "https://waterservices.usgs.gov/nwis/gwlevels/?format=json&stateCd=ut&startDT=1800-01-01&endDT=2018-7-31&parameterCd=72019&siteStatus=all"
    f = urllib.urlopen(link)
    myfile = f.read()
    myfile = json.loads(myfile)
    print len(myfile['value']['timeSeries'])

    aquifermin = 0.0
    points = {
        'type': 'FeatureCollection',
        'features': []
    }
    for i in range(0, len(myfile['value']['timeSeries'])):
        times = []
        values = []
        for j in myfile['value']['timeSeries'][i]['values'][0]['value']:
            if float(j['value']) != 999999.0 and float(j['value']) != -999999.0:
                time = j['dateTime']
                value = float(j['value']) * -1
                times.append(time)
                values.append(value)
                if value < aquifermin:
                    aquifermin = value
        id_name = myfile['value']['timeSeries'][i]['name']
        pos = id_name.find(":")
        pos2 = id_name.find(":", pos + 1)
        id_name = id_name[pos + 1:pos2]
        latitude = float(
            myfile['value']['timeSeries'][i]['sourceInfo']['geoLocation']['geogLocation']['latitude'])
        longitude = float(
            myfile['value']['timeSeries'][i]['sourceInfo']['geoLocation']['geogLocation']['longitude'])
        if len(times) > 0:
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [longitude, latitude]
                },
                'TsTime': times,
                'TsValue': values,
                'properties': {
                    'HydroID': int(id_name)
                }
            }
        else:
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [longitude, latitude]
                },
                'properties': {
                    'HydroID': int(id_name)
                }
            }
        points['features'].append(feature)

    url = "https://waterservices.usgs.gov/nwis/site/?format=rdb&stateCd=ut&siteType=GW&siteStatus=all"
    f = pd.read_csv(url, skiprows=29, sep='\t')
    length = len(f['site_no'])
    i = 1
    for p in points['features']:
        newstart = i
        while i < length:
            if p['properties']['HydroID'] == int(f['site_no'][i]):
                empty = pd.isnull(f['alt_va'][i])
                if empty == False:
                    p['properties']['LandElev'] = float(f['alt_va'][i])
                break
            i += 1
        if i == length:
            i = newstart
            continue

    count = 0
    for i in points['features']:
        if 'TsValue' in i:
            array = []
            for j in range(0, len(i['TsTime'])):
                this_time = i['TsTime'][j]
                pos = this_time.find("-")
                pos2 = this_time.find("-", pos + 1)
                pos3 = this_time.find("T")
                year = this_time[0:pos]
                month = this_time[pos + 1:pos2]
                day = this_time[pos2 + 1:pos3]
                month = int(month)
                year = int(year)
                day = int(day)
                this_time = calendar.timegm(datetime.datetime(year, month, day).timetuple())
                i['TsTime'][j] = this_time
            # The following code sorts the timeseries entries for each well so they are in chronological order
            length = len(i['TsTime'])
            for j in range(0, len(i['TsTime'])):
                array.append((i['TsTime'][j], i['TsValue'][j]))
            array.sort(key=itemgetter(0))
            i['TsTime'] = []
            i['TsValue'] = []
            for j in range(0, length):
                i['TsTime'].append(array[j][0])
                i['TsValue'].append(array[j][1])
            count += 1

    points['aquifermin']=aquifermin
    mywellsfile = os.path.join(app_workspace.path, region + "/Wells.json")
    with open(mywellsfile, 'w') as outfile:
        json.dump(points, outfile)

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

    return points

#This function takes a region and aquiferid number and writes a new JSON file with data for the specified aquifer.
# This function divides the data from a CSV and JSON file combination.
def subdivideaquifers(region,app_workspace,aquiferid):
    aquiferlist = getaquiferlist(app_workspace, region)

    geofile = region+"/Wells1.json"
    nc_file=os.path.join(app_workspace.path,geofile)
    aquifer = int(aquiferid)

    for i in aquiferlist:
        if i['Id'] == int(aquifer):
            myaquifer = i

    if myaquifer['Name']!=region:
        with open(nc_file, 'r') as f:
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
            if feature['properties']['AquiferID'] == aquifer:
                points['features'].append(feature)
        points['features'].sort(key=lambda x: x['properties']['HydroID'])
        time_csv = []
        aquifer = str(aquifer)
        mycsv=region+'/csv/Wells_Master.csv'
        the_csv=os.path.join(app_workspace.path,mycsv)
        with open(the_csv) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['AquiferID'] == aquifer:
                    if row['TsValue_normalized'] != '':
                        timestep = (int(row['FeatureID']), (row['TsTime']), (float(row['TsValue'])),
                                    (float(row['TsValue_normalized'])))
                        time_csv.append(timestep)
        aquifer=int(aquifer)
    else:
        with open(nc_file, 'r') as f:
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
        mycsv = region+'/csv/Wells_Master.csv'
        the_csv = os.path.join(app_workspace.path, mycsv)
        with open(the_csv) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['TsValue_normalized'] != '':
                    timestep = (int(row['FeatureID']), (row['TsTime']), (float(row['TsValue'])),
                                (float(row['TsValue_normalized'])))
                    time_csv.append(timestep)
    time_csv.sort(key=lambda x:x[0])

    number = 0
    aquifermin = 0.0
    for i in time_csv:
        while number < len(points['features']):
            if i[0] == points['features'][number]['properties']['HydroID']:
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



    for i in points['features']:
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
            for j in range(0, length):
                i['TsTime'].append(array[j][0])
                i['TsValue'].append(array[j][1])
                i['TsValue_norm'].append(array[j][2])

    points['aquifermin']=aquifermin

    print myaquifer
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

    print len(time_csv)
    return [points,aquifermin]

#This function opens the Aquifers.csv file for the specified region and returns a JSON object listing the aquifers
def getaquiferlist(app_workspace,region):
    aquiferlist = []
    aquifercsv = os.path.join(app_workspace.path, region + '/' + region + '_Aquifers.csv')
    with open(aquifercsv) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            myaquifer = {
                'Id': int(row['ID']),
                'Name': row['Name'],
                'Type': row['Type'],
                'CapsName': row['CapsName'],
                'FieldName':row['NameField']
            }
            aquiferlist.append(myaquifer)
    return aquiferlist

#This function opens the Aquifers.csv file for the specified region and returns a JSON object listing the aquifers
def gettimelist(region,aquifer,interpolation_type):

    list = []
    timelist=[]
    directory=os.path.join(thredds_serverpath,region+'/'+interpolation_type)
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
            'Default':h.default
        }
        h.close()
        # components=item.split('.')
        # if len(components)>4:
        #     mytime={
        #         'Full_Name':item,
        #         'Aquifer':components[0].replace("_"," "),
        #         'Start_Date':int(components[1]),
        #         'End_Date':int(components[2]),
        #         'Interval':int(components[3]),
        #         'Resolution':float(components[4]),
        #         'Min_Samples':int(components[5]),
        #         'Min_Ratio':float(components[6]),
        #         'Time_Tolerance':float(components[7])
        #     }
        #     if len(components)>9 or ".Default" in item:
        #         mytime['Default']=True
        # else:
        #     mytime={
        #         'Full_Name':item,
        #         'Aquifer':components[0].replace("_"," "),
        #         'Start_Date':1985,
        #         'End_Date':2015,
        #         'Interval':5,
        #         'Resolution': "NA",
        #         'Min_Samples': "NA",
        #         'Min_Ratio': "NA",
        #         'Time_Tolerance': "NA"
        #     }
        #     if ".Default" in item:
        #         mytime['Default']=True
        timelist.append(mytime)
    return timelist

def interp_wizard(app_workspace, aquiferid, region, interpolation_type, start_date, end_date, interval, resolution, make_default, min_samples, min_ratio, time_tolerance, from_wizard):
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
    date_name=aquifer+"."+str(start_date)+"."+str(end_date)+"."+str(interval)+"."+str(int(resolution*100))+"."+str(min_samples)+"."+str(int(min_ratio*100))+"."+str(time_tolerance)

    netcdf_directory = os.path.join(thredds_serverpath, region + '/' + interpolation_type)
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
    #         if make_default==1:
    #             newname=filename[:-3]+".Default.nc"
    #             src = os.path.join(netcdf_directory, filename)
    #             dst = os.path.join(netcdf_directory, newname)
    #             os.rename(src, dst)
    #     elif make_default==1:
    #         if ".Default" in filename:
    #             newname=filename.replace(".Default","")
    #             src=os.path.join(netcdf_directory,filename)
    #             dst=os.path.join(netcdf_directory,newname)
    #             os.rename(src,dst)
    #
    # if make_default==1:
    #     date_name=date_name+".Default"


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

    # Execute the following function to interpolate groundwater levels and create a netCDF File and upload it to the server
    if interpolate == 1:
        upload_netcdf(points, name, app_workspace, aquiferid, region, interpolation_type, start_date, end_date,
                      interval, resolution, min_samples, min_ratio, time_tolerance, date_name, make_default)

    end = t.time()
    print(end - start)

    return points


