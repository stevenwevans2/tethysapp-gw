//Get a CSRF cookie for request
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

//find if method is csrf safe
function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

//add csrf token to appropriate ajax requests
$(function() {
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", getCookie("csrftoken"));
            }
        }
    });
}); //document ready

//This function is called when the interpolation method or the data type is adjusted on the app Regional Map page.
//The function clears the displayed Raster layers and then adds new raster layers for the specified interpolation and data type.
//The function calls the getLayerMinMax function to determine the bounds of the new raster and adjust the symbology and legend accordingly.
function changeWMS(){
    var region_number=$("#select_aquifer").find('option:selected').val();
    region_number=Number(region_number);
    var aquifers=['Hueco Bolson','West Texas Bolsons','Pecos Valley','Seymour','Brazos River Alluvium','Blaine','Blossom','Bone Spring-Victorio Peak','Capitan Reef Complex','Carrizo','Edwards','Edwards-Trinity-High Plains','Edwards-Trinity','Ellenburger-San-Aba','Gulf Coast','Hickory','Igneous','Maratho','Marble Falls','Nacatoch','Ogallala','None','Rita Blanca','Queen City','Rustler','Dockum','Sparta','Trinity','Woodbine','Lipan','Yegua Jackson','Texas'];    var aquifer=aquifers[region_number-1];
    var name=aquifers[region_number-1];
    name=name.replace(/ /g,"_");
    clearwaterlevels();
    var interpolation_type=$("#select_interpolation").find('option:selected').val();
    var testWMS="https://tethys.byu.edu/thredds/wms/testAll/groundwater/"+interpolation_type+"/"+name+".nc";
    //var testWMS="http://localhost:8080/thredds/wms/testAll/groundwater/"+interpolation_type+"/"+name+".nc";
    var colormin=$("#col_min").val();
    var colormax=$("#col_max").val();
    var opac = $("#opacity_val").val();
    var wmsLayer=$("#select_view").find('option:selected').val();


    var testLayer = L.tileLayer.wms(testWMS, {
        layers: wmsLayer,
        format: 'image/png',
        transparent: true,
        opacity:opac,
        styles:'boxfill/grace',
        colorscalerange:colormin+','+colormax,
        attribution: '<a href="https://www.pik-potsdam.de/">PIK</a>'
    });
    var contourLayer=L.tileLayer.wms(testWMS,{
        layers: wmsLayer,
        format: 'image/png',
        transparent: true,
        colorscalerange:colormin+','+colormax,
        styles:'contour/grace',
        attribution: '<a href="https://www.pik-potsdam.de/">PIK</a>'
    });
    var testTimeLayer=L.timeDimension.layer.wms(testLayer);
    getLayerMinMax(wmsLayer,testLayer,contourLayer,testWMS,addLegend,testTimeLayer);
}

