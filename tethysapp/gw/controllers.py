from django.shortcuts import render
from django.shortcuts import redirect, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required,user_passes_test
from tethys_sdk.gizmos import Button, SelectInput, RangeSlider, TextInput, TableView
import pandas as pd
import urllib
from urllib.parse import urlencode
import contextlib
from osgeo import gdal
from ajax_controllers import *
import copy



@login_required()
def home(request):
    """
    Controller for the app home page.
    """

    context = {

    }

    return render(request, 'gw/home.html', context)


@user_passes_test(user_permission_test)
def removeregion(request):
    """
    Controller for the remove region page.
    """
    app_workspace = app.get_app_workspace()
    dirs = next(os.walk(app_workspace.path))[1]
    regions = []
    for entry in dirs:
        region = (entry, entry)
        regions.append(region)
    select_region = SelectInput(display_text='Select a Region to Remove:',
        name='select_region',
        multiple=False,
        options=regions,
        initial='Texas',
        attributes={
        }
    )
    submit_button = Button(display_text='Delete Region',
       name='submit_button',
       icon='glyphicon glyphicon-remove',
       style='danger',
       disabled=False,
       attributes={
           'data-toggle': 'tooltip',
           'data-placement': 'top',
           'title': 'Delete Selected Region from the app',
           'onclick': "delete_region()",
       }
   )

    context = {
        'select_region':select_region,
        'submit_button':submit_button
    }

    return render(request, 'gw/remove_region.html', context)


