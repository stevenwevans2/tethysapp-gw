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
                                        ('Sparta (minor)',27),('West Texas Bolsons (minor)',2),('Woodbine (minor)',29),('Yegua Jackson (minor)',31),('NA',22),('All',32)]
                               )

    required_data=RangeSlider(display_text='Minimum Number of Data Points per Well',
                      name='required_data',
                      min=0,
                      max=50,
                      initial=0,
                      step=1
    )

    calcbutton = Button(
        display_text='Display Wells',
        name='calcbutton',

        attributes={
            'data-toggle': 'tooltip',
            'data-placement': 'top',
            'title': 'Display Wells',
            'onclick':'displaywells()'
        },
    )

    clearbutton = Button(
        display_text='Clear Wells',
        name='clearbutton',

        attributes={
            'data-toggle': 'tooltip',
            'data-placement': 'top',
            'title': 'Clear Wells',
            'onclick': 'clearwells()'
        },
    )

    interpolatebutton=Button(
        display_text="Show Water Levels",
        name='interpolationbutton',

        attributes={
            'data-toggle': 'tooltip',
            'data-placement': 'top',
            'title':'Interpolate water levels',
            'onclick':'showraster()'

        }
    )

    clearrasterbutton=Button(
        display_text='Clear Water Levels',
        name='clearrasterbutton',

        attributes={
            'data-toggle': 'tooltip',
            'data-placement': 'top',
            'title': 'Clear Water Levels',
            'onclick': 'clearwaterlevels()'
        }
    )

    context = {
        "select_aquifer":select_aquifer,
        "required_data": required_data,
        "calcbutton": calcbutton,
        "clearbutton":clearbutton,
        'interpolatebutton':interpolatebutton,
        'clearrasterbutton':clearrasterbutton,
    }

    return render(request, 'gw/region_map.html', context)