//This function is called when the min, max, and opacity boxes are adjusted on the app Regional Map page. This function clears the netCDF rasters and legend
// and then reloads the rasters and legend from the Thredds Server with the specified changes to the symbology.
function updateWMS(){
    var region_number=$("#select_aquifer").find('option:selected').val();
    region_number=Number(region_number);
    var aquifers=['Hueco Bolson','West Texas Bolsons','Pecos Valley','Seymour','Brazos River Alluvium','Blaine','Blossom','Bone Spring-Victorio Peak','Capitan Reef Complex','Carrizo','Edwards','Edwards-Trinity-High Plains','Edwards-Trinity','Ellenburger-San-Aba','Gulf Coast','Hickory','Igneous','Maratho','Marble Falls','Nacatoch','Ogallala','None','Rita Blanca','Queen City','Rustler','Dockum','Sparta','Trinity','Woodbine','Lipan','Yegua Jackson','Texas'];    var aquifer=aquifers[region_number-1];
    var name=aquifers[region_number-1];
    name=name.replace(/ /g,"_");
    clearwaterlevels();
    var interpolation_type=$("#select_interpolation").find('option:selected').val();
    var testWMS="https://tethys.byu.edu/thredds/wms/testAll/groundwater/"+interpolation_type+"/"+name+".nc";
    //var testWMS="http://localhost:8080/thredds/wms/testAll/groundwater/"+interpolation_type+"/"+name+".nc";
    var colormin=$("#col_min").val();
    var colormax=$("#col_max").val();
    var opac = $("#opacity_val").val();
    var wmsLayer=$("#select_view").find('option:selected').val();


    var testLayer = L.tileLayer.wms(testWMS, {
        layers: wmsLayer,
        format: 'image/png',
        transparent: true,
        opacity:opac,
        styles:'boxfill/grace',
        colorscalerange:colormin+','+colormax,
        attribution: '<a href="https://www.pik-potsdam.de/">PIK</a>'
    });
    var contourLayer=L.tileLayer.wms(testWMS,{
        layers: wmsLayer,
        format: 'image/png',
        transparent: true,
        colorscalerange:colormin+','+colormax,
        styles:'contour/grace',
        attribution: '<a href="https://www.pik-potsdam.de/">PIK</a>'
    });
    var testTimeLayer=L.timeDimension.layer.wms(testLayer);
    testLegend.onAdd = function(map) {
                    var src=testWMS+"?REQUEST=GetLegendGraphic&LAYER="+wmsLayer+"&PALETTE=grace&COLORSCALERANGE="+colormin+","+colormax;
                    var div = L.DomUtil.create('div', 'info legend');
                    div.innerHTML +=
                        '<img src="' + src + '" alt="legend">';
                    return div;
                };
    testLegend.addTo(map);
    var contourTimeLayer=L.timeDimension.layer.wms(contourLayer);
    interpolation_group.addLayer(testTimeLayer);
    interpolation_group.addTo(map);
    contour_group.addLayer(contourTimeLayer);
}

//This function is called by the getLayerMinMax function and adds a legend to the map as well as contour symbology
var addLegend=function(testWMS,contourLayer, testLayer,colormin,colormax,layer,testTimeLayer){
    testLegend.onAdd = function(map) {
                    var src=testWMS+"?REQUEST=GetLegendGraphic&LAYER="+layer+"&PALETTE=grace&COLORSCALERANGE="+colormin+","+colormax;
                    var div = L.DomUtil.create('div', 'info legend');
                    div.innerHTML +=
                        '<img src="' + src + '" alt="legend">';
                    return div;
                };
    testLegend.addTo(map);
    var contourTimeLayer=L.timeDimension.layer.wms(contourLayer);
    interpolation_group.addLayer(testTimeLayer);
    interpolation_group.addTo(map);
    contour_group.addLayer(contourTimeLayer);
    toggle.removeLayer(contour_group, "Contours");
    toggle.addOverlay(contour_group, "Contours");
//    map.on('overlayremove',function(eventLayer){
//        if (eventLayer.name=='Contours'){
//            map.removeControl(testLegend);
//        }
//    })
//    map.on('overlayadd',function(eventLayer){
//        if (eventLayer.name=='Contours'){
//            map.addControl(testLegend);
//        }
//    })
}

//This function determines the min and max values of a netCDF dataset on the Thredds server and
//updates the symbology of the rasters and calls the addLegend function
var getLayerMinMax = function(layer,testLayer,contourWMS, testWMS, callback,testTimeLayer) {
    var url = testWMS + '?service=WMS&version=1.1.1&request=GetMetadata&item=minmax';
    url = url + '&layers=' + testLayer.options.layers;
    url = url + '&srs=EPSG:4326';
    //size is a global variable obtained from var size = map.getSize();
    url = url + '&BBox=' + bounds;
    url = url + '&height=' + size.y;
    url = url + '&width=' + size.x;

    var oReq = new XMLHttpRequest();
    oReq.addEventListener("load", (function(xhr) {
        var response = xhr.currentTarget.response;
        var data = JSON.parse(response);
        var range = data.max - data.min;
        var min = Math.round(data.min/100.0)*100;
        var max = Math.round(data.max/100.0)*100;
       
        if (min==max){
            min-=50;
            max+=50;
        }
        if (min>data.min){
            min-=50;
        }
        if (max<data.max){
            max+=50;
        }
        if (layer=="drawdown"){
            max=min*-1;
        }
        testLayer.options.colorscalerange = min + "," + max;
        testLayer.wmsParams.colorscalerange = min + "," + max;
        contourWMS.options.colorscalerange = min + "," + max;
        contourWMS.wmsParams.colorscalerange = min + "," + max;
	    document.getElementById("col_min").value=min;
        document.getElementById("col_max").value=max;

        if (callback != undefined) {
            callback(testWMS,contourWMS,testLayer,min,max,layer,testTimeLayer);
        }
    }));
    oReq.open("GET", url);
    oReq.send();
};