@user_passes_test(user_permission_test)
def addregion_nwis(request):
    """
    Controller for the addregion page.
    """
    region_error=''
    border_error=''
    major_error=''
    id_error=''
    dem_error=''

    id=None
    region=None
    border_file=None
    major_file=None
    minor_file=None
    dem_file=None

    if request.POST and 'add_button' in request.POST:
        has_errors=False
        region=request.POST.get('region_name')
        if not region:
            has_errors=True
            region_error='Region name is required.'
        id=request.POST.get('stateID')
        if not id:
            has_errors=True
            id_error='Two letter ID is required.'

        if request.FILES and 'border-file' in request.FILES:
            border_file=request.FILES.getlist('border-file')
        if request.FILES and 'major-file' in request.FILES:
            major_file=request.FILES.getlist('major-file')
        if request.FILES and 'minor-file' in request.FILES:
            minor_file=request.FILES.getlist('minor-file')
        if request.FILES and 'dem-file' in request.FILES:
            dem_file=request.FILES.getlist('dem-file')

        if not border_file or len(border_file)<1:
            has_errors=True
            border_error='JSON file for the region boundary is required.'
        if not major_file or len(major_file)<1:
            has_errors=True
            major_error='JSON file for the major aquifers is required.'
        if not dem_file or len(dem_file)<1:
            has_errors=True
            dem_error='Regional DEM TIF File is required.'

        if not has_errors:
            border_file = border_file[0]
            major_file=major_file[0]
            dem_file=dem_file[0]
            region = region.replace(' ', '_')

            app_workspace = app.get_app_workspace()
            # Function to write the file from the uploaded file
            def writefile(input, output):
                lines = []
                for line in input:
                    lines.append(line)

                directory = os.path.join(app_workspace.path, region)
                if not os.path.exists(directory):
                    os.mkdir(directory)
                the_csv = os.path.join(directory, output)
                with open(the_csv, 'w') as f:
                    for line in lines:
                        f.write(line)
            # try:
            # writefile(csv_file,region+"_Aquifers.csv")
            writefile(border_file,region+"_State_Boundary.json")
            writefile(major_file,"MajorAquifers.json")
            writefile(dem_file,'temp.tif')
            State_Boundary = os.path.join(app_workspace.path, region + '/' + region + '_State_Boundary.json')
            with open(State_Boundary, 'r') as f:
                state = json.load(f)
            AquiferShape=state
            lonmin=360
            lonmax=-360
            latmin=90
            latmax=-90
            for shape in AquiferShape['features']:
                if 'geometry' in shape:
                    if shape['geometry']is not None:
                        mylonmin,mylatmin,mylonmax,mylatmax=bbox(shape)
                        if mylatmin<latmin:
                            latmin=mylatmin
                        if mylonmin<lonmin:
                            lonmin=mylonmin
                        if mylatmax>latmax:
                            latmax=mylatmax
                        if mylonmax>lonmax:
                            lonmax=mylonmax
            # lonmin, latmin, lonmax, latmax = bbox(AquiferShape['features'][0])
            out_path = os.path.join(app_workspace.path, region + "/DEM.tif")
            dem_path=os.path.join(app_workspace.path, region + "/temp.tif")
            ds = gdal.Open(dem_path)
            ds = gdal.Translate(out_path, ds, outputSRS='EPSG:4326', projWin=[lonmin, latmax, lonmax, latmin])
            ds = None
            os.remove(dem_path)
            if minor_file:
                minor_file=minor_file[0]
                writefile(minor_file, "MinorAquifers.json")
            # # Code for writing the aquifers_csv file
            # directory = os.path.join(app_workspace.path, region)
            # aqs = []
            # for filename in os.listdir(directory):
            #     if filename.startswith('MinorAquifers.json'):
            #         minorfile = os.path.join(directory, 'MinorAquifers.json')
            #         with open(minorfile) as f:
            #             minor_json = json.load(f)
            #         for a in minor_json['features']:
            #             aq = [a['properties']['AquiferID'], a['properties']['DisplayName'],
            #                   a['properties']['Aquifer_Name']]
            #             aqs.append(aq)
            # majorfile = os.path.join(directory, 'MajorAquifers.json')
            # with open(majorfile) as f:
            #     major_json = json.load(f)
            # for a in major_json['features']:
            #     aq = [a['properties']['AquiferID'], a['properties']['DisplayName'], a['properties']['Aquifer_Name']]
            #     aqs.append(aq)
            # the_csv = os.path.join(directory, region + '_Aquifers.csv')
            # with open(the_csv, mode='w') as csv_file:
            #     fieldnames = ['ID', 'Name', 'CapsName']
            #     writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            #     writer.writeheader()
            #     for aq in aqs:
            #         writer.writerow({'ID': aq[0], 'Name': aq[1], 'CapsName': aq[2]})
            #     writer.writerow({'ID': '-999', 'Name': region.replace("_", " ").title(), 'CapsName': region})
            # # end code for writing the aquifers_csv file

            pullnwis(id, app_workspace, region)

            # #Set up the appropriate folders on the Thredds server
            # thredds_folder=os.path.join(thredds_serverpath,region)
            # if not os.path.exists(thredds_folder):
            #     os.mkdir(thredds_folder)
            #
            # #Addition
            # aquiferlist = getaquiferlist(app_workspace, region)
            #
            # well_file = os.path.join(app_workspace.path, region + '/Wells.json')
            # print "to divide aquifers"
            # for aq in aquiferlist:
            #     i = aq['Id']
            #     if os.path.exists(well_file):
            #         divideaquifers(region, app_workspace, i)
            # #End Addition
            # success = True
            #
            # # except Exception as e:
            # #     print e
            # #     success=False
            #
            # if success:
            #     messages.info(request, 'Successfully added region')
            # else:
            #     messages.info(request, 'Unable to add region.')
            # return redirect(reverse('gw:region_map'))
        # if not has_errors:
            messages.info(request, 'Files uploaded successfully.')
            return redirect(reverse('gw:addregion_nwis2', kwargs={'region': region}))
        else:
            messages.info(request, 'Unable to upload files.')

        messages.error(request, "Please fix errors.")


    #Define form gizmos
    region_name = TextInput(display_text='Enter a name for the region:',
                           name='region_name',
                           placeholder='e.g.: Texas',
                            error=region_error)
    add_button=Button(
        display_text='Add Region',
        name='add_button',
        icon='glyphicon-plus',
        style='success',
        attributes={'form':'add-region-form'},
        submit=True
    )

    stateId=TextInput(display_text='Enter the two letter state ID for your region:',
                      name='stateID',
                      placeholder='e.g.: tx',
                      error=id_error)

    context = {
        'region_name':region_name,
        'stateId':stateId,
        'add_button':add_button,
        'border_error':border_error,
        'major_error':major_error,
        'dem_error':dem_error
    }

    return render(request, 'gw/addregion_nwis.html', context)

