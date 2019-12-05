from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.shortcuts import redirect, reverse
from django.contrib import messages
import netCDF4
import numpy as np
import time as t
from operator import itemgetter
from shapely.geometry import Point
from shapely.geometry import shape
from hs_restclient import HydroShare, HydroShareAuthBasic
from .uploadnetcdf import *
from .model import *

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
        region=request.GET.get('region')

        Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
        session = Session()

        majoraquifers = session.query(Aquifers.AquiferName,Aquifers.AquiferShapeJSON).filter(Aquifers.RegionName == region.replace("_"," "), Aquifers.AquiferType=="Major")
        major=[]
        for aquifer in majoraquifers:
            mymajor=aquifer.AquiferShapeJSON
            mymajor['features'][0]['properties']['Name']=aquifer.AquiferName
            major.append(mymajor)
        return_obj['major'] = major
        minoraquifers=session.query(Aquifers.AquiferName,Aquifers.AquiferShapeJSON).filter(Aquifers.RegionName == region.replace("_"," "), Aquifers.AquiferType=="Minor")
        minor=[]
        if minoraquifers:
            for aquifer in minoraquifers:
                myminor = aquifer.AquiferShapeJSON
                myminor['features'][0]['properties']['Name'] = aquifer.AquiferName
                minor.append(myminor)
            return_obj['minor']=minor
        state=session.query(Regions.RegionJSON).filter(Regions.RegionName == region.replace("_"," "))
        for entry in state:
            return_obj['state']=entry.RegionJSON
        session.close()

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

        Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
        session = Session()
        aquiferlist = session.query(Aquifers.AquiferShapeJSON,Aquifers.AquiferName).filter(Aquifers.RegionName == region.replace("_", " "),Aquifers.AquiferID==aquifer_number)
        for aquifer in aquiferlist:
            return_obj['data']=aquifer.AquiferShapeJSON
            return_obj['aquifer'] = aquifer.AquiferName
        session.close()

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

        Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
        session = Session()
        aquifersession = session.query(Aquifers.AquiferID, Aquifers.AquiferName, Aquifers.AquiferType).filter(Aquifers.RegionName == region.replace("_", " "))
        aquiferlist=[]
        for aquifer in aquifersession:
            myaquifer={
                'Id': aquifer.AquiferID,
                'Name': aquifer.AquiferName,
                'Type': aquifer.AquiferType,
            }
            aquiferlist.append(myaquifer)

        session.close()
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