var regioncenter=[31.2,-100.0];
var mychart=[]
//add a map to the html div "map" with time dimension capabilities. Times are currently hard coded, but will need to be changed as new GRACE data comes
var map = L.map('map', {
    crs: L.CRS.EPSG4326,
    zoom: 5,
    fullscreenControl: true,
    timeDimension: true,
    timeDimensionOptions:{
			 times:"1949-12-30T00:00:00.000Z,1954-12-30T00:00:00.000Z,1959-12-30T00:00:00.000Z,1964-12-30T00:00:00.000Z,1969-12-30T00:00:00.000Z,1974-12-30T00:00:00.000Z,1979-12-30T00:00:00.000Z,1984-12-30T00:00:00.000Z,1989-12-30T00:00:00.000Z,1994-12-30T00:00:00.000Z,1999-12-30T00:00:00.000Z,2004-12-30T00:00:00.000Z,2009-12-30T00:00:00.000Z,2014-12-30T00:00:00.000Z",
    },
    timeDimensionControl: true,
    timeDimensionControlOptions:{
        loopButton:true,
        playerOptions:{
            loop:true,
        }
    },
    center: regioncenter,
});

//These two variables are global variables specifying the size and bounds of the overall region. This is used in the getLayerMinMax function.
var size= map.getSize();
var bounds=map.getBounds().toBBoxString();
//add the background imagery
var wmsLayer = L.tileLayer.wms('https://demo.boundlessgeo.com/geoserver/ows?', {
    //layers: 'nasa:bluemarble'
    layers:'ne:NE1_HR_LC_SR_W_DR'
}).addTo(map);



//This ajax controller loads the JSON file for the Texas State boundary and adds it to the map
var geolayer = 'Texas_State_Boundary.json';
$.ajax({
    url: '/apps/gw/displaygeojson/',
    type: 'GET',
    data: {'geolayer':geolayer},
    contentType: 'application/json',
    error: function (status) {

    }, success: function (response) {
        texasboundary=response.features;
        texasborder=L.geoJSON(texasboundary,{
            color:"red",
            weight:1,
            fillOpacity:0.0
        })
        texasborder.addTo(map)
    }
});

var testLegend = L.control({
    position: 'bottomright'
});

var well_group=L.layerGroup();
var aquifer_group=L.layerGroup();
var interpolation_group=L.layerGroup();
var contour_group=L.layerGroup();
var overlayMaps={

    };
var toggle=L.control.layers(null,overlayMaps).addTo(map);

//This function is called when the region is changed in the Select Aquifer dropdown or the Update Region button is clicked
function change_region(){
    document.getElementById('chart').innerHTML='';
    var wait_text = "<strong>Loading Data...</strong><br>" +
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src='/static/gw/images/loading.gif'>";
    document.getElementById('waiting_output').innerHTML = wait_text;
    clearwells();
    clearwaterlevels();

    var region_number=$("#select_aquifer").find('option:selected').val();
    region_number=Number(region_number);

    displaygeojson(region_number,displayallwells);
};

function clearwells(){
    well_group.clearLayers();
    aquifer_group.clearLayers();
    document.getElementById("chart").innerHTML="";
}

function clearwaterlevels(){
    interpolation_group.clearLayers();
    contour_group.clearLayers();
    testLegend.remove();
}


