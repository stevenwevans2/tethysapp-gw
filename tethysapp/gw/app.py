from tethys_sdk.base import TethysAppBase, url_map_maker


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
    tags = '&quot;Hydrology&quot;,&quot;Groundwater&quot;,&quot;Timeseries&quot;'
    enable_feedback = False
    feedback_emails = []

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

        )

        return url_maps
