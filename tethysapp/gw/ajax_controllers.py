from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
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
import scipy
import elevation
from rasterio.transform import from_bounds, from_origin
from rasterio.warp import reproject, Resampling
from scipy.spatial.distance import pdist, squareform, cdist
from scipy.optimize import least_squares
import rasterio
from django.contrib.auth.decorators import login_required,user_passes_test
import math
import pygslib

porosity=0.3
#global variables
thredds_serverpath='/home/tethys/Thredds/groundwater/'
#thredds_serverpath = "/home/student/tds/apache-tomcat-8.5.30/content/thredds/public/testdata/groundwater/"

#Check if the user is superuser or staff. Only the superuser or staff have the permission to add and manage watersheds.
def user_permission_test(user):
    return user.is_superuser or user.is_staff

#The explode and bbox functions are used to get the bounding box of a geoJSON object
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
    return round(np.min(x)-.05,1), round(np.min(y)-.05,1), round(np.max(x)+.05,1), round(np.max(y)+.05,1)

# The following functions are used to automatically fit a variogram to the input data
def great_circle_distance(lon1, lat1, lon2, lat2):
    """Calculate the great circle distance between one or multiple pairs of
    points given in spherical coordinates. Spherical coordinates are expected
    in degrees. Angle definition follows standard longitude/latitude definition.
    This uses the arctan version of the great-circle distance function
    (en.wikipedia.org/wiki/Great-circle_distance) for increased
    numerical stability.
    Parameters
    ----------
    lon1: float scalar or numpy array
        Longitude coordinate(s) of the first element(s) of the point
        pair(s), given in degrees.
    lat1: float scalar or numpy array
        Latitude coordinate(s) of the first element(s) of the point
        pair(s), given in degrees.
    lon2: float scalar or numpy array
        Longitude coordinate(s) of the second element(s) of the point
        pair(s), given in degrees.
    lat2: float scalar or numpy array
        Latitude coordinate(s) of the second element(s) of the point
        pair(s), given in degrees.
    Calculation of distances follows numpy elementwise semantics, so if
    an array of length N is passed, all input parameters need to be
    arrays of length N or scalars.
    Returns
    -------
    distance: float scalar or numpy array
        The great circle distance(s) (in degrees) between the
        given pair(s) of points.
    """
    # Convert to radians:
    lat1 = np.array(lat1)*np.pi/180.0
    lat2 = np.array(lat2)*np.pi/180.0
    dlon = (lon1-lon2)*np.pi/180.0

    # Evaluate trigonometric functions that need to be evaluated more
    # than once:
    c1 = np.cos(lat1)
    s1 = np.sin(lat1)
    c2 = np.cos(lat2)
    s2 = np.sin(lat2)
    cd = np.cos(dlon)

    # This uses the arctan version of the great-circle distance function
    # from en.wikipedia.org/wiki/Great-circle_distance for increased
    # numerical stability.
    # Formula can be obtained from [2] combining eqns. (14)-(16)
    # for spherical geometry (f=0).

    return 180.0 / np.pi * np.arctan2(np.sqrt((c2*np.sin(dlon))**2 + (c1*s2-s1*c2*cd)**2), s1*s2+c1*c2*cd)

def _variogram_residuals(params, x, y, variogram_function, weight):
    """Function used in variogram model estimation. Returns residuals between
    calculated variogram and actual data (lags/semivariance).
    Called by _calculate_variogram_model.
    Parameters
    ----------
    params: list or 1D array
        parameters for calculating the model variogram
    x: ndarray
        lags (distances) at which to evaluate the model variogram
    y: ndarray
        experimental semivariances at the specified lags
    variogram_function: callable
        the actual funtion that evaluates the model variogram
    weight: bool
        flag for implementing the crude weighting routine, used in order to
        fit smaller lags better
    Returns
    -------
    resid: 1d array
        residuals, dimension same as y
    """

    # this crude weighting routine can be used to better fit the model
    # variogram to the experimental variogram at smaller lags...
    # the weights are calculated from a logistic function, so weights at small
    # lags are ~1 and weights at the longest lags are ~0;
    # the center of the logistic weighting is hard-coded to be at 70% of the
    # distance from the shortest lag to the largest lag
    if weight:
        drange = np.amax(x) - np.amin(x)
        k = 2.1972 / (0.1 * drange)
        x0 = 0.7 * drange + np.amin(x)
        weights = 1. / (1. + np.exp(-k * (x0 - x)))
        weights /= np.sum(weights)
        resid = (variogram_function(params, x) - y) * weights
    else:
        resid = variogram_function(params, x) - y

    return resid