//This is the new function that I am working on
function displaygeojson(region_number, wellfunction) {

    var aquifers=['HUECO_BOLSON','WEST TEXAS BOLSONS','PECOS VALLEY','SEYMOUR','BRAZOS RIVER ALLUVIUM','BLAINE','BLOSSOM','BONE SPRING-VICTORIO PEAK','CAPITAN REEF COMPLEX','CARRIZO','EDWARDS','EDWARDS-TRINITY (HIGH PLAINS)','EDWARDS-TRINITY','ELLENBURGER-SAN SABA','GULF_COAST','HICKORY','IGNEOUS','MARATHON','MARBLE FALLS','NACATOCH','OGALLALA','NONE','RITA BLANCA','QUEEN CITY','RUSTLER','DOCKUM','SPARTA','TRINITY','WOODBINE','LIPAN','YEGUA JACKSON'];
    var geolayer=aquifers[region_number-1];

    //calls the loadjson ajax controller to open the aquifer shapefiles and return the appropriate geoJSON object for the aquifer
    $.ajax({
    url: '/apps/gw/loadjson/',
    type: 'GET',
    data: {'geolayer':geolayer},
    contentType: 'application/json',
    error: function (status) {

    }, success: function (response) {
        AquiferShape=response['data'];

        var aquifer_center=[];

        //find the center of the aquifer if an aquifer is selected. Add the aquifer to the map and zoom and pan to the center
        if (AquiferShape[0]){
            var AquiferLayer=L.geoJSON(AquiferShape[0],{
                onEachFeature: function (feature, layer) {
                    feature.properties.bounds_calculated = layer.getBounds();
                    var latcenter=(feature.properties.bounds_calculated._northEast.lat+feature.properties.bounds_calculated._southWest.lat)/2;
                    var loncenter=(feature.properties.bounds_calculated._northEast.lng+feature.properties.bounds_calculated._southWest.lng)/2;
                    aquifer_center=[latcenter,loncenter];
                },
                fillOpacity:0.0,
                weight:1,
            }
            );
            map.setView(aquifer_center,5.5);
            aquifer_group.addLayer(AquiferLayer);
        }
        //if no aquifer is loaded, zoom to the Texas boundaries
        else{
            map.setView(regioncenter,5);
        }

        aquifer_group.addTo(map);

        min_num=$("#required_data").find('option:selected').val();
        min_num=Number(min_num);
        id=region_number;
        var aquifers=['Hueco Bolson','West Texas Bolsons','Pecos Valley','Seymour','Brazos River Alluvium','Blaine','Blossom','Bone Spring-Victorio Peak','Capitan Reef Complex','Carrizo','Edwards','Edwards-Trinity-High Plains','Edwards-Trinity','Ellenburger-San-Aba','Gulf Coast','Hickory','Igneous','Maratho','Marble Falls','Nacatoch','Ogallala','None','Rita Blanca','Queen City','Rustler','Dockum','Sparta','Trinity','Woodbine','Lipan','Yegua Jackson','Texas'];
        var name=aquifers[id-1];
        name=name.replace(/ /g,"_");
        var interpolation_type=$("#select_interpolation").find('option:selected').val();
            $.ajax({
                url: '/apps/gw/loaddata/',
                type: 'GET',
                data: {'id':id,'min_num':min_num, 'name':name, 'interpolation_type':interpolation_type},
                contentType: 'application/json',
                error: function (status) {

                }, success: function (response) {
                    var well_points=response['data'];//.features;

                    //calls displayallwells
                    wellfunction(region_number, well_points,min_num);

                    overlayMaps={
                        "Aquifer Boundary":aquifer_group,
                        "Wells":well_group,
                        "Water Table Surface":interpolation_group,
                    };

                    toggle.remove();
                    toggle=L.control.layers(null,overlayMaps).addTo(map);
                }
            })
        }
    })
}