@login_required()
def addregion_nwis2(request,region):
    success=False

    print("Region on next line:")
    print(region)
    app_workspace=app.get_app_workspace()
    # Code for writing the aquifers_csv file
    #options for the user to select which property in the aquifers json file to use as DisplayName, ID, and Name
    directory = os.path.join(app_workspace.path, region)
    aqs = []
    majorfile = os.path.join(directory, 'MajorAquifers.json')
    with open(majorfile) as f:
        major_json = json.load(f)
    major_props=major_json['features'][0]['properties'].viewkeys()
    print(major_props)

    count = min(3, len(major_json['features']))
    myrows = []
    for i in range(0, count):
        row = major_json['features'][i]['properties'].viewvalues()
        myrows.append(row)

    w_ids = []
    for i in major_props:
        id = (i, i)
        w_ids.append(id)
    table_view_aq = TableView(column_names=(major_props),
                              rows=myrows,
                              hover=True,
                              striped=False,
                              bordered=False,
                              condensed=False)

    add_button = Button(
        display_text='Add Region',
        name='add_button',
        icon='glyphicon-plus',
        style='success',
        attributes={'onclick': 'add_aquifer_nwis_settings()'},
        submit=True
    )
    ids=[]
    for i in major_props:
        id = (i, i)
        ids.append(id)
    select_region = SelectInput(display_text='Region',
       name='select_region',
       multiple=False,
       options=[(region,region)],
       initial=region,
       attributes={
       }
   )
    select_AquiferID = SelectInput(display_text='Select AquiferID Attribute',
        name='select_AquiferID',
        multiple=False,
        options=ids,
        initial='AquiferID',
        attributes={
        }
    )
    select_DisplayName = SelectInput(display_text='Select DisplayName Attribute',
       name='select_DisplayName',
       multiple=False,
       options=ids,
       initial='DisplayName',
       attributes={
       }
   )
    select_Aquifer_Name = SelectInput(display_text='Select Aquifer_Name Attribute',
       name='select_Aquifer_Name',
       multiple=False,
       options=ids,
       initial='Aquifer_Name',
       attributes={
       }
   )
    opt_a_ids = copy.deepcopy(ids)
    opt_a_ids.insert(0, ('Unused', 'Unused'))
    select_porosity = SelectInput(display_text='Select Aquifer Storage Coefficient Attribute (optional)',
      name='select_porosity',
      multiple=False,
      options=opt_a_ids,
      initial='Unused',
      attributes={
      }
    )


    context={
        'add_button':add_button,
        'select_AquiferID':select_AquiferID,
        'select_DisplayName':select_DisplayName,
        'select_Aquifer_Name':select_Aquifer_Name,
        'select_porosity':select_porosity,
        'select_region':select_region,
        'table_view_aq':table_view_aq,
    }
    return render(request, 'gw/addregion_nwis2.html', context)





@user_passes_test(user_permission_test)
def addregion(request):
    """
    Controller for the addregion page.
    """
    region_error = ''
    border_error = ''
    major_error = ''
    wells_error = ''
    time_error = ''
    dem_error = ''

    def writefilestoworkspace(request):
        region_error1 = ''
        border_error1 = ''
        major_error1 = ''
        wells_error1 = ''
        time_error1 = ''
        dem_error1 = ''
        def writefile(input, output):
            lines = []
            for line in input:
                lines.append(line)
            app_workspace = app.get_app_workspace()
            directory = os.path.join(app_workspace.path, region)
            if not os.path.exists(directory):
                os.mkdir(directory)
            the_csv = os.path.join(directory, output)
            with open(the_csv, 'w') as f:
                for line in lines:
                    f.write(line)
        region = None
        border_file = None
        major_file = None
        minor_file = None
        wells_file = None
        time_file = None
        dem_file = None
        has_errors = False
        region = request.POST.get('region_name')
        if not region:
            has_errors = True
            region_error = 'Region name is required.'

        if request.FILES and 'border-file' in request.FILES:
            border_file = request.FILES.getlist('border-file')
        if request.FILES and 'major-file' in request.FILES:
            major_file = request.FILES.getlist('major-file')
        if request.FILES and 'minor-file' in request.FILES:
            minor_file = request.FILES.getlist('minor-file')
        if request.FILES and 'wells-file' in request.FILES:
            wells_file = request.FILES.getlist('wells-file')
        if request.FILES and 'time-file' in request.FILES:
            time_file = request.FILES.getlist('time-file')
        if request.FILES and 'dem-file' in request.FILES:
            dem_file = request.FILES.getlist('dem-file')

        if not border_file or len(border_file) < 1:
            has_errors = True
            border_error1 = 'JSON file for the region boundary is required.'
        if not major_file or len(major_file) < 1:
            has_errors = True
            major_error1 = 'JSON file for the major aquifers is required.'
        if not wells_file or len(wells_file) < 1:
            has_errors = True
            wells_error1 = 'JSON file of well locations is required.'
        if not time_file or len(time_file) < 1:
            has_errors = True
            time_error1 = 'CSV of well time series information is required.'
        if not dem_file or len(dem_file) < 1:
            has_errors = True
            dem_error1 = 'DEM for the region is required.'
        errors=[border_error1,major_error1,wells_error1,time_error1,dem_error1,region_error1]
        if not has_errors:
            border_file = border_file[0]
            major_file = major_file[0]
            wells_file = wells_file[0]
            time_file = time_file[0]
            dem_file = dem_file[0]
            region = region.replace(' ', '_')
            app_workspace = app.get_app_workspace()

            # writefile(csv_file, region + "_Aquifers.csv")
            writefile(border_file, region + "_State_Boundary.json")
            writefile(major_file, "MajorAquifers.json")
            writefile(wells_file, "Wells1.json")
            writefile(time_file, "Wells_Master.csv")
            writefile(dem_file, "temp.tif")
            #Code for adding the DEM

            State_Boundary = os.path.join(app_workspace.path, region + '/' + region + '_State_Boundary.json')
            with open(State_Boundary, 'r') as f:
                state = json.load(f)
            AquiferShape = state
            lonmin = 360
            lonmax = -360
            latmin = 90
            latmax = -90
            for shape in AquiferShape['features']:
                if 'geometry' in shape:
                    if shape['geometry'] is not None:
                        mylonmin, mylatmin, mylonmax, mylatmax = bbox(shape)
                        if mylatmin < latmin:
                            latmin = mylatmin
                        if mylonmin < lonmin:
                            lonmin = mylonmin
                        if mylatmax > latmax:
                            latmax = mylatmax
                        if mylonmax > lonmax:
                            lonmax = mylonmax
            out_path = os.path.join(app_workspace.path, region + "/DEM.tif")
            dem_path = os.path.join(app_workspace.path, region + "/temp.tif")
            ds = gdal.Open(dem_path)
            ds = gdal.Translate(out_path, ds, outputSRS='EPSG:4326', projWin=[lonmin, latmax, lonmax, latmin])
            ds = None
            os.remove(dem_path)
            if minor_file:
                minor_file = minor_file[0]
                writefile(minor_file, "MinorAquifers.json")
            #Code for writing the aquifers_csv file

            return region, errors
        messages.error(request, "Please fix errors.")
        return region,errors
    if request.POST and 'add_button' in request.POST:
        region, errors = writefilestoworkspace(request)
        border_error = errors[0]
        major_error = errors[1]
        wells_error = errors[2]
        time_error = errors[3]
        dem_error = errors[4]
        region_error = errors[5]
        has_errors=False
        for i in errors:
            if i!="":
                has_errors=True
        success=False
        if not has_errors:
            messages.info(request, 'Files uploaded successfully.')
            return redirect(reverse('gw:addregion2',kwargs={'region':region}))
        else:
            messages.info(request, 'Unable to upload files.')
            # return redirect(reverse('gw:addregion'))

    #Define form gizmos
    region_name = TextInput(display_text='Enter a name for the region:',
                           name='region_name',
                           placeholder='e.g.: Texas',
                            error=region_error)
    add_button=Button(
        display_text='Upload Files',
        name='add_button',
        icon='glyphicon-plus',
        style='success',
        attributes={'form':'add-region-form'},
        submit=True
    )

    context = {
        'region_name':region_name,
        'add_button':add_button,
        'border_error':border_error,
        'major_error':major_error,
        'wells_error':wells_error,
        'time_error':time_error,
        'dem_error':dem_error,
    }
    return render(request, 'gw/addregion.html', context)

