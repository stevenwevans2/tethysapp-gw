from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from tethys_sdk.gizmos import Button, SelectInput, RangeSlider

@login_required()
def home(request):
    """
    Controller for the app home page.
    """

    context = {

    }

    return render(request, 'gw/home.html', context)

def region_map(request):
    """
    Controller for the app home page.
    """
    select_region = SelectInput(display_text='Select Region',
                                 name='select_region',
                                 multiple=False,
                                 options=[('Texas', 'Texas'), ('Utah', "Utah")],
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
                                        ('Sparta',27),('West Texas Bolsons',2),('Woodbine',29),('Yegua Jackson',31),('NA',22),('Texas',32)],
                               initial='',
                               attributes={
                                   'onchange':'change_aquifer()'
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
                                     'onchange': 'changeWMS()'
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
                                       initial="2",
                                       attributes={
                                            'onchange': 'change_filter()'
                                       }
                                       )

    context = {
        "select_region":select_region,
        "select_aquifer":select_aquifer,
        "required_data": required_data,
        "select_interpolation": select_interpolation,
        "select_view":select_view,
    }

    return render(request, 'gw/region_map.html', context)

def interpolation(request):
    """
    Controller for the app home page.
    """
    select_region = SelectInput(display_text='Select Region',
                                 name='select_region',
                                 multiple=False,
                                 options=[('Texas', 'Texas'), ('Utah', "Utah")],
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
    for i in range(1800,2019):
        date=(i,i)
        dates.append(date)
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
                            options=[("1 Sample", 1),("2 Samples",2),("5 Samples",5),("10 Samples",10),("25 Samples",25),("50 Samples",50)]
                            )
    min_ratio=SelectInput(display_text='Percent of Time Frame Well Timeseries Must Span',
                            name='min_ratio',
                            options=[("No Minimum", 0),("25%",.25),("50%",.5),("75%",.75),("100%",1.0)],
                            initial="75%"
                            )

    overwrite=SelectInput(display_text='Overwrite Existing Interpolation Files',
                          name='overwrite',
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
        "overwrite":overwrite,
        "min_samples":min_samples,
        'min_ratio':min_ratio
    }

    return render(request, 'gw/interpolation.html', context)