def spherical_variogram_model(m, d):
    """Spherical model, m is [psill, range, nugget]"""
    psill = float(m[0])
    range_ = float(m[1])
    nugget = float(m[2])
    return np.piecewise(d, [d <= range_, d > range_],
                        [lambda x: psill * ((3.*x)/(2.*range_) - (x**3.)/(2.*range_**3.)) + nugget, psill + nugget])

'''The generate_variogram function automatically fits a variogram to the data
    Inputs:
        X: a 2d array of geographical coordinates of sample points (longitude, latitude) of length n
        y: an array of length n containing the values at sample points, ordered the same as X
        variogram_function: a function for the variogram model (Spherical, Gaussian)
    Returns:
        variogram_model_parameters: a list of 1. the sill, 2. the range, 3. the nugget'''
def generate_variogram(X,y,variogram_function):
    # This calculates the pairwise geographic distance and variance between pairs of points
    x1, x2 = np.meshgrid(X[:, 0], X[:, 0], sparse=True)
    y1, y2 = np.meshgrid(X[:, 1], X[:, 1], sparse=True)
    z1, z2 = np.meshgrid(y, y, sparse=True)
    d = great_circle_distance(x1, y1, x2, y2)
    g = 0.5 * (z1 - z2) ** 2.
    indices = np.indices(d.shape)
    d = d[(indices[0, :, :] > indices[1, :, :])]
    g = g[(indices[0, :, :] > indices[1, :, :])]

    # Now we will sort the d and g into bins
    nlags = 10
    weight = False
    dmax = np.amin(d) + (np.amax(d) - np.amin(d)) / 2.0
    dmax = np.amax(d)

    dmin = np.amin(d)
    dd = (dmax - dmin) / nlags
    bins = [dmin + n * dd for n in range(nlags)]
    dmax += 0.001
    bins.append(dmax)

    lags = np.zeros(nlags)
    semivariance = np.zeros(nlags)

    for n in range(nlags):
        # This 'if... else...' statement ensures that there are data
        # in the bin so that numpy can actually find the mean. If we
        # don't test this first, then Python kicks out an annoying warning
        # message when there is an empty bin and we try to calculate the mean.
        if d[(d >= bins[n]) & (d < bins[n + 1])].size > 0:
            lags[n] = np.mean(d[(d >= bins[n]) & (d < bins[n + 1])])
            semivariance[n] = np.mean(g[(d >= bins[n]) & (d < bins[n + 1])])
        else:
            lags[n] = np.nan
            semivariance[n] = np.nan
    lags = lags[~np.isnan(semivariance)]
    semivariance = semivariance[~np.isnan(semivariance)]

    # First entry is the sill, then the range, then the nugget
    x0 = [np.amax(semivariance) - np.amin(semivariance), lags[2], 0]
    bnds = ([0., lags[2], 0.], [10. * np.amax(semivariance), np.amax(lags), 1])

    # use 'soft' L1-norm minimization in order to buffer against
    # potential outliers (weird/skewed points)
    res = least_squares(_variogram_residuals, x0, bounds=bnds, loss='soft_l1',
                        args=(lags, semivariance, variogram_function, weight))
    variogram_model_parameters = res.x
    print variogram_model_parameters
    return variogram_model_parameters

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
    heights=[]
    aquifermin=points['aquifermin']
    iterations=int((end_date-start_date)/interval+1)
    start_time=calendar.timegm(datetime.datetime(start_date, 1, 1).timetuple())
    end_time=calendar.timegm(datetime.datetime(end_date, 1, 1).timetuple())
    sixmonths=False
    if interval==.5:
        sixmonths=True
        iterations+=1
    #old method of interpolation that uses all data
    if min_samples==1 and min_ratio==0:
        for v in range(0, iterations):
            if sixmonths==False:
                targetyear = int(start_date + interval * v)
                target_time = calendar.timegm(datetime.datetime(targetyear, 1, 1).timetuple())
            else:
                monthyear=start_date+interval*v
                doubleyear=monthyear*2
                if doubleyear%2==0:
                    targetyear=int(monthyear)
                    target_time = calendar.timegm(datetime.datetime(targetyear, 1, 1).timetuple())
                else:
                    targetyear=int(monthyear-.5)
                    target_time = calendar.timegm(datetime.datetime(targetyear, 7, 1).timetuple())
            fiveyears = 157766400 * 2
            myspots = []
            mylons = []
            mylats = []
            myvalues = []
            myelevations = []
            myheights=[]
            slope = 0
            number = 0
            timevalue = 0

            for i in points['features']:
                if 'TsTime' in i and 'LandElev' in i['properties']:
                    if i['properties']['LandElev']==-9999:
                        i['properties']['LandElev']=0
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
            if sixmonths==False:
                targetyear = int(start_date + interval * v)
                target_time = calendar.timegm(datetime.datetime(targetyear, 1, 1).timetuple())
            else:
                monthyear=start_date+interval*v
                doubleyear=monthyear*2
                if doubleyear%2==0:
                    targetyear=int(monthyear)
                    target_time = calendar.timegm(datetime.datetime(targetyear, 1, 1).timetuple())
                else:
                    targetyear=int(monthyear-.5)
                    target_time = calendar.timegm(datetime.datetime(targetyear, 7, 1).timetuple())
            fiveyears = (157766400/5)*time_tolerance
            oneyear=(157766400/5)
            myspots = []
            mylons = []
            mylats = []
            myvalues = []
            myelevations = []
            myheights=[]
            timevalue = 0


            for i in points['features']:
                if 'TsTime' in i and 'LandElev' in i['properties'] and ('Outlier' not in i['properties'] or i['properties']['Outlier']==False):
                    if i['properties']['LandElev']==-9999:
                        i['properties']['LandElev']=0
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
                                y_data = np.array(i['TsValue'])
                                x_data = np.array(i['TsTime'])
                                timevalue=scipy.interpolate.pchip_interpolate(x_data,y_data,target_time)
                                # timedelta = target_time - i['TsTime'][tlocation - 1]
                                # slope = (i['TsValue'][tlocation] - i['TsValue'][tlocation - 1]) / (
                                #         i['TsTime'][tlocation] - i['TsTime'][tlocation - 1])
                                # timevalue = i['TsValue'][tlocation - 1] + slope * timedelta


                            else:
                                timevalue = 9999

                        # for the case where the target time is before
                        if tlocation == -888:
                            if listlength > min_samples:
                                consistent = False
                                if listlength > 10:
                                    consistent = True
                                    for step in range(0, 6):
                                        timechange = i['TsTime'][step+1] - i['TsTime'][step]
                                        if timechange != 0:
                                            slope = (i['TsValue'][step+1] - i['TsValue'][step]) / timechange
                                        else:
                                            consistent = False
                                            break
                                        consistent_slope=5.0/oneyear #5 ft/year
                                        if abs(slope)>consistent_slope:
                                            consistent=False
                                            break
                                        if (i['TsTime'][step+1] - i['TsTime'][step]) > (oneyear*2):
                                            consistent = False
                                            break
                                if (i['TsTime'][0] - target_time) < fiveyears/2 or (consistent and (i['TsTime'][0]-target_time)<(fiveyears)):
                                    y_data = np.array(i['TsValue'])
                                    x_data = np.array(i['TsTime'])
                                    ymax = np.amax(y_data)
                                    ymin = np.amin(y_data)
                                    yrange = ymax - ymin
                                    toplim = y_data[0] + yrange / 2
                                    botlim = y_data[0] - yrange / 2
                                    #sp1 = UnivariateSpline(x_data, y_data, k=1)
                                    if listlength<2:
                                        slope=0.0
                                    elif (i['TsTime'][1]-i['TsTime'][0])!=0:
                                        slope=float((i['TsValue'][1]-i['TsValue'][0])/(i['TsTime'][1]-i['TsTime'][0]))
                                    else:
                                        slope=0.0
                                    slope_val=i['TsValue'][0]+slope*(target_time-i['TsValue'][0])

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
                                        timechange=i['TsTime'][step] - i['TsTime'][step-1]
                                        if timechange!=0:
                                            slope = (i['TsValue'][step] - i['TsValue'][step-1]) / timechange
                                        else:
                                            consistent=False
                                            break
                                        consistent_slope = 5.0 / oneyear  # 5 ft/year
                                        if abs(slope) > consistent_slope:
                                            consistent = False
                                            break
                                        if (i['TsTime'][step]-i['TsTime'][step-1])>(oneyear*2):
                                            consistent=False
                                            break
                                if (target_time - i['TsTime'][listlength - 1])<(oneyear/2):
                                    timevalue=i['TsValue'][listlength-1]
                                elif (target_time - i['TsTime'][listlength - 1]) < fiveyears/2 or (consistent and (target_time - i['TsTime'][listlength - 1]) < fiveyears):
                                    y_data = np.array(i['TsValue'])
                                    x_data = np.array(i['TsTime'])
                                    ymax = np.amax(y_data)
                                    ymin = np.amin(y_data)
                                    yrange = ymax - ymin
                                    toplim = y_data[listlength-1] + yrange / 2
                                    botlim = y_data[listlength-1] - yrange / 2
                                    if listlength<2:
                                        slope=0.0
                                    elif (i['TsTime'][listlength-1]-i['TsTime'][listlength-2])!=0:
                                        slope=float((i['TsValue'][listlength-1]-i['TsValue'][listlength-2])/(i['TsTime'][listlength-1]-i['TsTime'][listlength-2]))
                                    else:
                                        slope=0.0
                                    slope_val=i['TsValue'][listlength-1]+slope*(target_time-i['TsValue'][listlength-1])

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
                        if timevalue != 9999:
                            the_elevation = i['properties']['LandElev'] + timevalue
                            myelevations.append(the_elevation)
                            myvalues.append(timevalue)
                            myspots.append(i['geometry']['coordinates'])
                            mylons.append(i['geometry']['coordinates'][0])
                            mylats.append(i['geometry']['coordinates'][1])
                            if 'LandElev' in i['properties']:
                                myheights.append(i['properties']['LandElev'])
            values.append(myvalues)
            elevations.append(myelevations)
            spots.append(myspots)
            lons.append(mylons)
            lats.append(mylats)
            heights.append(myheights)
            print len(myvalues)
        lons = np.array(lons)
        lats = np.array(lats)
        values = np.array(values)
        elevations = np.array(elevations)
        heights=np.array(heights)

    #Now we prepare the data for the generate_variogram function
    coordinates = []
    for i in range(0, iterations):
        coordinate = np.array((lons[i], lats[i])).T
        coordinates.append(coordinate)
    coordinates = np.array(coordinates)
    X = coordinates[0]
    y = values[0]
    variogram_function=spherical_variogram_model
    variogram_model_parameters=generate_variogram(X,y,variogram_function)

    aquiferlist = getaquiferlist(app_workspace, region)
    for i in aquiferlist:
        if i['Id'] == int(aquifer_number):
            myaquifer = i
    myaquifercaps = myaquifer['CapsName']
    fieldname = myaquifer['FieldName']

    AquiferShape = {
        'type': 'FeatureCollection',
        'features': []
    }

    MajorAquifers = os.path.join(app_workspace.path, region + '/MajorAquifers.json')
    if os.path.exists(MajorAquifers):
        with open(MajorAquifers, 'r') as f:
            major = json.load(f)
        for i in major['features']:
            if fieldname in i['properties']:
                if i['properties'][fieldname] == myaquifercaps:
                    AquiferShape['features'].append(i)

    MinorAquifers = os.path.join(app_workspace.path, region + '/MinorAquifers.json')
    if os.path.exists(MinorAquifers):
        with open(MinorAquifers, 'r') as f:
            minor = json.load(f)
        for i in minor['features']:
            if fieldname in i['properties']:
                if i['properties'][fieldname] == myaquifercaps:
                    AquiferShape['features'].append(i)

    State_Boundary = os.path.join(app_workspace.path, region + '/' + region + '_State_Boundary.json')
    with open(State_Boundary, 'r') as f:
        state = json.load(f)

    if myaquifercaps == region or myaquifercaps == 'NONE':
        AquiferShape = state

    lonmin, latmin, lonmax, latmax = bbox(AquiferShape['features'][0])
    latgrid = np.mgrid[latmin:latmax:resolution]
    longrid = np.mgrid[lonmin:lonmax:resolution]
    latrange = len(latgrid)
    lonrange = len(longrid)
    nx = (lonmax - lonmin) / resolution
    ny = (latmax - latmin) / resolution
    searchradius = 3
    ndmax = len(elevations[0])
    ndmin = ndmax - 2
    noct = 0
    nugget = 0
    sill = variogram_model_parameters[0]
    vrange = variogram_model_parameters[1]
    print latrange, lonrange

    bounds = (lonmin, latmin, lonmax, latmax)
    west, south, east, north = bounds
    # Reproject DEM to 0.01 degree resolution using rasterio
    dem_path=os.path.join(app_workspace.path, region+"/DEM/"+name.replace(" ","_")+"_DEM.tif")
    dem_raster = rasterio.open(dem_path)
    src_crs = dem_raster.crs
    src_shape = src_height, src_width = dem_raster.shape
    src_transform = from_bounds(west, south, east, north, src_width, src_height)
    source = dem_raster.read(1)
    dst_crs = {'init': 'EPSG:4326'}
    dst_transform = from_origin(lonmin, latmax, resolution, resolution)
    dem_array = np.zeros((latrange, lonrange))
    dem_array[:] = np.nan
    reproject(source,
              dem_array,
              src_transform=src_transform,
              src_crs=src_crs,
              dst_transform=dst_transform,
              dst_crs=dst_crs,
              resampling=Resampling.bilinear)
    dem_array = np.array(dem_array)
    dem_array = np.flipud(dem_array)
    dem = np.reshape(dem_array.T, ((lonrange) * latrange))
    # dem=dem*3.28084 #use this to convert from meters to feet
    dem_grid = np.reshape(dem, (lonrange, latrange))

    outx = np.repeat(longrid, latrange)
    outy = np.tile(latgrid, lonrange)
    depth_grids = []
    elev_grids = []

    for i in range(0, iterations):
        params = {
            'x': lons[i],
            'y': lats[i],
            'vr': values[i],
            'nx': nx,
            'ny': ny,
            'nz': 1,
            'xmn': lonmin,
            'ymn': latmin,
            'zmn': 0,
            'xsiz': resolution,
            'ysiz': resolution,
            'zsiz': 1,
            'nxdis': 1,
            'nydis': 1,
            'nzdis': 1,
            'outx': outx,
            'outy': outy,
            'radius': searchradius,
            'radius1': searchradius,
            'radius2': searchradius,
            'ndmax': ndmax,
            'ndmin': ndmin,
            'noct': noct,
            'ktype': 1,
            'idbg': 0,
            'c0': nugget,
            'it': 1,
            'cc': sill,
            'aa': vrange,
            'aa1': vrange,
            'aa2': vrange
        }
        if interpolation_type=="Kriging with External Drift":
            params['vr']=elevations[i]
            params['ve']=heights[i]
            params['outextve']=dem
            params['ktype']=3
        estimate = pygslib.gslib.kt3d(params)
        if interpolation_type=="IDW":
            array=estimate[0]['outidpower']
        else:
            array = estimate[0]['outest']
        depth_grid = np.reshape(array, (lonrange, latrange))
        if interpolation_type == "Kriging with External Drift":
            elev_grid=depth_grid
            depth_grid = elev_grid - dem_grid
        else:
            elev_grid = dem_grid + depth_grid
        depth_grids.append(depth_grid)
        elev_grids.append(elev_grid)
        print i
    depth_grids = np.array(depth_grids)
    elev_grids = np.array(elev_grids)

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
    h.interpolation=interpolation_type

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

    volume = h.createVariable("volume", np.float64, ('time', 'lon', 'lat'), fill_value=-9999)
    volume.long_name = "Change in aquifer storage volume since " + str(start_date)
    volume.units = "Acre-ft"
    volume.grid_mapping = "WGS84"
    volume.cell_measures = "area: area"
    volume.coordinates = "time lat lon"

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
    t=0
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
            if sixmonths==False:
                year=int(year)
                timearray.append(datetime.datetime(year, 1, 1).toordinal() - 1)
            else:
                monthyear=start_date+interval*i
                doubleyear=monthyear*2
                if doubleyear%2==0:
                    monthyear=int(monthyear)
                    timearray.append(datetime.datetime(monthyear, 1, 1).toordinal() - 1)
                else:
                    monthyear=int(monthyear-.5)
                    timearray.append(datetime.datetime(monthyear, 7, 1).toordinal() - 1)
            year += interval

        else: # for IDW, Kriging, and Kriging with External Drift
            if sixmonths==False:
                year=int(year)
                timearray.append(datetime.datetime(year, 1, 1).toordinal() - 1)
            else:
                monthyear=start_date+interval*i
                doubleyear=monthyear*2
                if doubleyear%2==0:
                    monthyear=int(monthyear)
                    timearray.append(datetime.datetime(monthyear, 1, 1).toordinal() - 1)
                else:
                    monthyear=int(monthyear-.5)
                    timearray.append(datetime.datetime(monthyear, 7, 1).toordinal() - 1)
            year += interval
            time[t] = timearray[i]
            for y in range(0, latrange):
                depth[t, :, y] = depth_grids[i, :, y]
                elevation[t, :, y] = elev_grids[i, :, y]
                if t == 0:
                    drawdown[t, :, y] = 0
                else:
                    drawdown[t, :, y] = depth[i, :, y] - depth[0, :, y]
                mylatmin = math.radians(latitude[y] - resolution / 2)
                mylatmax = math.radians(latitude[y] + resolution / 2)
                area = 6371000 * math.radians(resolution) * 6371000 * abs(
                    (math.sin(mylatmin) - math.sin(mylatmax)))  # 3959 is the radius of the earth in miles, 6,371,000 is radius in meters
                # area = area * 640  # convert from square miles to acres by multiplying by 640
                volume[t, :, y] = drawdown[i, :, y] * porosity * area
            t+=1

    h.close()

    # Calls a shellscript that uses NCO to clip the NetCDF File created above to aquifer boundaries
    myshell = 'aquifersubset.sh'
    directory = temp_dir
    shellscript = os.path.join(app_workspace.path, myshell)
    subprocess.call([shellscript, filename, directory, interpolation_type, region, str(resolution), app_workspace.path])




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

    directory = os.path.join(app_workspace.path, region + '/DEM')
    if not os.path.exists(directory):
        os.makedirs(directory)
    # Download and Set up the DEM for the aquifer
    minorfile = os.path.join(app_workspace.path, region + '/MinorAquifers.json')
    majorfile = os.path.join(app_workspace.path, region + '/MajorAquifers.json')
    aquiferShape = {
        'type': 'FeatureCollection',
        'features': []
    }
    fieldname = myaquifer['FieldName']

    if os.path.exists(minorfile):
        with open(minorfile, 'r') as f:
            minor = json.load(f)
        for i in minor['features']:
            if fieldname in i['properties']:
                if i['properties'][fieldname] == myaquifer['CapsName']:
                    aquiferShape['features'].append(i)

    if os.path.exists(majorfile):
        with open(majorfile, 'r') as f:
            major = json.load(f)
        for i in major['features']:
            if fieldname in i['properties']:
                if i['properties'][fieldname] == myaquifer['CapsName']:
                    aquiferShape['features'].append(i)
    print aquiferShape
    lonmin, latmin, lonmax, latmax = bbox(aquiferShape['features'][0])
    bounds = (lonmin - .1, latmin - .1, lonmax + .1, latmax + .1)
    dem_path = name.replace(' ','_') + '_DEM.tif'
    output = os.path.join(directory, dem_path)
    elevation.clip(bounds=bounds, output=output, product='SRTM3')
    print "This step works. 90 m DEM downloaded for ",name

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
            if 'Contains' in row:
                if row['Contains'] !="":
                    myaquifer['Contains']=row['Contains'].split('.')
                    myaquifer['Contains']=[int(i) for i in myaquifer['Contains']]
            aquiferlist.append(myaquifer)
    return aquiferlist


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
        }
        h.close()

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

    # Execute the following function to interpolate groundwater levels and create a netCDF File and upload it to the server
    if interpolate == 1:
        upload_netcdf(points, name, app_workspace, aquiferid, region, interpolation_type, start_date, end_date,
                      interval, resolution, min_samples, min_ratio, time_tolerance, date_name, make_default)

    end = t.time()
    print(end - start)

    return points