def deleteregion(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        region=request.GET.get('region')
        try:
            Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
            session = Session()
            session.query(Aquifers).filter(Aquifers.RegionName == region.replace('_'," ")).delete()

            session.query(Regions).filter(Regions.RegionFileName == region).delete()

            session.commit()
            session.close()
            # directory = os.path.join(thredds_serverpath, region)
            # if os.path.exists(directory):
            #     shutil.rmtree(directory)
            app_workspace = app.get_app_workspace()
            directory = os.path.join(app_workspace.path, region)
            if os.path.exists(directory):
                shutil.rmtree(directory)
            success=True
        except Exception as e:
            print(e)
            success=False
        url = ''
        if success:
            messages.info(request, 'Successfully removed region')
            url = reverse('gw:region_map')
        else:
            messages.error(request, 'Failed to remove region')
            url = reverse('gw:removeregion')
        return_obj['url']=url
    return JsonResponse(return_obj)

def finish_addregion(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        region=request.GET.get('region')
        AquiferID=request.GET.get('AquiferID')
        DisplayName=request.GET.get('DisplayName')
        Aquifer_Name=request.GET.get('Aquifer_Name')
        porosity=request.GET.get('porosity')
        HydroID=request.GET.get('HydroID')
        AqID=request.GET.get('AqID')
        Elev=request.GET.get('Elev')
        Type=request.GET.get('Type')
        Depth=request.GET.get('Depth')
        come_from=request.GET.get("come_from")
        units=request.GET.get("units")
        minor_AquiferID=request.GET.get('minor_AquiferID')
        minor_DisplayName=request.GET.get('minor_DisplayName')
        minor_Aquifer_Name=request.GET.get('minor_Aquifer_Name')
        minor_porosity=request.GET.get('minor_porosity')
        toggle_region=request.GET.get("toggle_region")
        wlat=request.GET.get('wlat')
        wlon=request.GET.get('wlon')
        print(minor_Aquifer_Name)
        app_workspace=app.get_app_workspace()
        directory = os.path.join(app_workspace.path, region)
        print(AquiferID)
        print(directory)
        aqs=[]
        for filename in os.listdir(directory):
            if filename.startswith('MinorAquifers.json'):
                minorfile = os.path.join(directory, 'MinorAquifers.json')
                with open(minorfile) as f:
                    minor_json = json.load(f)
                for a in minor_json['features']:
                    aq = [a['properties'][minor_AquiferID], a['properties'][minor_DisplayName], a['properties'][minor_Aquifer_Name]]
                    if porosity!='Unused':
                        aq.append(a['properties'][minor_porosity])
                    aqs.append(aq)
                    a['properties']['AquiferID']=a['properties'].pop(minor_AquiferID)
                    a['properties']['DisplayName']=a['properties'].pop(minor_DisplayName)
                    a['properties']['Aquifer_Name']=a['properties'].pop(minor_Aquifer_Name)
                    if minor_porosity!='Unused':
                        a['properties']['Storage_Coefficient']=a['properties'].pop(minor_porosity)
                with open(minorfile,'w') as f:
                    json.dump(minor_json,f)
        majorfile = os.path.join(directory, 'MajorAquifers.json')
        with open(majorfile) as f:
            major_json = json.load(f)
        for a in major_json['features']:
            aq = [a['properties'][AquiferID], a['properties'][DisplayName], a['properties'][Aquifer_Name]]
            if porosity != 'Unused':
                aq.append(a['properties'][porosity])
            aqs.append(aq)
            a['properties']['AquiferID'] = a['properties'].pop(AquiferID)
            a['properties']['DisplayName'] = a['properties'].pop(DisplayName)
            a['properties']['Aquifer_Name'] = a['properties'].pop(Aquifer_Name)
            if porosity != 'Unused':
                a['properties']['Storage_Coefficient'] = a['properties'].pop(porosity)

        with open(majorfile, 'w') as f:
            json.dump(major_json, f)

        if come_from=="upload":
            #This section is for updating and saving the well properties
            wellfile = os.path.join(directory, 'Wells1.json')
            if os.path.exists(wellfile):
                with open(wellfile) as f:
                    well_json = json.load(f)
                for w in well_json['features']:
                    w['properties']['HydroID'] = w['properties'].pop(HydroID)
                    w['properties']['AquiferID'] = w['properties'].pop(AqID)
                    if Elev != "Unused":
                        w['properties']['LandElev'] = w['properties'].pop(Elev)
                    if Type != "Unused":
                        w['properties']['FType'] = w['properties'].pop(Type)
                    if Depth != "Unused":
                        w['properties']['WellDepth'] = w['properties'].pop(Depth)

            else:
                wellfile=os.path.join(directory, 'Wells1.csv')
                well_json = {
                    'type': 'FeatureCollection',
                    'features': []
                }
                with open(wellfile) as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        w={
                            'type':'Feature',
                            'properties':dict(),
                            'geometry':dict()
                        }
                        w['properties']['HydroID'] = row[HydroID]
                        w['properties']['AquiferID'] = int(row[AqID])
                        if Elev != "Unused":
                            w['properties']['LandElev'] = row[Elev]
                        if Type != "Unused":
                            w['properties']['FType'] = row[Type]
                        if Depth != "Unused":
                            w['properties']['WellDepth'] = row[Depth]
                        w['geometry']['type']="Point"
                        w['geometry']['coordinates']=[row[wlon],row[wlat]]
                        well_json['features'].append(w)
            wellfile = os.path.join(directory, 'Wells1.json')
            with open(wellfile, 'w') as f:
                json.dump(well_json, f)

            #end well properties

        the_csv = os.path.join(directory, region + '_Aquifers.csv')
        with open(the_csv, mode='w') as csv_file:
            if porosity == 'Unused':
                fieldnames = ['ID', 'Name', 'CapsName']
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                for aq in aqs:
                    writer.writerow({'ID': aq[0], 'Name': aq[1], 'CapsName': aq[2]})
            else:
                fieldnames=['ID', 'Name', 'CapsName','Storage_Coefficient']
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                for aq in aqs:
                    writer.writerow({'ID': aq[0], 'Name': aq[1], 'CapsName': aq[2], 'Storage_Coefficient': aq[3]})
            print(toggle_region)
            if toggle_region=="Yes":
                writer.writerow({'ID': '-999', 'Name': region.replace("_", " ").title(), 'CapsName': region})
        try:
            # Set up the appropriate folders on the Thredds server
            blank_raster=os.path.join(thredds_serverpath,"Blank.nc")
            if not os.path.exists(blank_raster):
                lons = [0.0, 1.0]
                lons = np.array(lons)
                lats = lons
                h = netCDF4.Dataset(blank_raster, 'w', format="NETCDF4")

                h.start_date = 1850
                h.end_date = 2020
                h.interval = 1
                h.resolution = 1
                h.min_samples = 0
                h.min_ratio = 0
                h.time_tolerance = 0
                h.default = 0

                time = h.createDimension("time", 0)
                lat = h.createDimension("lat", len(lats))
                lon = h.createDimension("lon", len(lons))
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
                drawdown.long_name = "Well Drawdown"
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
                latitude[:] = lats[:]
                longitude[:] = lons[:]
                year = 1850
                timearray = []

                for i in range(0, 170):
                    print "iteration", i
                    timearray.append(datetime.datetime(year, 1, 1).toordinal() - 1)
                    year += 1
                    time[i] = timearray[i]
                    depth[i, 0, 0] = -9999
                    drawdown[i, 0, 0] = -9999
                    elevation[i, 0, 0] = -9999
                h.close()
            thredds_folder = os.path.join(thredds_serverpath, region)
            if not os.path.exists(thredds_folder):
                os.mkdir(thredds_folder)
            app_workspace = app.get_app_workspace()
            aquiferlist = getaquiferlist(app_workspace, region)

            well_file = os.path.join(app_workspace.path, region + '/Wells1.json')
            times_file = os.path.join(app_workspace.path, region + '/Wells_Master.csv')
            well_nwis_file = os.path.join(app_workspace.path, region + '/Wells.json')

            add_region(region, units)
            for aq in aquiferlist:
                i = aq['Id']
                print(aq)
                if os.path.exists(well_file) and os.path.exists(times_file):
                    subdivideaquifers(region, app_workspace, i,units)
                elif os.path.exists(well_nwis_file):
                    divideaquifers(region, app_workspace, i,units)
            success = True

        except Exception as e:
            print(e)
            success = False
        url=''
        if success:
            messages.info(request, 'Successfully added region')
            shutil.rmtree(os.path.join(app_workspace.path, region))
            url=reverse('gw:region_map')
        else:
            shutil.rmtree(os.path.join(app_workspace.path, region))
            url=reverse('gw:addregion')
        return_obj['url']=url
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

        Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
        session = Session()
        all_wells = session.query(Aquifers).filter(Aquifers.AquiferName == aquifer,
                                                   Aquifers.RegionName == region.replace("_", " "))
        for well in all_wells:
            wells= well.AquiferWellsJSON
        for i in wells['features']:
            if i['properties']['HydroID'] == int(hydroId):
                if edit == "add":
                    i['properties']['Outlier'] = True
                elif edit == "remove":
                    i['properties']['Outlier'] = False
        session.query(Aquifers).filter(Aquifers.AquiferName == aquifer,
                                       Aquifers.RegionName == region.replace("_", " ")).AquiferWellsJSON=wells
        session.commit()
        session.close()

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

#THe get_timeseries function returns the timeseries values used for interpolation for a specific netcdf file to be plotted in highcharts
def get_timeseries(request):
    return_obj = {
        'success': False
    }

    # Check if its an ajax post request
    if request.is_ajax() and request.method == 'GET':
        return_obj['success'] = True
        region=request.GET.get('region')
        netcdf=request.GET.get('netcdf')
        hydroid=request.GET.get('hydroid')

        directory = os.path.join(thredds_serverpath, region)
        file=os.path.join(directory,netcdf)
        if os.path.exists(file):
            h = netCDF4.Dataset(file, 'r+', format="NETCDF4")
            if 'tsvalue' in h.variables:
                times = h.variables['time'][:]
                for i in range(len(h.variables['hydroid'])):
                    if h.variables['hydroid'][i] == hydroid:
                        depths=h.variables['tsvalue'][:, i]
                        depths[np.isnan(depths)]=-9999
                        return_obj['depths'] = depths.tolist()
                        return_obj['times'] = times.tolist()
                        break
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
        interpolation_options = request.GET.get('interpolation_options')
        make_default=request.GET.get("make_default")
        min_samples=request.GET.get("min_samples")
        min_ratio=request.GET.get("min_ratio")
        time_tolerance=request.GET.get('time_tolerance')
        from_wizard=request.GET.get("from_wizard")
        units=request.GET.get("units")
        temporal_interpolation=request.GET.get("temporal_interpolation")
        porosity=request.GET.get("porosity")
        ndmin=request.GET.get("ndmin")
        ndmax = request.GET.get("ndmax")
        searchradius = request.GET.get("searchradius")
        seasonal=request.GET.get("seasonal")

        return_obj['id'] = aquiferid
        app_workspace = app.get_app_workspace()
        aquiferid=int(aquiferid)

        make_default = int(make_default)
        from_wizard=int(from_wizard)

        if interpolation_type:
            ndmin=int(ndmin)
            ndmax=int(ndmax)
            searchradius=float(searchradius)
            start_date=int(start_date)
            end_date=int(end_date)
            interval=float(interval)
            resolution=float(resolution)
            length=int(length)
            min_samples=int(min_samples)
            min_ratio=float(min_ratio)
            time_tolerance=int(time_tolerance)
            porosity=float(porosity)
            seasonal=int(seasonal)

        if aquiferid==9999:
            for i in range(1,length):
                aquiferid=i
                points,returnmessage=interp_wizard(app_workspace, aquiferid, region, interpolation_type, interpolation_options, temporal_interpolation, start_date, end_date, interval, resolution, make_default, min_samples, min_ratio, time_tolerance, from_wizard, units,porosity,ndmin,ndmax,searchradius,seasonal)
        else:
            points,returnmessage=interp_wizard(app_workspace, aquiferid, region, interpolation_type, interpolation_options, temporal_interpolation, start_date, end_date, interval, resolution, make_default, min_samples, min_ratio, time_tolerance, from_wizard, units,porosity,ndmin,ndmax,searchradius,seasonal)

        return_obj['data']=points
        return_obj['message']=returnmessage
    return JsonResponse(return_obj)


#This function takes a region and aquiferid number and writes a new JSON file with data for the specified aquifer
#This function uses data from the Wells.json file for the region.
def divideaquifers(region,app_workspace,aquiferid,units):
    aquiferlist = getaquiferlist(app_workspace, region)
    for i in aquiferlist:
        if i['Id'] == int(aquiferid):
            myaquifer = i
    name=myaquifer['Name']
    Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
    session = Session()
    q = session.query(Aquifers).filter(Aquifers.AquiferName == name)
    exists = session.query(literal(True)).filter(q.exists()).scalar()
    session.close()
    if exists==None:
        minorfile = os.path.join(app_workspace.path, region + '/MinorAquifers.json')
        majorfile = os.path.join(app_workspace.path, region + '/MajorAquifers.json')
        aquiferShape = []
        fieldname = 'Aquifer_Name'

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
            all_points = json.load(f)

        if len(aquiferShape)>0:
            polygon = shape(aquiferShape[0]['geometry'])
            points = {
                'type': 'FeatureCollection',
                'features': []
            }
            aquifermin=0.0
            for well in all_points['features']:
                point=Point(well['geometry']['coordinates'])
                if polygon.contains(point) and 'TsTime' in well:
                    well['properties']['AquiferID']=int(aquiferid)
                    points['features'].append(well)
                    array=[]
                    # The following code sorts the timeseries entries for each well so they are in chronological order
                    length = len(well['TsTime'])
                    for j in range(0, len(well['TsTime'])):
                        array.append((well['TsTime'][j], well['TsValue'][j]))
                    array.sort(key=itemgetter(0))
                    well['TsTime'] = []
                    well['TsValue'] = []
                    # This portion of the sorting code checks to see if the dates are duplicates and does not add them if they are
                    oldtime = -9999.5555
                    for j in range(0, length):
                        #These next 2 lines calculate the aquifermin
                        if array[j][1]<aquifermin:
                            aquifermin=array[j][1]
                        if oldtime != array[j][0]:
                            well['TsTime'].append(array[j][0])
                            well['TsValue'].append(array[j][1])
                            oldtime = array[j][0]
            print(len(points['features']))
            points['aquifermin'] = aquifermin
        else:
            points=all_points

        directory = os.path.join(app_workspace.path, region + '/aquifers')
        if not os.path.exists(directory):
            os.makedirs(directory)
        # Write a json file to the app workspace for the specified aquifer.
        # This file includes all the geographical, time series, and properties data for the aquifer.
        filename = name.replace(' ', '_') + '.json'
        filename = os.path.join(app_workspace.path, region + '/aquifers/' + filename)

        with open(filename, 'w') as outfile:
            json.dump(points, outfile)

        if name != 'NONE' and name != "None":
            add_aquifer(points, region, name, myaquifer, units)
        return points

#This function takes a region and aquiferid number and writes a new JSON file with data for the specified aquifer.
# This function divides the data from a CSV and JSON file combination.
def subdivideaquifers(region,app_workspace,aquiferid,units):
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

    Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
    session = Session()
    q = session.query(Aquifers).filter(Aquifers.AquiferName == myaquifer['Name'])
    exists = session.query(literal(True)).filter(q.exists()).scalar()
    session.close()
    if exists == None:
        if myaquifer['Name']!=region and myaquifer['Name'].replace(' ', '_')!=region and myaquifer['Name'].replace(' ','_').title()!=region:
            with open(well_file, 'r') as f:
                wells_json = json.load(f)
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
                    if row:
                        if row['AquiferID'] == aquifer_id_number or int(float(row['AquiferID'])) in aquifer_id_numbers:
                            if row['TsValue_normalized'] != '':
                                timestep = ((str(row['FeatureID']).strip()), (row['TsTime']), (float(row['TsValue'])),
                                            (float(row['TsValue_normalized'])))
                                time_csv.append(timestep)
        else:
            with open(well_file, 'r') as f:
                points = json.load(f)

            points['features'].sort(key=lambda x: x['properties']['HydroID'])
            print(len(points['features']))

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

        if name != 'NONE' and name != "None":
            add_aquifer(points, region, name, myaquifer, units)


        return [points,aquifermin]


#This function finds all the netcdf files for the aquifer on the Thredds server and returns an object for each one with its attributes
def gettimelist(region,aquifer):

    list = []
    timelist=[]
    directory=os.path.join(thredds_serverpath,region)
    print(directory)
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
        if 'interp_options' in h.ncattrs():
            mytime['Interp_Options']=h.interp_options
        if 'temporal_interpolation' in h.ncattrs():
            mytime['temporal_interpolation']=h.temporal_interpolation
        h.close()

        timelist.append(mytime)
    return timelist

def interp_wizard(app_workspace, aquiferid, region, interpolation_type,interpolation_options, temporal_interpolation, start_date, end_date, interval, resolution, make_default, min_samples, min_ratio, time_tolerance, from_wizard, units,porosity,ndmin,ndmax,searchradius,seasonal):
    if from_wizard==True:
        interpolate = 1
    else:
        interpolate=0

    Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
    session = Session()
    aquiferlist = session.query(Aquifers.AquiferFileName,Aquifers.AquiferWellsJSON).filter(Aquifers.RegionName == region.replace("_", " "),
                                                 Aquifers.AquiferID == str(aquiferid))
    for aquifer in aquiferlist:
        name = aquifer.AquiferFileName
        points=aquifer.AquiferWellsJSON
    session.close()

    if interpolation_type:
        date_name=name+"."+str(start_date)+"."+str(end_date)+"."+str(interval)+"."+str(int(resolution*100))+"."+str(min_samples)+"."+str(int(min_ratio*100))+"."+str(time_tolerance)+"."+interpolation_type[0]
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


    print(len(points['features']))

    returnmessage=''
    # Execute the following function to interpolate groundwater levels and create a netCDF File and upload it to the server
    if interpolate == 1:

        returnmessage=upload_netcdf(points, name, app_workspace, aquiferid, region, interpolation_type,interpolation_options, temporal_interpolation, start_date, end_date,
                      interval, resolution, min_samples, min_ratio, time_tolerance, date_name, make_default, units,porosity,ndmin,ndmax,searchradius,seasonal)

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
        print(e)
    finally:
        return JsonResponse(return_json)