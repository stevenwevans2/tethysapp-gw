from tethys_sdk.base import TethysAppBase, url_map_maker
from tethys_sdk.app_settings import PersistentStoreDatabaseSetting, CustomSetting

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
                name='interpolation',
                url='interpolation',
                controller='gw.controllers.interpolation'
            ),
            UrlMap(
                name='addregion_nwis',
                url='addregion_nwis',
                controller='gw.controllers.addregion_nwis'
            ),
            UrlMap(
                name='addregion',
                url='addregion',
                controller='gw.controllers.addregion'
            ),
            UrlMap(
                name='finish_addregion',
                url='gw/finish_addregion',
                controller='gw.ajax_controllers.finish_addregion'
            ),
            UrlMap(
                name='addregion2',
                url='addregion2/{region}',
                controller='gw.controllers.addregion2'
            ),
            UrlMap(
                name='addregion_nwis2',
                url='addregion_nwis2/{region}',
                controller='gw.controllers.addregion_nwis2'
            ),
            UrlMap(
                name='removeregion',
                url='removeregion',
                controller='gw.controllers.removeregion'
            ),
            UrlMap(
                name='deleteregion',
                url='gw/deleteregion',
                controller='gw.ajax_controllers.deleteregion'
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
                name='loaddata',
                url='gw/loaddata',
                controller='gw.ajax_controllers.loaddata'
            ),
            UrlMap(
                name='loadaquiferlist',
                url='gw/loadaquiferlist',
                controller='gw.ajax_controllers.loadaquiferlist'
            ),
            UrlMap(
                name='loadtimelist',
                url='gw/loadtimelist',
                controller='gw.ajax_controllers.loadtimelist'
            ),
            UrlMap(
                name='gettotalvolume',
                url='gw/gettotalvolume',
                controller='gw.ajax_controllers.gettotalvolume'
            ),
            UrlMap(
                name='checktotalvolume',
                url='gw/checktotalvolume',
                controller='gw.ajax_controllers.checktotalvolume'
            ),
            UrlMap(
                name='deletenetcdf',
                url='gw/deletenetcdf',
                controller='gw.ajax_controllers.deletenetcdf'
            ),
            UrlMap(
                name='defaultnetcdf',
                url='gw/defaultnetcdf',
                controller='gw.ajax_controllers.defaultnetcdf'
            ),
            UrlMap(
                name='addoutlier',
                url='gw/addoutlier',
                controller='gw.ajax_controllers.addoutlier'
            ),
            UrlMap(
                name='upload_to_hydroshare',
                url='gw/upload-to-hydroshare',
                controller='gw.ajax_controllers.upload_to_hydroshare'
            ),
            UrlMap(
                name='get_timeseries',
                url='gw/get_timeseries',
                controller='gw.ajax_controllers.get_timeseries'
            ),
            UrlMap(
                name='get_aquifer_wells',
                url='gw/get_aquifer_wells',
                controller='gw.model.get_aquifer_wells'
            ),
        )

        return url_maps

    def custom_settings(self):
        return(
            CustomSetting(
                name='thredds_path',
                type=CustomSetting.TYPE_STRING,
                description="Local file path to the folder used by the Thredds server",
                required=True,
            ),
            CustomSetting(
                name='thredds_url',
                type=CustomSetting.TYPE_STRING,
                description="Url of the thredds server",
                required=True,
            )
        )