@login_required()
def addregion2(request,region):
    success=False

    print("Region on next line:")
    print(region)
    app_workspace=app.get_app_workspace()
    # Code for writing the aquifers_csv file
    #options for the user to select which property in the aquifers json file to use as DisplayName, ID, and Name
    directory = os.path.join(app_workspace.path, region)
    aqs = []
    majorfile = os.path.join(directory, 'MajorAquifers.json')
    with open(majorfile) as f:
        major_json = json.load(f)
    major_props=major_json['features'][0]['properties'].viewkeys()
    print(major_props)

    count = min(3, len(major_json['features']))
    myrows = []
    for i in range(0, count):
        row = major_json['features'][i]['properties'].viewvalues()
        myrows.append(row)

    w_ids = []
    for i in major_props:
        id = (i, i)
        w_ids.append(id)
    table_view_aq = TableView(column_names=(major_props),
                           rows=myrows,
                           hover=True,
                           striped=False,
                           bordered=False,
                           condensed=False)

    add_button = Button(
        display_text='Add Region',
        name='add_button',
        icon='glyphicon-plus',
        style='success',
        attributes={'onclick': 'add_aquifer_settings()'},
        submit=True
    )
    ids=[]
    for i in major_props:
        id = (i, i)
        ids.append(id)
    select_region = SelectInput(display_text='Region',
       name='select_region',
       multiple=False,
       options=[(region,region)],
       initial=region,
       attributes={
       }
   )
    select_AquiferID = SelectInput(display_text='Select AquiferID Attribute',
        name='select_AquiferID',
        multiple=False,
        options=ids,
        initial='AquiferID',
        attributes={
        }
    )
    select_DisplayName = SelectInput(display_text='Select DisplayName Attribute',
       name='select_DisplayName',
       multiple=False,
       options=ids,
       initial='DisplayName',
       attributes={
       }
   )
    select_Aquifer_Name = SelectInput(display_text='Select Aquifer_Name Attribute',
       name='select_Aquifer_Name',
       multiple=False,
       options=ids,
       initial='Aquifer_Name',
       attributes={
       }
   )
    opt_a_ids = copy.deepcopy(ids)
    opt_a_ids.insert(0, ('Unused', 'Unused'))
    select_porosity = SelectInput(display_text='Select Aquifer Storage Coefficient Attribute (optional)',
      name='select_porosity',
      multiple=False,
      options=opt_a_ids,
      initial='Unused',
      attributes={
      }
  )

    # These options are for choosing the well attributes for your region
    well_file = os.path.join(directory, 'Wells1.json')
    with open(well_file) as f:
        well_json = json.load(f)
    well_props = well_json['features'][0]['properties'].viewkeys()
    count=min(3,len(well_json['features']))
    myrows=[]
    for i in range(0,count):
        row=well_json['features'][i]['properties'].viewvalues()
        myrows.append(row)

    w_ids = []
    for i in well_props:
        id = (i, i)
        w_ids.append(id)
    table_view = TableView(column_names=(well_props),
       rows=myrows,
       hover=True,
       striped=False,
       bordered=False,
       condensed=False)

    opt_ids = copy.deepcopy(w_ids)
    opt_ids.insert(0, ('Unused', 'Unused'))

    select_hydroid = SelectInput(display_text='Select Well HydroID Attribute',
                                 name='select_hydroid',
                                 multiple=False,
                                 options=w_ids,
                                 initial='HydroID',
                                 attributes={
                                 }
                                 )
    select_elev = SelectInput(display_text='Select Well Elevation Attribute (optional)',
                                 name='select_elev',
                                 multiple=False,
                                 options=opt_ids,
                                 initial='LandElev',
                                 attributes={
                                 }
                                 )
    select_aqid = SelectInput(display_text='Select Well AquiferID Attribute',
                                 name='select_aqid',
                                 multiple=False,
                                 options=w_ids,
                                 initial='AquiferID',
                                 attributes={
                                 }
                                 )
    select_depth = SelectInput(display_text='Select Well Depth Attribute (optional)',
                                 name='select_depth',
                                 multiple=False,
                                 options=opt_ids,
                                 initial='Unused',
                                 attributes={
                                 }
                                 )
    select_type = SelectInput(display_text='Select Well Type Attribute (optional)',
                               name='select_type',
                               multiple=False,
                               options=opt_ids,
                               initial='Unused',
                               attributes={
                               }
                               )
    context={
        'add_button':add_button,
        'select_AquiferID':select_AquiferID,
        'select_DisplayName':select_DisplayName,
        'select_Aquifer_Name':select_Aquifer_Name,
        'select_porosity':select_porosity,
        'select_region':select_region,
        'table_view':table_view,
        'select_hydroid':select_hydroid,
        'select_aqid':select_aqid,
        'select_elev':select_elev,
        'select_type':select_type,
        'select_depth':select_depth,
        'table_view_aq':table_view_aq,
    }
    return render(request, 'gw/addregion2.html', context)


