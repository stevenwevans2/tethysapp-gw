from tethys_sdk.base import TethysAppBase, url_map_maker
from tethys_sdk.app_settings import PersistentStoreDatabaseSetting

class Gw(TethysAppBase):
    """
    Tethys app class for Groundwater Level Mapping Tool.
    """

    name = 'Groundwater Level Mapping Tool'
    index = 'gw:home'
    icon = 'gw/images/gw_logo.png'
    package = 'gw'
    root_url = 'gw'
    color = '#27AE60'
    description = 'This application uses spatial and temporal interpolation of well data to create groundwater level maps and time series.'
    tags = 'Hydrology,Groundwater'
    enable_feedback = False
    feedback_emails = []

    def persistent_store_settings(self):
        #Define Persistent Store Settings.

        ps_settings=(
            PersistentStoreDatabaseSetting(
                name='primary_db',
                description='primary database',
                initializer='gw.model.init_primary_db',
                required=True
            ),
        )

        return ps_settings

    def url_maps(self):
        """
        Add controllers
        """
        UrlMap = url_map_maker(self.root_url)

        url_maps = (
            UrlMap(
                name='home',
                url='gw',
                controller='gw.controllers.home'
            ),
            UrlMap(
                name='region_map',
                url='region_map',
                controller='gw.controllers.region_map'
            ),
            UrlMap(
                name='create_wells',
                url='gw/displaygeojson',
                controller='gw.ajax_controllers.displaygeojson'
            ),
            UrlMap(
                name='load_well_time',
                url='gw/loadjson',
                controller='gw.ajax_controllers.loadjson'
            ),
            UrlMap(
                name='save_json',
                url='gw/savejson',
                controller='gw.ajax_controllers.savejson'
            ),
            UrlMap(
                name='retrieve_wells',
                url='gw/retrieve_Wells',
                controller='gw.model.retrieve_Wells'
            ),

        )

        return url_maps
