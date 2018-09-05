from django.shortcuts import render
from django.shortcuts import redirect, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from tethys_sdk.gizmos import Button, SelectInput, RangeSlider, TextInput
import csv
import os
import tempfile
import shutil
from .app import Gw as app
import urllib
import json
import calendar
import datetime
import pandas as pd
from operator import itemgetter

#global variables
#thredds_serverpath='/home/tethys/Thredds/groundwater/'
thredds_serverpath = "/home/student/tds/apache-tomcat-8.5.30/content/thredds/public/testdata/groundwater/"

@login_required()
def home(request):
    """
    Controller for the app home page.
    """

    context = {

    }

    return render(request, 'gw/home.html', context)

@login_required()
def addregion(request):
    """
    Controller for the addregion page.
    """
    file_error=''
    region_error=''
    border_error=''
    major_error=''
    id_error=''

    id=None
    region=None
    csv_file=None
    border_file=None
    major_file=None
    minor_file=None

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

        if request.FILES and 'csv-file' in request.FILES:
            csv_file=request.FILES.getlist('csv-file')
        if request.FILES and 'border-file' in request.FILES:
            border_file=request.FILES.getlist('border-file')
        if request.FILES and 'major-file' in request.FILES:
            major_file=request.FILES.getlist('major-file')
        if request.FILES and 'minor-file' in request.FILES:
            minor_file=request.FILES.getlist('minor-file')

        if not csv_file or len(csv_file)<1:
            has_errors=True
            file_error='CSV file of aquifer information is required.'
        if not border_file or len(border_file)<1:
            has_errors=True
            border_error='JSON file for the region boundary is required.'
        if not major_file or len(major_file)<1:
            has_errors=True
            major_error='JSON file for the major aquifers is required.'

        if not has_errors:
            csv_file=csv_file[0]
            border_file = border_file[0]
            major_file=major_file[0]

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
            try:
                writefile(csv_file,region+"_Aquifers.csv")
                writefile(border_file,region+"_State_Boundary.json")
                writefile(major_file,"MajorAquifers.json")
                if minor_file:
                    minor_file=minor_file[0]
                    writefile(minor_file, "MinorAquifers.json")
                pullnwis(id, app_workspace, region)

                #Set up the appropriate folders on the Thredds server
                thredds_folder=os.path.join(thredds_serverpath,region)
                if not os.path.exists(thredds_folder):
                    os.mkdir(thredds_folder)
                    idw=os.path.join(thredds_folder,"IDW")
                    os.mkdir(idw)
                    kriging=os.path.join(thredds_folder,"Kriging")
                    os.mkdir(kriging)

                success=True

            except Exception as e:
                print e
                success=False

            if success:
                messages.info(request, 'Successfully added region')
            else:
                messages.info(request, 'Unable to add region.')
            return redirect(reverse('gw:region_map'))

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
        'file_error':file_error,
        'border_error':border_error,
        'major_error':major_error
    }

    return render(request, 'gw/addregion.html', context)

@login_required()
def region_map(request):
    """
    Controller for the app home page.
    """
    app_workspace=app.get_app_workspace()
    dirs=next(os.walk(app_workspace.path))[1]
    regions=[]
    for entry in dirs:
        region=(entry,entry)
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

    select_interpolation = SelectInput(display_text='Select Interpolation Method',
                                 name='select_interpolation',
                                 multiple=False,
                                 options=[("IDW (Shepard's Method)", 'IDW'), ('Kriging', 'Kriging')],
                                 initial="IDW (Shepard's Method)",
                                 attributes={
                                     'onchange': 'list_dates(1)'#this calls list_dates, which then calls changeWMS
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
                                    'onchange': 'changeWMS()'
                                }
    )
    delete_button=Button(display_text='Delete Selected Raster Animation',
                         name='delete_button',
                         icon='glyphicon glyphicon-remove',
                         style='danger',
                         disabled=False,
                         attributes={
                             'data-toggle': 'tooltip',
                             'data-placement': 'top',
                             'title': 'Remove',
                             'onclick':"confirm_delete()",
                         }
    )
    default_button = Button(display_text='Set Selected Raster Animation as Default',
                           name='default_button',
                           icon='glyphicon glyphicon-menu-right',
                           style='default',
                           disabled=False,
                           attributes={
                               'data-toggle': 'tooltip',
                               'data-placement': 'top',
                               'title': 'Make Default',
                               'onclick': "confirm_default()",
                           }
                           )

    context = {
        "select_region":select_region,
        "select_aquifer":select_aquifer,
        "required_data": required_data,
        "select_interpolation": select_interpolation,
        "select_view":select_view,
        "available_dates":available_dates,
        'delete_button':delete_button,
        'default_button':default_button,
    }

    return render(request, 'gw/region_map.html', context)

@login_required()
def interpolation(request):
    """
    Controller for the app home page.
    """
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
                               }
    )


    select_interpolation = SelectInput(display_text='Interpolation Method',
                                 name='select_interpolation',
                                 multiple=False,
                                 options=[("IDW (Shepard's Method)", 'IDW'), ('Kriging', 'Kriging')],
                                 initial="IDW (Shepard's Method)",
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
                           options=[("1 year",1),("2 years",2),("5 years",5),("10 years",10),("25 years",25)],
                           initial="5 years"
                           )
    resolution = SelectInput(display_text='Raster Resolution',
                            name='resolution',
                            multiple=False,
                            options=[(".01 degree", .01), (".025 degree", .025), (".05 degree", .05), (".1 degree", .10)],
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
        'time_tolerance':time_tolerance
    }

    return render(request, 'gw/interpolation.html', context)


#The pullnwis function pulls data from the web for a specified region and writes the data to a JSON file named Wells.JSON in the appropriate folder.
def pullnwis(state, app_workspace,region):
    link = "https://waterservices.usgs.gov/nwis/gwlevels/?format=json&stateCd="+state+"&startDT=1850-01-01&endDT=2018-7-31&parameterCd=72019&siteStatus=all"
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

    url = "https://waterservices.usgs.gov/nwis/site/?format=rdb&stateCd="+state+"&siteType=GW&siteStatus=all"
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