from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from tethys_sdk.gizmos import Button, SelectInput

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
                                options=[('',''),('Region 1', 0), ('Region 2', 1), ('Region 3', 2),
                                         ('Region 4', 3), ('Region 5', 4), ('Region 6', 5),
                                         ('Region 7', 6), ('Region 8', 7), ('Region 9', 8),]
                                )


    context = {
        "select_region": select_region
    }

    return render(request, 'gw/region_map.html', context)