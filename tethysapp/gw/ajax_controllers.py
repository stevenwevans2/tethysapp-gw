from __future__ import division
from django.http import Http404, HttpResponse, JsonResponse
import os
import json
import netCDF4
from netCDF4 import Dataset
import datetime
import numpy as np
from .app import Gw as app
import csv
import time as t
import calendar
from operator import itemgetter
import subprocess

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


def loaddata(request):
	return_obj = {
		'success': False
	}

	# Check if its an ajax post request
	if request.is_ajax() and request.method == 'GET':
		return_obj['success'] = True
		aquiferid = request.GET.get('id')
		min_num = request.GET.get('min_num')
		name = request.GET.get('name')
		return_obj['iteration'] = min_num
		return_obj['id'] = aquiferid
		return_obj['name'] = name
		app_workspace = app.get_app_workspace()


		name = name.replace(' ', '_')
		interpolate = 1
		timesteps = 14
		if min_num == 0:
			interpolate = 0
			timesteps = 1
		serverpath = "/home/student/tds/apache-tomcat-8.5.30/content/thredds/public/testdata/groundwater"
		name = name + ".nc"
		netcdfpath = os.path.join(serverpath, name)
		if os.path.exists(netcdfpath):
			interpolate = 0
			timesteps = 1
		return_obj['interpolate'] = interpolate

		start = t.time()
		geofile = "Wells1.json"
		nc_file=os.path.join(app_workspace.path,geofile)
		aquifer = int(aquiferid)

		if aquifer<32:
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
			print len(points['features'])

			time_csv = []
			aquifer = str(aquifer)
			mycsv='csv/Wells_Master.csv'
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
			mycsv = 'csv/Wells_Master.csv'
			the_csv = os.path.join(app_workspace.path, mycsv)
			with open(the_csv) as csvfile:
				reader = csv.DictReader(csvfile)
				for row in reader:
					if row['TsValue_normalized'] != '':
						timestep = (int(row['FeatureID']), (row['TsTime']), (float(row['TsValue'])),
									(float(row['TsValue_normalized'])))
						time_csv.append(timestep)

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
		print points['features'][0]

		count = 0
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
				if count == 0:
					print array
				count += 1
		print(points['features'][0])

		print len(time_csv)

		#Execute the following code to interpolate groundwater levels and create a netCDF File and upload it to the server
		if interpolate==1:
			spots = []
			lons = []
			lats = []
			values = []

			for v in range(0, 14):
				targetyear = 1950 + 5 * v
				target_time = calendar.timegm(datetime.datetime(targetyear, 1, 1).timetuple())
				fiveyears = 157766400 * 2
				myspots = []
				mylons = []
				mylats = []
				myvalues = []
				slope = 0
				number = 0
				timevalue = 0
				for i in points['features']:
					if 'TsTime' in i:
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
							myvalues.append(timevalue)
							myspots.append(i['geometry']['coordinates'])
							mylons.append(i['geometry']['coordinates'][0])
							mylats.append(i['geometry']['coordinates'][1])
				values.append(myvalues)
				spots.append(myspots)
				lons.append(mylons)
				lats.append(mylats)
			lons = np.array(lons)
			lats = np.array(lats)
			values = np.array(values)

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

			latgrid = np.mgrid[latmin:latmax:.05]
			longrid = np.mgrid[lonmin:lonmax:.05]

			latrange = (latmax - latmin) / .05 + 1
			lonrange = (lonmax - lonmin) / .05 + 1
			latrange = int(latrange)
			lonrange = int(lonrange)

			def iwd(x, y, v, grid, power):
				for i in xrange(grid.shape[0]):
					for j in xrange(grid.shape[1]):
						distance = np.sqrt((x - ((i * .05) + lonmin)) ** 2 + (y - ((j * .05) + latmin)) ** 2)
						if (distance ** power).min() == 0:
							grid[i, j] = v[(distance ** power).argmin()]
						else:
							total = np.sum(1 / (distance ** power))
							grid[i, j] = np.sum(v / (distance ** power) / total)
				return grid

			grid = np.zeros((lonrange, latrange), dtype='float32')  # float32 gives us a lot precision
			mastergrid = []
			grids = []

			#aquifer = int(aquifer)
			aquifers = ['HUECO_BOLSON', 'WEST TEXAS BOLSONS', 'PECOS VALLEY', 'SEYMOUR', 'BRAZOS RIVER ALLUVIUM',
						'BLAINE', 'BLOSSOM', 'BONE SPRING-VICTORIO PEAK', 'CAPITAN REEF COMPLEX', 'CARRIZO', 'EDWARDS',
						'EDWARDS-TRINITY (HIGH PLAINS)', 'EDWARDS-TRINITY', 'ELLENBURGER-SAN SABA', 'GULF_COAST',
						'HICKORY', 'IGNEOUS', 'MARATHON', 'MARBLE FALLS', 'NACATOCH', 'OGALLALA', 'NONE', 'RITA BLANCA',
						'QUEEN CITY', 'RUSTLER', 'DOCKUM', 'SPARTA', 'TRINITY', 'WOODBINE', 'LIPAN', 'YEGUA JACKSON',
						'Texas']
			region = aquifers[aquifer - 1]

			MajorAquifers=os.path.join(app_workspace.path,'MajorAquifers.json')
			with open(MajorAquifers, 'r') as f:
				allwells = ''
				wells = f.readlines()
				for i in range(0, len(wells)):
					allwells += wells[i]
			major = json.loads(allwells)

			MinorAquifers = os.path.join(app_workspace.path, 'MinorAquifers.json')
			with open(MinorAquifers, 'r') as f:
				allwells = ''
				wells = f.readlines()
				for i in range(0, len(wells)):
					allwells += wells[i]
			minor = json.loads(allwells)

			Texas_State_Boundary=os.path.join(app_workspace.path,'Texas_State_Boundary.json')
			with open(Texas_State_Boundary, 'r') as f:
				allwells = ''
				wells = f.readlines()
				for i in range(0, len(wells)):
					allwells += wells[i]
			texas = json.loads(allwells)

			AquiferShape = {
				'type': 'FeatureCollection',
				'features': []
			}
			for i in major['features']:
				if i['properties']['AQ_NAME'] == region:
					AquiferShape['features'].append(i)

			for i in minor['features']:
				if i['properties']['AQU_NAME'] == region:
					AquiferShape['features'].append(i)
			if region == 'Texas':
				AquiferShape['features'].append(texas['features'][0])

			myshapefile=os.path.join(app_workspace.path,"shapefile.json")
			with open(myshapefile, 'w') as outfile:
				json.dump(AquiferShape, outfile)



			latlen = len(latgrid)
			lonlen = len(longrid)

			filename=name
			nc_file = os.path.join(app_workspace.path, filename)
			h = netCDF4.Dataset(nc_file, 'w', format="NETCDF4")

			time = h.createDimension("time", 0)
			lat = h.createDimension("lat", latlen)
			lon = h.createDimension("lon", lonlen)
			latitude = h.createVariable("lat", np.float64, ("lat"))
			longitude = h.createVariable("lon", np.float64, ("lon"))
			time = h.createVariable("time", np.float64, ("time"), fill_value="NaN")
			depth = h.createVariable("depth", np.float64, ('time', 'lon', 'lat'), fill_value=-9999)
			depth.units = "ft"
			depth.grid_mapping = "WGS84"
			depth.cell_measures = "area: area"
			depth.coordinates = "time lat lon"
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
			year = 1950
			timearray = []  # [datetime.datetime(2000,1,1).toordinal()-1,datetime.datetime(2002,1,1).toordinal()-1]
			for i in range(0, 14):
				a = lons[i]
				b = lats[i]
				c = values[i]
				a = np.array(a)
				b = np.array(b)
				c = np.array(c)
				grids = iwd(a, b, c, grid, 2)
				timearray.append(datetime.datetime(year, 1, 1).toordinal() - 1)
				year += 5
				time[i] = timearray[i]
				for x in range(0, len(longrid)):
					for y in range(0, len(latgrid)):
						depth[i, x, y] = grids[x, y]
					# depth[i,x,y]=f([longrid[x],latgrid[y]],power=2.0,n_neighbors=len(values))
			h.close()

			#os.system("./aquifersubset.sh %s" % (filename))
			myshell='aquifersubset.sh'
			directory=app_workspace.path
			shellscript=os.path.join(app_workspace.path,myshell)
			subprocess.call([shellscript, filename, directory])
			# serverpath = "/home/student/tds/apache-tomcat-8.5.30/content/thredds/public/testdata/groundwater"
			# destination = os.path.join(serverpath, filename)
			# os.rename(nc_file, destination)

		end = t.time()
		print(end - start)

		return_obj['data']=points
	return JsonResponse(return_obj)