function displayallwells(region_number,well_points,required){

	var colors=['blue','red','yellow','green','orange','purple'];
    var aquifers=['Hueco Bolson','West Texas Bolsons','Pecos Valley','Seymour','Brazos River Alluvium','Blaine','Blossom','Bone Spring-Victorio Peak','Capitan Reef Complex','Carrizo','Edwards','Edwards-Trinity-High Plains','Edwards-Trinity','Ellenburger-San-Aba','Gulf Coast','Hickory','Igneous','Maratho','Marble Falls','Nacatoch','Ogallala','None','Rita Blanca','Queen City','Rustler','Dockum','Sparta','Trinity','Woodbine','Lipan','Yegua Jackson','Texas'];
    num=region_number%6;
    var color=colors[num];
    var aquifer=aquifers[region_number-1];
    var name =aquifer;
    var points='{"type":"FeatureCollection","features":[]}';
    points=JSON.parse(points);
    if (required>0){
        for (i=0;i<well_points.features.length;i++){
            if (well_points.features[i].TsTime){
                if (well_points.features[i].TsTime.length>required){
                    points.features.push(well_points.features[i]);
                }
            }
        }
    }
    else{
        points=well_points;
    }

    name=name.replace(/ /g,"_")
    var interpolation_type=$("#select_interpolation").find('option:selected').val();
    var testWMS="https://tethys.byu.edu/thredds/wms/testAll/groundwater/"+interpolation_type+"/"+name+".nc";
    //var testWMS="http://localhost:8080/thredds/wms/testAll/groundwater/"+interpolation_type+"/"+name+".nc";
    var colormin=-500;
    var colormax=0;
    if (region_number==28){
          colormin=-1000;
    }
    var wmsLayer=$("#select_view").find('option:selected').val();

    var testLayer = L.tileLayer.wms(testWMS, {
        layers: wmsLayer,
        format: 'image/png',
        transparent: true,
        opacity:0.5,
        styles:'boxfill/grace',
        colorscalerange:colormin+','+colormax,
        attribution: '<a href="https://www.pik-potsdam.de/">PIK</a>'
    });
    var contourLayer=L.tileLayer.wms(testWMS,{
        layers: wmsLayer,
        format: 'image/png',
        transparent: true,
        colorscalerange:colormin+','+colormax,
        styles:'contour/grace',
        attribution: '<a href="https://www.pik-potsdam.de/">PIK</a>'
    });
    var testTimeLayer=L.timeDimension.layer.wms(testLayer);

    getLayerMinMax(wmsLayer,testLayer,contourLayer,testWMS,addLegend,testTimeLayer);


    var well_layer=L.geoJSON(points,{
        onEachFeature: function (feature, layer){
            var popup_content="Hydro ID: "+feature.properties.HydroID;
            var type=feature.properties.FType;
            if (type=="W"){
                type="Water Withdrawal";
            }
            else if (type=="P"){
                type="Petroleum";
            }
            else if (type=="O"){
                type="Observation";
            }
            else if (type=="M"){
                type="Mine";
            }
            popup_content+="<br>"+"Well Type: "+type;
            popup_content+="<br>"+"Aquifer: "+aquifer;
            popup_content+="<br>"+"Elevation: "+feature.properties.LandElev + " feet";
            popup_content+="<br>"+"Well Depth: "+feature.properties.WellDepth + " feet";
            var data=[];
        if (feature.TsTime){
            for (i=0;i<feature.TsTime.length;i++){
                data[i]=[feature.TsTime[i]*1000,feature.TsValue[i]]
            }
        }
            //make a high charts
            layer.on({
                click: function showResultsInDiv() {
                    mychart=Highcharts.chart('chart',{
                        chart: {
                            type: 'spline'
                        },
                        title: {
                            text: 'Depth to Water Table at Well ' +feature.properties.HydroID+", located at "+feature.geometry.coordinates
                        },
                        xAxis: {
                            type: 'datetime',

                            title: {
                                text: 'Date'
                            },
                plotLines: [{
                        color: 'red',
                        dashStyle: 'solid',
                        value: new Date(testTimeLayer._timeDimension.getCurrentTime()),
                        width: 2,
                        id: 'pbCurrentTime'
                    }]
                        },
                        yAxis:{
                            title: {
                                text: 'Depth to Water Table (ft)'}
                        },
                        series: [{
                            data: data,
                            name: "Depth to Water Table (ft)"

                        }]
                    });
                testTimeLayer._timeDimension.on('timeload', (function() {
                    if (!mychart){
                        return;
                    }
                    mychart.xAxis[0].removePlotBand("pbCurrentTime");
                    mychart.xAxis[0].addPlotLine({
                        color: 'red',
                        dashStyle: 'solid',
                        value: new Date(testTimeLayer._timeDimension.getCurrentTime()),
                        width: 2,
                        id: 'pbCurrentTime'
                    });
                        }).bind(this));
                }

            });

            layer.bindPopup(popup_content);
        },
        pointToLayer:function(geoJsonPoint, latlng){
            return L.circleMarker(latlng,{radius:1, color:color});
        }
    });
    well_group.addLayer(well_layer)

    well_group.addTo(map);

    document.getElementById('waiting_output').innerHTML = '';
}








