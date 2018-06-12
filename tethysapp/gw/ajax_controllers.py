from django.http import Http404, HttpResponse, JsonResponse
import os
import json
import netCDF4
from netCDF4 import Dataset
import datetime
import numpy as np
from .app import Gw as app

def displaygeojson(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        geolayer = request.GET.get('geolayer')
        return_obj['geolayer'] = geolayer
        app_workspace = app.get_app_workspace()
        geofile = os.path.join(app_workspace.path, geolayer)
        with open(geofile, 'r') as f:
            allwells = ''
            wells = f.readlines()
            for i in range(0, len(wells)):#len(wells)
                allwells += wells[i]
        return_obj = json.loads(allwells)
    return JsonResponse(return_obj)


def loadjson(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        geolayer = request.GET.get('geolayer')
        return_obj['geolayer'] = geolayer
        app_workspace = app.get_app_workspace()
        geofile = os.path.join(app_workspace.path, geolayer)
        with open(geofile, 'r') as f:
            allwells = ''
            wells = f.readlines()
            for i in range(0, len(wells)):
                allwells += wells[i]
        return_obj = json.loads(allwells)
    return JsonResponse(return_obj)


def savejson(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'POST':
        return_obj['success'] = True
        geolayer = request.POST.get('geolayer')
        name=request.POST.get('name')
	iteration=request.POST.get('iteration')
	return_obj['iteration']=iteration
        return_obj['geolayer'] = geolayer
        return_obj['name']=name
        app_workspace = app.get_app_workspace()
        # filename='interpolationpoints.json'
        # geofile = os.path.join(app_workspace.path, filename)
        # print(geolayer)
        # with open(geofile, 'w') as f:
        #     f.write(geolayer)
        #
        # with open(geofile, "r") as f:
        #     alldata = ''
        #     data = f.readlines()
        #     for i in range(0, len(data)):
        #         alldata += data[i]
        #
        # welldata = json.loads(alldata)
        welldata=json.loads(geolayer)
	i = 0
	lats = []
	lons = []
	while welldata['features'][i]['geometry']['coordinates'][0] == welldata['features'][i + 1]['geometry']['coordinates'][0]:
	    lats.append(welldata['features'][i]['geometry']['coordinates'][1])
	    i += 1
	latlen = i + 1
	lats.append(welldata['features'][i]['geometry']['coordinates'][1])
	lonlen = len(welldata['features']) / latlen
	for i in range(0, len(welldata['features']), latlen):
	    lons.append(welldata['features'][i]['geometry']['coordinates'][0])
	name=name.replace(' ','_')
	filename=name+'.nc'
	nc_file=os.path.join(app_workspace.path, filename)
	iteration=int(iteration)
	if iteration==0:
		h=netCDF4.Dataset(nc_file,'w',format="NETCDF4")
		time = h.createDimension("time", 0)
		lat = h.createDimension("lat", latlen)
		lon = h.createDimension("lon", lonlen)
		latitude=h.createVariable("lat",np.float64,("lat"))
		longitude=h.createVariable("lon",np.float64,("lon"))
		time=h.createVariable("time",np.float64,("time"))
		depth=h.createVariable("depth",np.float64,('time','lat','lon'),fill_value=-9999)
		depth.units="ft"
		depth.grid_mapping="WGS84"
		depth.cell_measures="area: area"
		depth.coordinates="time lat lon"
		latitude.long_name="Latitude"
		latitude.units="degrees_north"
		latitude.axis="Y"
		longitude.long_name="Longitude"
		longitude.units="degrees_east"
		longitude.axis="X"
		time.axis="T"
		time.units='days since 0001-01-01 00:00:00 UTC'
		latitude[:]=lats[:]
		longitude[:]=lons[:]
		#timearray=['2000-01-01T00:00:00.000Z','2001-01-01T00:00:00.000Z','2002-01-01T00:00:00.000Z']
		year=1950
		timearray=[]#[datetime.datetime(2000,1,1).toordinal()-1,datetime.datetime(2001,1,1).toordinal()-1,datetime.datetime(2002,1,1).toordinal()-1]
		for i in range(0,14):
			timearray.append(datetime.datetime(year,1,1).toordinal()-1)
			year+=5
		print(timearray)
		for i in range(0,len(timearray)):
		    time[i]=timearray[i]
		for i in welldata['features']:
		    oldlon=i['geometry']['coordinates'][0]
		    for j in range(0,len(lons)):
			if oldlon==lons[j]:
			    lonindice=j         
		    oldlat=i['geometry']['coordinates'][1]
		    for j in range(0,len(lats)):
			if oldlat==lats[j]:
			    latindice=j  
		    olddepth=i['properties']['timevalue']
		    depth[0,latindice,lonindice]=olddepth
		print(depth[0,1,1])
		h.close()
		os.chmod(nc_file,0o777)
	else:
		h=netCDF4.Dataset(nc_file,'r+',format="NETCDF4")
		for i in welldata['features']:
		    oldlon=i['geometry']['coordinates'][0]
		    for j in range(0,len(lons)):
			if oldlon==lons[j]:
			    lonindice=j         
		    oldlat=i['geometry']['coordinates'][1]
		    for j in range(0,len(lats)):
			if oldlat==lats[j]:
			    latindice=j  
		    olddepth=i['properties']['timevalue']
		    h.variables['depth'][iteration,latindice,lonindice]=olddepth
		h.close()
		if iteration==13:
			serverpath="/home/student/tds/apache-tomcat-8.5.30/content/thredds/public/testdata/groundwater"
			destination= os.path.join(serverpath, filename)
			os.rename(nc_file, destination)
        print("success")
    return JsonResponse(return_obj)
