from django.http import Http404, HttpResponse, JsonResponse
import os
import json
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
            for i in range(0, len(wells)):#len(wells)
                allwells += wells[i]
        return_obj = json.loads(allwells)
    return JsonResponse(return_obj)