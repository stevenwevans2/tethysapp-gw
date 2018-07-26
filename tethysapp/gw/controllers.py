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

    select_aquifer=SelectInput(display_text='Select Aquifer',
                               name='select_aquifer',
                               multiple=False,
                               options=[('Carrizo',10),('Edwards',11),('Edwards-Trinity',13),('Gulf Coast',15),('Hueco Bolson',1),('Ogallala',21),
                                        ('Pecos Valley',3),('Seymour',4),('Trinity',28),('Blaine (minor)',6),('Blossom (minor)',7),('Bone Spring-Victorio Peak (minor)',8),
                                        ('Brazos River Alluvium (minor)',5),('Capitan Reef Complex (minor)',9),('Dockum (minor)',26),('Edwards-Trinity (High Plains) (minor)',12),
                                        ('Ellenburger-San-Aba (minor)',14),('Hickory (minor)',16),('Igneous (minor)',17),('Lipan (minor)', 30),('Marathon (minor)',18),
                                        ('Marble Falls (minor)',19),('Nacatoch (minor)',20),('Queen City (minor)',24),('Rita Blanca (minor)',23),('Rustler (minor)',25),
                                        ('Sparta (minor)',27),('West Texas Bolsons (minor)',2),('Woodbine (minor)',29),('Yegua Jackson (minor)',31),('NA',22),('All',32)],
                               initial='All',
                               attributes={
                                   'onchange':'change_region()'
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
                                       initial="2"
                                       )

    context = {
        "select_aquifer":select_aquifer,
        "required_data": required_data,
        "select_interpolation": select_interpolation,
        "select_view":select_view,
    }

    return render(request, 'gw/region_map.html', context)