@login_required()
def region_map(request):
    """
    Controller for the app home page.
    """
    app_workspace=app.get_app_workspace()
    dirs=next(os.walk(app_workspace.path))[1]
    regions=[]
    for entry in dirs:
        # One time code to fix aquifer names
        # names_list = ['Name', 'AQ_NAME', 'AQU_NAME', 'Hydro_Zone', 'altName', 'WMU_NAME']
        # directory = os.path.join(app_workspace.path,entry)
        # the_csv=os.path.join(directory,entry+'_Aquifers.csv')
        # majorfile=os.path.join(directory,'MajorAquifers.json')
        # aquifercsv=[]
        # with open(the_csv) as csvfile:
        #     reader = csv.DictReader(csvfile)
        #     for row in reader:
        #         if row:
        #             aq=((row['ID']),(row["Name"]),(row['CapsName']))
        #             aquifercsv.append(aq)
        # with open(majorfile) as f:
        #     json_object=json.load(f)
        # for aq in aquifercsv:
        #     for aquifer in json_object['features']:
        #         if aq[2]==aquifer['properties']['Aquifer_Name']:
        #             if 'DisplayName' in aquifer:
        #                 del aquifer['DisplayName']
        #             aquifer['properties']['AquiferID']=aq[0]
        #             aquifer['properties']['DisplayName']=aq[1]
        #             print(aq[1])
        #             break
        # with open(majorfile,'w') as f:
        #     json.dump(json_object,f)
        # for filename in os.listdir(directory):
        #     if filename.startswith('MinorAquifers.json'):
        #         minorfile=os.path.join(directory,'MinorAquifers.json')
        #         with open(minorfile) as f:
        #             json_object = json.load(f)
        #         for aq in aquifercsv:
        #             for aquifer in json_object['features']:
        #                 if aq[2] == aquifer['properties']['Aquifer_Name']:
        #                     if 'DisplayName' in aquifer:
        #                         del aquifer['DisplayName']
        #                     aquifer['properties']['AquiferID'] = aq[0]
        #                     aquifer['properties']['DisplayName'] = aq[1]
        #                     break
        #         with open(minorfile, 'w') as f:
        #             json.dump(json_object, f)
        # for filename in os.listdir(directory):
        #     if filename.startswith('MajorAquifers.json'):
        #         myfile=os.path.join(directory,'MajorAquifers.json')
        #         with open(myfile) as f:
        #             json_object=json.load(f)
        #         for aquifer in json_object['features']:
        #             for name in names_list:
        #                 if name in aquifer['properties']:
        #                     aquifer['properties']['Aquifer_Name']=aquifer['properties'][name]
        #                     break
        #         with open(myfile, 'w') as f:
        #             json.dump(json_object, f)
        # for filename in os.listdir(directory):
        #     myfile = os.path.join(directory, 'MinorAquifers.json')
        #     if filename.startswith('MinorAquifers.json'):
        #         with open(myfile) as f:
        #             json_object=json.load(f)
        #         for aquifer in json_object['features']:
        #             for name in names_list:
        #                 if name in aquifer['properties']:
        #                     aquifer['properties']['Aquifer_Name']=aquifer['properties'][name]
        #                     break
        #         with open(myfile, 'w') as f:
        #             json.dump(json_object, f)
        # #end one time fix code

        region=(entry.replace("_"," "),entry)
        regions.append(region)
    select_region = SelectInput(display_text='Select Region',
                                 name='select_region',
                                 multiple=False,
                                 options=regions,
                                 initial='Texas',
                                 attributes={
                                     'onchange':'list_aquifer()'
                                 }
    )
    region_home=Button(display_text='Region Home',
                         name='region_home',
                         icon='glyphicon glyphicon-home',
                         attributes={
                             'data-toggle': 'tooltip',
                             'data-placement': 'top',
                             'title': 'Jump to Home View for Region',
                             'onclick':"list_aquifer()",
                         }
    )

    select_aquifer=SelectInput(display_text='Select Aquifer',
                               name='select_aquifer',
                               multiple=False,
                               options=[('',9999),('Carrizo',10),('Edwards',11),('Edwards-Trinity',13),('Gulf Coast',15),('Hueco Bolson',1),('Ogallala',21),
                                        ('Pecos Valley',3),('Seymour',4),('Trinity',28),('Blaine',6),('Blossom',7),('Bone Spring-Victorio Peak',8),
                                        ('Brazos River Alluvium',5),('Capitan Reef Complex',9),('Dockum',26),('Edwards-Trinity-High Plains',12),
                                        ('Ellenburger-San Saba',14),('Hickory',16),('Igneous',17),('Lipan', 30),('Marathon',18),
                                        ('Marble Falls',19),('Nacatoch',20),('Queen City',24),('Rita Blanca',23),('Rustler',25),
                                        ('Sparta',27),('West Texas Bolsons',2),('Woodbine',29),('Yegua Jackson',31),('None',22),('Texas',32)],
                               initial='',
                               attributes={
                                   'onchange':'list_dates(2)' #this calls list_dates, which then calls change_aquifer
                               }
    )

    select_view=SelectInput(display_text='Select Data Type',
                                 name='select_view',
                                 multiple=False,
                                 options=[("Depth to Groundwater", 'depth'), ('Elevation of Groundwater', 'elevation'),("Well Drawdown","drawdown")],
                                 attributes={
                                     'onchange':'changeWMS()'
                                 }
    )

    required_data = SelectInput(display_text='Minimum Samples per Well',
                                       name='required_data',
                                       multiple=False,
                                       options=[("0","0"),("1","1"),("2","2"),("3","3"),("4","4"),("5","5"),("6","6"),
                                                ("7", "7"),("8","8"),("9","9"),("10","10"),("11","11"),("12","12"),("13","13"),
                                                ("14", "14"),("15","15"),("16","16"),("17","17"),("18","18"),("19","19"),("20","20"),
                                                ("21", "21"),("22","22"),("23","23"),("24","24"),("25","25"),("26","26"),("27","27"),
                                                ("28", "28"),("29","29"),("30","30"),("31","31"),("32","32"),("33","33"),("34","34"),
                                                ("35", "35"),("36","36"),("37","37"),("38","38"),("39","39"),("40","40"),("41","41"),
                                                ("42", "42"),("43","43"),("44","44"),("45","45"),("46","46"),("47","47"),("48","48"),
                                                ("49", "49"),("50","50"),],
                                       initial="5",
                                       attributes={
                                            'onchange': 'change_filter()'
                                       }
                                       )

    available_dates=SelectInput(display_text='Available Raster Animations',
                                name='available_dates',
                                multiple=False,
                                options=[],
                                attributes={
                                    'onchange': 'changeWMS();toggleButtons()'
                                }
    )
    delete_button=Button(display_text='Delete Raster',
                         name='delete_button',
                         icon='glyphicon glyphicon-remove',
                         style='danger',
                         disabled=False,
                         attributes={
                             'data-toggle': 'tooltip',
                             'data-placement': 'top',
                             'title': 'Delete Selected Raster Animation',
                             'onclick':"confirm_delete()",
                         }
    )
    default_button = Button(display_text='Make Raster Default',
                           name='default_button',
                           icon='glyphicon glyphicon-menu-right',
                           style='default',
                           disabled=False,
                           attributes={
                               'data-toggle': 'tooltip',
                               'data-placement': 'top',
                               'title': 'Set Selected Raster Animation as Default',
                               'onclick': "confirm_default()",
                           }
                           )
    volume_button=Button(display_text='Aquifer Storage',
                           name='default_button',
                           icon='glyphicon glyphicon-stats',
                           style='default',
                           disabled=False,
                           attributes={
                               'data-toggle': 'tooltip',
                               'data-placement': 'top',
                               'title': 'Display Change in Aquifer Storage',
                               'onclick': "totalvolume()",
                           }
                           )

    context = {
        "select_region":select_region,
        "select_aquifer":select_aquifer,
        "required_data": required_data,
        "select_view":select_view,
        "available_dates":available_dates,
        'delete_button':delete_button,
        'default_button':default_button,
        'region_home':region_home,
        'volume_button':volume_button
    }

    return render(request, 'gw/region_map.html', context)

@login_required()
def interpolation(request):
    """
    Controller for the app home page.
    """
    select_units=SelectInput(display_text='Select Units',
                             name='select_units',
                             options=[('English','English'),("Metric","Metric")],
                             initial='English',
    )

    app_workspace = app.get_app_workspace()
    dirs = next(os.walk(app_workspace.path))[1]
    regions = []
    for entry in dirs:
        region = (entry, entry)
        regions.append(region)

    select_region = SelectInput(display_text='Select Region',
                                 name='select_region',
                                 multiple=False,
                                 options=regions,
                                 initial='Texas',
                                 attributes={
                                     'onchange':'update_aquifers()'
                                 }
    )

    select_aquifer=SelectInput(display_text='Select Aquifer',
                               name='select_aquifer',
                               multiple=False,
                               options=[('Interpolate All Aquifers',9999),('Carrizo',10),('Edwards',11),('Edwards-Trinity',13),('Gulf Coast',15),('Hueco Bolson',1),('Ogallala',21),
                                        ('Pecos Valley',3),('Seymour',4),('Trinity',28),('Blaine',6),('Blossom',7),('Bone Spring-Victorio Peak',8),
                                        ('Brazos River Alluvium',5),('Capitan Reef Complex',9),('Dockum',26),('Edwards-Trinity-High Plains',12),
                                        ('Ellenburger-San Saba',14),('Hickory',16),('Igneous',17),('Lipan', 30),('Marathon',18),
                                        ('Marble Falls',19),('Nacatoch',20),('Queen City',24),('Rita Blanca',23),('Rustler',25),
                                        ('Sparta',27),('West Texas Bolsons',2),('Woodbine',29),('Yegua Jackson',31),('None',22),('Texas',32)],
                               initial='',
                               attributes={
                                   'onchange':'get_porosity()'
                               }
    )

    select_porosity = TextInput(display_text='Enter the storage coefficient for the aquifer:',
                            name='select_porosity',
                            initial='0.1',
    )


    select_interpolation = SelectInput(display_text='Spatial Interpolation Method',
                                 name='select_interpolation',
                                 multiple=False,
                                 options=[("IDW (Shepard's Method)", 'IDW'), ('Kriging', 'Kriging'), ('Kriging with External Drift', 'Kriging with External Drift')],
                                 initial="IDW (Shepard's Method)",
                                 attributes={
                                 }
    )
    interpolation_options=SelectInput(display_text="Spatial Interpolation Options",
                                      name='interpolation_options',
                                      multiple=False,
                                      options=[("Interpolate Water Surface Elevation and Depth to Water Table Seperately","both"),
                                               ("Interpolate Water Surface Elevation, and calculate Depth to Water Table using a DEM","elev"),
                                               ("Interpolate Depth to Water Table, and calculate Water Surface Elevation using a DEM","depth")],
                                      attributes={
                                      }
    )
    temporal_interpolation = SelectInput(display_text='Temporal Interpolation Method',
                                       name='temporal_interpolation',
                                       multiple=False,
                                       options=[("Pchip Interpolation", 'pchip'), ('Multi-Linear Regression', 'MLR')],
                                       initial="Pchip Interpolation",
                                       attributes={
                                       }
    )
    dates=[]
    for i in range(1850,2019):
        date=(i,i)
        dates.append(date)
    tolerances=[("1 Year",1)]
    for i in range(2,26):
        tolerance=(str(i)+" Years",i)
        tolerances.append(tolerance)
    tolerances.append(("50 Years",50))
    tolerances.append(("No Limit", 999))
    ratios=[("No Minimum",0)]
    for i in range(5,105,5):
        ratio=(str(i)+"%",float(i)/100)
        ratios.append(ratio)
    start_date = SelectInput(display_text='Interpolation Start Date',
                                name='start_date',
                                multiple=False,
                                options=dates,
                                initial=1950
                                )
    end_date = SelectInput(display_text='Interpolation End Date',
                             name='end_date',
                             multiple=False,
                             options=dates,
                             initial=2015
                             )
    frequency = SelectInput(display_text='Time Increment',
                           name='frequency',
                           multiple=False,
                           options=[("3 months",.25),("6 months",.5),("1 year",1),("2 years",2),("5 years",5),("10 years",10),("25 years",25)],
                           initial="5 years"
                           )
    resolution = SelectInput(display_text='Raster Resolution',
                            name='resolution',
                            multiple=False,
                            options=[(".001 degree",.001),(".0025 degree",.0025),(".005 degree",.005),(".01 degree", .01), (".025 degree", .025), (".05 degree", .05), (".1 degree", .10)],
                            initial=".05 degree"
                            )
    min_samples=SelectInput(display_text='Minimum Water Level Samples per Well',
                            name='min_samples',
                            options=[("1 Sample", 1),("2 Samples",2),("5 Samples",5),("10 Samples",10),("25 Samples",25),("50 Samples",50)],
                            initial="5 Samples"
                            )
    min_ratio=SelectInput(display_text='Percent of Time Frame Well Timeseries Must Span',
                            name='min_ratio',
                            options=ratios,
                            initial="75%"
                            )
    time_tolerance = SelectInput(display_text='Temporal Extrapolation Limit',
                           name='time_tolerance',
                           multiple=False,
                           options=tolerances,
                           initial="5 Years"
                           )
    default=SelectInput(display_text='Set Interpolation as Default for the Aquifer',
                          name='default',
                          multiple=False,
                          options=[("Yes",1),("No",0)],
                          initial="No"
                          )
    submit_button = Button(
        display_text='Submit',
        name='submit_button',
        attributes={
            'data-toggle': 'tooltip',
            'data-placement': 'top',
            'title': 'Submit',
            'onclick':'submit_form()'
        }
    )


    context = {
        "select_units":select_units,
        "select_region":select_region,
        "select_aquifer":select_aquifer,
        "select_interpolation": select_interpolation,
        "start_date":start_date,
        "end_date":end_date,
        "frequency":frequency,
        "resolution":resolution,
        "submit_button":submit_button,
        "default":default,
        "min_samples":min_samples,
        'min_ratio':min_ratio,
        'time_tolerance':time_tolerance,
        'interpolation_options':interpolation_options,
        'temporal_interpolation':temporal_interpolation,
        'select_porosity':select_porosity
    }

    return render(request, 'gw/interpolation.html', context)


#The pullnwis function pulls data from the web for a specified region and writes the data to a JSON file named Wells.JSON in the appropriate folder.
def pullnwis(state, app_workspace,region):
    states=state.split(',')
    print(states)
    points = {
        'type': 'FeatureCollection',
        'features': []
    }
    aquifermin = 0.0
    for mystate in states:
        print mystate
        todaysdate=datetime.datetime.today()
        urlyear=str(todaysdate.year)
        urlmonth=str(todaysdate.month)
        print urlmonth,urlyear
        link = "https://waterservices.usgs.gov/nwis/gwlevels/?format=json&stateCd="+mystate+"&startDT=1850-01-01&endDT="+urlyear+"-"+urlmonth+"-28&parameterCd=72019&siteStatus=all"
        with contextlib.closing(urllib.urlopen(link)) as f:
        # f=urllib.open(link)
            myfile=f.read()
        myfile = json.loads(myfile)
        print len(myfile['value']['timeSeries'])


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

        url = "https://waterservices.usgs.gov/nwis/site/?format=rdb&stateCd="+mystate+"&siteType=GW&siteStatus=all"
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
    # End Loop
    count = 0
    print("Starting the TsValue loop")
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
    print("done with this function")