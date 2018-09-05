var thredds_url="https://tethys.byu.edu/thredds/wms/testAll/groundwater/";
//var thredds_url = "http://localhost:8080/thredds/wms/testAll/groundwater/";

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

    var name=$("#available_dates").find('option:selected').val();
    name=name.replace(/ /g,"_");
    clearwaterlevels();
    var interpolation_type=$("#select_interpolation").find('option:selected').val();
    var region=$("#select_region").find('option:selected').val();


    var testWMS=thredds_url+region+'/'+interpolation_type+'/'+name;

    var colormin=$("#col_min").val();
    var colormax=$("#col_max").val();
    var opac = $("#opacity_val").val();
    var wmsLayer=$("#select_view").find('option:selected').val();
    var palette=$("#select_symbology").find('option:selected').val();


    var testLayer = L.tileLayer.wms(testWMS, {
        layers: wmsLayer,
        format: 'image/png',
        transparent: true,
        opacity:opac,
        styles:'boxfill/'+palette,
        colorscalerange:colormin+','+colormax,
        attribution: '<a href="https://ceen.et.byu.edu/">BYU</a>'
    });
    var contourLayer=L.tileLayer.wms(testWMS,{
        layers: wmsLayer,
        crs: L.CRS.EPSG4326,
        format: 'image/png',
        transparent: true,
        colorscalerange:colormin+','+colormax,
        styles:'contour/'+palette,
        attribution: '<a href="https://ceen.et.byu.edu/">BYU</a>'
    });
    var testTimeLayer=L.timeDimension.layer.wms(testLayer, {
        cache:50
    });

    var url=thredds_url+region+'/'+interpolation_type+'/'+name+"?service=WMS&version=1.3.0&request=GetCapabilities";

    var oReq = new XMLHttpRequest();
    oReq.addEventListener("load", (function(xhr) {
        var response = xhr.currentTarget.response;
        pos1=response.indexOf("-12-30T00:00:00.000Z")+1
        pos2=response.indexOf("-12-30T00:00:00.000Z",pos1)-4
        pos3=response.indexOf(">",pos2)
        pos4=response.indexOf("<",pos2)
        pos3=Math.min(pos3,pos4)
        substring=response.substring(pos2,pos3)
        map.timeDimension.setAvailableTimes(substring, "replace");
        //document.getElementById('waiting_output').innerHTML = '';
        getLayerMinMax(wmsLayer,testLayer,contourLayer,testWMS,addLegend,testTimeLayer);
    }));
    oReq.open("GET", url);
    oReq.send();

    //getLayerMinMax(wmsLayer,testLayer,contourLayer,testWMS,addLegend,testTimeLayer);
}

//This function is called when the min, max, and opacity boxes are adjusted on the app Regional Map page. This function clears the netCDF rasters and legend
// and then reloads the rasters and legend from the Thredds Server with the specified changes to the symbology.
function updateWMS(){
    var name=$("#available_dates").find('option:selected').val();
    name=name.replace(/ /g,"_");
    clearwaterlevels();
    var interpolation_type=$("#select_interpolation").find('option:selected').val();
    var region=$("#select_region").find('option:selected').val();

    var testWMS=thredds_url+region+'/'+interpolation_type+'/'+name;

    var colormin=$("#col_min").val();
    var colormax=$("#col_max").val();
    var opac = $("#opacity_val").val();
    var wmsLayer=$("#select_view").find('option:selected').val();
    var palette=$("#select_symbology").find('option:selected').val();

    var testLayer = L.tileLayer.wms(testWMS, {
        layers: wmsLayer,
        format: 'image/png',
        transparent: true,
        opacity:opac,
        styles:'boxfill/'+palette,
        colorscalerange:colormin+','+colormax,
        attribution: '<a href="https://ceen.et.byu.edu/">BYU</a>'
    });
    var contourLayer=L.tileLayer.wms(testWMS,{
        layers: wmsLayer,
        crs: L.CRS.EPSG4326,
        format: 'image/png',
        transparent: true,
        colorscalerange:colormin+','+colormax,
        styles:'contour/'+palette,
        attribution: '<a href="https://ceen.et.byu.edu/">BYU</a>'
    });
    var testTimeLayer=L.timeDimension.layer.wms(testLayer,{
        cache:50
    });

    testLegend.onAdd = function(map) {
                    var src=testWMS+"?REQUEST=GetLegendGraphic&LAYER="+wmsLayer+"&PALETTE="+palette+"&COLORSCALERANGE="+colormin+","+colormax;
                    var div = L.DomUtil.create('div', 'info legend');
                    div.innerHTML +=
                        '<img src="' + src + '" alt="legend">';
                    return div;
                };
    testLegend.addTo(map);
    var contourTimeLayer=L.timeDimension.layer.wms(contourLayer,{
        cache:50
    });
    interpolation_group.addLayer(testTimeLayer);
    contour_group.addLayer(contourTimeLayer);

    var url=thredds_url+region+'/'+interpolation_type+'/'+name+"?service=WMS&version=1.3.0&request=GetCapabilities";

    var oReq = new XMLHttpRequest();
    oReq.addEventListener("load", (function(xhr) {
        var response = xhr.currentTarget.response;
        pos1=response.indexOf("-12-30T00:00:00.000Z")+1
        pos2=response.indexOf("-12-30T00:00:00.000Z",pos1)-4
        pos3=response.indexOf(">",pos2)
        pos4=response.indexOf("<",pos2)
        pos3=Math.min(pos3,pos4)
        substring=response.substring(pos2,pos3)
        map.timeDimension.setAvailableTimes(substring, "replace");
        document.getElementById('waiting_output').innerHTML = '';
    }));
    oReq.open("GET", url);
    oReq.send();
}

//This function is called by the getLayerMinMax function and adds a legend to the map as well as contour symbology
var addLegend=function(testWMS,contourLayer, testLayer,colormin,colormax,layer,testTimeLayer){
    var palette=$("#select_symbology").find('option:selected').val();
    testLegend.onAdd = function(map) {
                    var src=testWMS+"?REQUEST=GetLegendGraphic&LAYER="+layer+"&PALETTE="+palette+"&COLORSCALERANGE="+colormin+","+colormax;
                    var div = L.DomUtil.create('div', 'info legend');
                    div.innerHTML +=
                        '<img src="' + src + '" alt="legend">';
                    return div;
                };
    testLegend.addTo(map);
    var contourTimeLayer=L.timeDimension.layer.wms(contourLayer,{
        cache:50
    });
    interpolation_group.addLayer(testTimeLayer);
    interpolation_group.addTo(map);
    contour_group.addLayer(contourTimeLayer);
    contour_group.addTo(map);
    toggle.removeLayer(contour_group, "Contours");
    toggle.addOverlay(contour_group, "Contours");
}

//This function determines the min and max values of a netCDF dataset on the Thredds server and
//updates the symbology of the rasters and calls the addLegend function
var getLayerMinMax = function(layer,testLayer,contourWMS, testWMS, callback,testTimeLayer) {
    var url = testWMS + '?service=WMS&version=1.1.1&request=GetMetadata&item=minmax';
    url = url + '&layers=' + testLayer.options.layers;
    url = url + '&srs=EPSG:4326';//4326
    //size is a global variable obtained from var size = map.getSize();
    bounds=region_group.getBounds().toBBoxString();

    url = url + '&BBox=' + bounds//"-360.0,-90.0,360.0,90.0";//bounds
    url = url + '&height=' + 1000;//size.y
    url = url + '&width=' + 1000;//size.x

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
//        if (layer=="drawdown"){
//            max=min*-1;
//        }
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


document.getElementById('buttons').style.display="none"
var regioncenter=[31.2,-100.0];
var mychart=[]
//add a map to the html div "map" with time dimension capabilities. Times are currently hard coded, but will need to be changed as new GRACE data comes
var map = L.map('map', {
    crs: L.CRS.EPSG3857,//4326
    zoom: 5,
    fullscreenControl: true,
    timeDimension: true,
//    timeDimensionOptions:{
//			 times:"1949-12-30T00:00:00.000Z,1954-12-30T00:00:00.000Z,1959-12-30T00:00:00.000Z,1964-12-30T00:00:00.000Z,1969-12-30T00:00:00.000Z,1974-12-30T00:00:00.000Z,1979-12-30T00:00:00.000Z,1984-12-30T00:00:00.000Z,1989-12-30T00:00:00.000Z,1994-12-30T00:00:00.000Z,1999-12-30T00:00:00.000Z,2004-12-30T00:00:00.000Z,2009-12-30T00:00:00.000Z,2014-12-30T00:00:00.000Z",
//    },
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
var region=$("#select_region").find('option:selected').val();
var size= map.getSize();
var bounds=map.getBounds().toBBoxString();
//add the background imagery
//var wmsLayer = L.tileLayer.wms('https://demo.boundlessgeo.com/geoserver/ows?', {
//    //layers: 'nasa:bluemarble'
//    layers:'ne:NE1_HR_LC_SR_W_DR'
//}).addTo(map);
var StreetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
	maxZoom: 19,
	attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);
var TopoMap = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
	maxZoom: 17,
	attribution: 'Map data: &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
});

var region_group=L.featureGroup();
var well_group=L.featureGroup();
var aquifer_group=L.featureGroup();
var minor_group=L.featureGroup();
var major_group=L.featureGroup();
var interpolation_group=L.layerGroup();
var contour_group=L.layerGroup();
var overlayMaps={

};
var toggle=L.control.layers(null,overlayMaps).addTo(map);

//This ajax controller loads the JSON file for the Texas State boundary and adds it to the map
var geolayer = region+'_State_Boundary.json';
var region=$("#select_region").find('option:selected').val();
$.ajax({
    url: '/apps/gw/displaygeojson/',
    type: 'GET',
    data: {'geolayer':geolayer,'region':region},
    contentType: 'application/json',
    error: function (status) {

    }, success: function (response) {
        texasboundary=response['state'].features;
        texasborder=L.geoJSON(texasboundary,{
            color:"red",
            weight:1,
            fillOpacity:0.0
        })
        region_group.addLayer(texasborder);
        region_group.addTo(map);
        if (response['major']){
            major=response['major'];
            majoraquifers=L.geoJSON(major,{
                weight:1,
                fillOpacity:0.2,
                onEachFeature: function (feature, layer){
                    //map.doubleClickZoom.disable();
                    tooltip_content="Major Aquifer: "+feature.properties.Name;
                    layer.bindTooltip(tooltip_content,{sticky:true});
                    layer.on({
                        click: function jumpaquifer(){
                            $("#select_aquifer").val(feature.properties.Id);
                            document.getElementById("select2-select_aquifer-container").innerHTML=$("#select_aquifer").find('option:selected').text();
                            list_dates(2)
                        }
                    });

                }
            });
            majoraquifers.addTo(major_group);
            major_group.addTo(map);
            toggle.addOverlay(major_group, "Major Aquifers");
        }
        if (response['minor']){
            minor=response['minor'];
            minoraquifers=L.geoJSON(minor,{
                color:'green',
                weight:1,
                fillOpacity:0.2,
                onEachFeature: function (feature, layer){
                    tooltip_content="Minor Aquifer: "+feature.properties.Name;
                    layer.bindTooltip(tooltip_content,{sticky:true});
                    layer.on({
                        click: function jumpaquifer(){
                            $("#select_aquifer").val(feature.properties.Id);
                            document.getElementById("select2-select_aquifer-container").innerHTML=$("#select_aquifer").find('option:selected').text();
                            list_dates(2)
                        }
                    });

                }
            });
            minoraquifers.addTo(minor_group);
            minor_group.addTo(map);
            toggle.addOverlay(minor_group, "Minor Aquifers");
        }
    }
});

var testLegend = L.control({
    position: 'bottomright'
});

//This function is called when the amount of wells visible changes
function change_filter(){
    if ($("#select_aquifer").find('option:selected').val()!=9999){
        change_aquifer();
    }
}

//This function is called when the aquifer is changed in the Select Aquifer dropdown.
function change_aquifer(){
    $("#select_aquifer option[value=9999]").remove();
    document.getElementById('chart').innerHTML='';
    var wait_text = "<strong>Loading Data...</strong><br>" +
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src='/static/gw/images/loading.gif'>";
    document.getElementById('waiting_output').innerHTML = wait_text;
    clearwells();
    clearwaterlevels();

    aquifer_number=$("#select_aquifer").find('option:selected').val();
    aq_name=$("#available_dates").find('option:selected').val();
    if (typeof aq_name=="undefined"){
        document.getElementById('waiting_output').innerHTML = '';
        alert("The selected aquifer does not have any associated interpolation rasters .");
        return
    }
    aquifer_number=Number(aquifer_number);
    region=$("#select_region").find('option:selected').val();
    displaygeojson(aquifer_number,displayallwells);
};

function clearwells(){
    well_group.clearLayers();
    aquifer_group.clearLayers();
    document.getElementById("chart").innerHTML="";
    minor_group.clearLayers();
    major_group.clearLayers();
}

function clearwaterlevels(){
    interpolation_group.clearLayers();
    contour_group.clearLayers();
    testLegend.remove();
}

//This is the new function that I am working on
function displaygeojson(aquifer_number, displayallwells) {

    var region=$("#select_region").find('option:selected').val();
    //calls the loadjson ajax controller to open the aquifer shapefiles and return the appropriate geoJSON object for the aquifer
    $.ajax({
    url: '/apps/gw/loadjson/',
    type: 'GET',
    data: {'aquifer_number':aquifer_number,'region':region},
    contentType: 'application/json',
    error: function (status) {

    }, success: function (response) {
        AquiferShape=response['data'];
        myaquifer=response['aquifer'];
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
            //map.setView(aquifer_center,5.5);
            aquifer_group.addLayer(AquiferLayer);
            map.fitBounds(aquifer_group.getBounds());
        }
        //if no aquifer is loaded, zoom to the Texas boundaries
        else{
            //map.setView(regioncenter,5);
            map.fitBounds(region_group.getBounds());
        }

        aquifer_group.addTo(map);

        min_num=$("#required_data").find('option:selected').val();
        min_num=Number(min_num);
        id=aquifer_number;
        var name=myaquifer.Name;
        name=name.replace(/ /g,"_");

        var interpolation_type=$("#select_interpolation").find('option:selected').val();
        var region=$("#select_region").find('option:selected').val();

            $.ajax({
                url: '/apps/gw/loaddata/',
                type: 'GET',
                data: {'id':id, 'interpolation_type':interpolation_type,'region':region, 'make_default':0, 'from_wizard':0},
                contentType: 'application/json',
                error: function (status) {

                }, success: function (response) {
                    var well_points=response['data'];//.features;

                    //calls displayallwells
                    displayallwells(aquifer_number, well_points,min_num);

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

function displayallwells(aquifer_number,well_points,required){

    var color='blue';
    var aquifer=$("#select_aquifer").find('option:selected').text();
    var name=$("#available_dates").find('option:selected').val();

    var points='{"type":"FeatureCollection","features":[]}';
    points=JSON.parse(points);
    if (required>0){
        for (i=0;i<well_points.features.length;i++){
            if (well_points.features[i].TsTime){
                if (well_points.features[i].TsTime.length>=required){
                    points.features.push(well_points.features[i]);
                }
            }
        }
    }
    else{
        points=well_points;
    }

    name=name.replace(/ /g,"_");
    var interpolation_type=$("#select_interpolation").find('option:selected').val();
    var region=$("#select_region").find('option:selected').val();

    var testWMS=thredds_url+region+'/'+interpolation_type+'/'+name;

    var colormin=-500;
    var colormax=0;
    if (aquifer_number==28){
          colormin=-1000;
    }
    var wmsLayer=$("#select_view").find('option:selected').val();
    var palette=$("#select_symbology").find('option:selected').val();

    var testLayer = L.tileLayer.wms(testWMS, {
        layers: wmsLayer,
        format: 'image/png',
        transparent: true,
        opacity:0.7,
        styles:'boxfill/'+palette,
        colorscalerange:colormin+','+colormax,
        attribution: '<a href="https://ceen.et.byu.edu/>BYU</a>'
    });
    var contourLayer=L.tileLayer.wms(testWMS,{
        layers: wmsLayer,
        crs: L.CRS.EPSG4326,
        format: 'image/png',
        transparent: true,
        colorscalerange:colormin+','+colormax,
        styles:'contour/'+palette,
        attribution: '<a href="https://ceen.et.byu.edu/">BYU</a>'
    });
    var testTimeLayer=L.timeDimension.layer.wms(testLayer, {
        cache:50
    });

    getLayerMinMax(wmsLayer,testLayer,contourLayer,testWMS,addLegend,testTimeLayer);

    var well_layer=L.geoJSON(points,{
        onEachFeature: function (feature, layer){
            function getpopup_content(){
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
                if (!feature.properties.Outlier || feature.properties.Outlier==false){
                    var container ='<a href="#" class='+feature.properties.HydroID+'>Flag as Outlier</a>';
                    layer.setStyle({
                        color:"blue"
                    })
                }
                else{
                    var warning="Outlier";
                    warning=warning.fontcolor("red").bold();
                    var container ='<a href="#" class='+feature.properties.HydroID+'>Unflag as Outlier</a>'+"<br>"+warning;
                    layer.setStyle({
                        color:"red"
                    })
                }
                popup_content+="<br>"+container
                return popup_content
            }
            popup_content=getpopup_content();



            var data=[];
            var elevation=[];
            var drawdown=[];
            if (feature.TsTime){
                for (i=0;i<feature.TsTime.length;i++){
                    data[i]=[feature.TsTime[i]*1000,feature.TsValue[i]];
                    elevation[i]=[feature.TsTime[i]*1000,feature.TsValue[i]+feature.properties.LandElev];
                    drawdown[i]=[feature.TsTime[i]*1000,feature.TsValue[i]-feature.TsValue[0]];
                }
            }
            //make a high charts
            layer.on({
                click: function showResultsInDiv() {
                    count=0;
                    map.on('popupopen', function() {
                        $('.'+feature.properties.HydroID).click(function() {
                            if (count==0){
                                if (!feature.properties.Outlier || feature.properties.Outlier==false){
                                    feature.properties.Outlier=true;
                                    popup_content=getpopup_content();
                                    var edit="add";
                                    $.ajax({
                                        url: '/apps/gw/addoutlier/',
                                        type: 'GET',
                                        data: {'region':region, 'aquifer':aquifer, 'hydroId':feature.properties.HydroID, 'edit':edit},
                                        contentType: 'application/json',
                                        error: function (status) {

                                        }, success: function (response) {
                                            layer._popup.setContent(popup_content);
                                        }
                                    });
                                }
                                else{
                                    feature.properties.Outlier=false;
                                    popup_content=getpopup_content();
                                    var edit="remove";
                                    $.ajax({
                                        url: '/apps/gw/addoutlier/',
                                        type: 'GET',
                                        data: {'region':region, 'aquifer':aquifer, 'hydroId':feature.properties.HydroID, 'edit':edit},
                                        contentType: 'application/json',
                                        error: function (status) {

                                        }, success: function (response) {
                                            layer._popup.setContent(popup_content);
                                        }
                                    });
                                }
                                count+=1;
                                map.closePopup();
                            }
                        });
                    });
                    mychart=Highcharts.chart('chart',{
                        chart: {
                            type: 'spline'
                        },
                        title: {
                            text: (function(){
                                //'Depth to Water Table (ft)'}
                                    type=$("#select_view").find('option:selected').val();
                                    if (type=="elevation"){
                                        type="Elevation of Water Table ";
                                    }
                                    else if(type=="drawdown"){
                                        type="Drawdown ";
                                    }
                                    else{
                                        type="Depth to Water Table ";
                                    }
                                    type+='at Well ' +feature.properties.HydroID+", located at "+feature.geometry.coordinates
                                    return type;
                                    })()
                        },
                        tooltip:{valueDecimals:2},
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
                                text: (function(){
                                //'Depth to Water Table (ft)'}
                                    type=$("#select_view").find('option:selected').val();
                                    if (type=="elevation"){
                                        type="Elevation of Water Table (ft)";
                                    }
                                    else if(type=="drawdown"){
                                        type="Drawdown (ft)";
                                    }
                                    else{
                                        type="Depth to Water Table (ft)";
                                    }
                                    return type;
                                    })()
                                }
                        },
                        series: [{
                            data: data,
                            name: "Depth to Water Table (ft)",
                            marker:{enabled: true},
                            visible:(function(){
                                    type=$("#select_view").find('option:selected').val();
                                    if (type=="elevation"){
                                        type="Elevation of Water Table (ft)";
                                    }
                                    else if(type=="drawdown"){
                                        type="Drawdown (ft)";
                                    }
                                    else{
                                        type="Depth to Water Table (ft)";
                                    }
                                    visible=false
                                    if (type=="Depth to Water Table (ft)"){
                                        visible=true;
                                    }
                                    return visible;
                                })()
                            },
                            {
                            data:elevation,
                            name: "Elevation of Water Table (ft)",
                            marker:{enabled: true},
                            color:'blue',
                            visible:(function(){
                                    type=$("#select_view").find('option:selected').val();
                                    if (type=="elevation"){
                                        type="Elevation of Water Table (ft)";
                                    }
                                    else if(type=="drawdown"){
                                        type="Drawdown (ft)";
                                    }
                                    else{
                                        type="Depth to Water Table (ft)";
                                    }
                                    visible=false
                                    if (type=="Elevation of Water Table (ft)"){
                                        visible=true;
                                    }
                                    return visible;
                                })()
                            },
                            {
                            data:drawdown,
                            name: "Drawdown (ft)",
                            marker:{enabled: true},
                            color:'#1A429E',
                            visible:(function(){
                                    type=$("#select_view").find('option:selected').val();
                                    if (type=="elevation"){
                                        type="Elevation of Water Table (ft)";
                                    }
                                    else if(type=="drawdown"){
                                        type="Drawdown (ft)";
                                    }
                                    else{
                                        type="Depth to Water Table (ft)";
                                    }
                                    visible=false
                                    if (type=="Drawdown (ft)"){
                                        visible=true;
                                    }
                                    return visible;
                                })()
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
                    $("#select_view").bind("change", (function() {
                        if (!mychart){
                            return;
                        }
                        type=$("#select_view").find('option:selected').val();
                        if (type=="elevation"){
                            type="Elevation of Water Table (ft)";
                        }
                        else if(type=="drawdown"){
                            type="Drawdown (ft)";
                        }
                        else{
                            type="Depth to Water Table (ft)";
                        }
                        for (var i=0;i<mychart.series.length;i++){
                            if (mychart.series[i].name==type){
                                mychart.series[i].show();
                            }
                            else{
                                mychart.series[i].hide();
                            }
                        }
                        mychart.yAxis[0].setTitle({text: type});
                        type=type.substring(0,type.length-4)
                        mychart.setTitle({text:type +'at Well ' +feature.properties.HydroID+", located at "+feature.geometry.coordinates})

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

    var url=thredds_url+region+'/'+interpolation_type+'/'+name+"?service=WMS&version=1.3.0&request=GetCapabilities";

    var oReq = new XMLHttpRequest();
    oReq.addEventListener("load", (function(xhr) {
        var response = xhr.currentTarget.response;
        pos1=response.indexOf("-12-30T00:00:00.000Z")+1
        pos2=response.indexOf("-12-30T00:00:00.000Z",pos1)-4
        pos3=response.indexOf(">",pos2)
        pos4=response.indexOf("<",pos2)
        pos3=Math.min(pos3,pos4)
        substring=response.substring(pos2,pos3)
        map.timeDimension.setAvailableTimes(substring, "replace");
        document.getElementById('waiting_output').innerHTML = '';
    }));
    oReq.open("GET", url);
    oReq.send();

    //document.getElementById('waiting_output').innerHTML = '';
}

function list_aquifer(){
    region=$("#select_region").find('option:selected').val()
    region_group.clearLayers();
    clearwells();
    clearwaterlevels();
    toggle.remove();
    toggle=L.control.layers(null,null).addTo(map);
    minor_group.clearLayers();
    major_group.clearLayers();
    //This ajax controller loads the JSON file for the Texas State boundary and adds it to the map
    var geolayer = region+'_State_Boundary.json';
    var region=$("#select_region").find('option:selected').val();
    $.ajax({
        url: '/apps/gw/displaygeojson/',
        type: 'GET',
        data: {'geolayer':geolayer,'region':region},
        contentType: 'application/json',
        error: function (status) {

        }, success: function (response) {

            texasboundary=response['state'].features;
            var aquifer_center=regioncenter
            texasborder=L.geoJSON(texasboundary,{
                color:"red",
                weight:1,
                fillOpacity:0.0,
                onEachFeature: function (feature, layer) {
                    feature.properties.bounds_calculated = layer.getBounds();
                    var latcenter=(feature.properties.bounds_calculated._northEast.lat+feature.properties.bounds_calculated._southWest.lat)/2;
                    var loncenter=(feature.properties.bounds_calculated._northEast.lng+feature.properties.bounds_calculated._southWest.lng)/2;
                    aquifer_center=[latcenter,loncenter];
                },
            });
            region_group.addLayer(texasborder);
            region_group.addTo(map);
            regioncenter=aquifer_center;
            if (response['major']){
                major=response['major'];
                majoraquifers=L.geoJSON(major,{
                    weight:1,
                    fillOpacity:0.2,
                    onEachFeature: function (feature, layer){
                        tooltip_content="Major Aquifer: "+feature.properties.Name;
                        layer.bindTooltip(tooltip_content,{sticky:true});
                        layer.on({
                            click: function jumpaquifer(){
                                $("#select_aquifer").val(feature.properties.Id);
                                document.getElementById("select2-select_aquifer-container").innerHTML=$("#select_aquifer").find('option:selected').text();
                                list_dates(2)//,feature.properties.Name,feature.properties.Id)
                            }
                        });

                    }
                });
                majoraquifers.addTo(major_group);
                major_group.addTo(map);
                toggle.addOverlay(major_group, "Major Aquifers");
            }
            if (response['minor']){
                minor=response['minor'];
                minoraquifers=L.geoJSON(minor,{
                    color:'green',
                    weight:1,
                    fillOpacity:0.2,
                    onEachFeature: function (feature, layer){
                        tooltip_content="Minor Aquifer: "+feature.properties.Name;
                        layer.bindTooltip(tooltip_content,{sticky:true});
                        layer.on({
                            click: function jumpaquifer(){
                                $("#select_aquifer").val(feature.properties.Id);
                                document.getElementById("select2-select_aquifer-container").innerHTML=$("#select_aquifer").find('option:selected').text();
                                list_dates(2)//,feature.properties.Name,feature.properties.Id)
                            }
                        });

                    }
                });
                minoraquifers.addTo(minor_group);
                minor_group.addTo(map);
                toggle.addOverlay(minor_group, "Minor Aquifers");
            }

            map.fitBounds(region_group.getBounds());
            size= map.getSize();
            bounds=map.getBounds().toBBoxString();

            $.ajax({
                url: '/apps/gw/loadaquiferlist/',
                type: 'GET',
                data: {'region':region},
                contentType: 'application/json',
                error: function (status) {

                }, success: function (response) {
                    aquiferlist=response.aquiferlist;
                    $("#select_aquifer").empty();
                    $("#select_aquifer").append('<option value="'+9999+'">'+''+'</option>');
                    for (i=0;i<aquiferlist.length;i++){
                        name=aquiferlist[i].Name;
                        number=aquiferlist[i].Id;
                        $("#select_aquifer").append('<option value="'+number+'">'+name+'</option>');
                    }
                    document.getElementById("select2-select_aquifer-container").innerHTML=$("#select_aquifer").find('option:selected').text();
                    $("#available_dates").empty();
                    document.getElementById("select2-available_dates-container").innerHTML='';
                }
            });

        }

    });

}

function list_dates(call_function){
    var region=$("#select_region").find('option:selected').val()
    //This ajax controller

    aquifer=$("#select_aquifer").find('option:selected').text();

    var interpolation_type=$("#select_interpolation").find('option:selected').val();

    $.ajax({
        url: '/apps/gw/loadtimelist/',
        type: 'GET',
        data: {'region':region, 'aquifer':aquifer, 'interpolation_type':interpolation_type},
        contentType: 'application/json',
        error: function (status) {

        }, success: function (response) {
            timelist=response.timelist;
            $("#available_dates").empty();
            //$("#available_types").append('<option value="'+9999+'">'+''+'</option>');
            for (i=0;i<timelist.length;i++){
                number=timelist[i].Full_Name;
                name=timelist[i].Aquifer+': '+timelist[i].Start_Date+'-'+timelist[i].End_Date+' ('+timelist[i].Interval+ " Year Increments, "+(timelist[i].Resolution)+" Degree Resolution, "+timelist[i].Min_Samples+" Min Samples, "+(timelist[i].Min_Ratio)+ " Min Ratio, "+timelist[i].Time_Tolerance+ " Year Time Tolerance)";
                $("#available_dates").append('<option value="'+number+'">'+name+'</option>');
                if (timelist.length==1){
                    $("#available_dates").val(number);
                }

                if (timelist[i].Default==1){
                    $("#available_dates").val(number);
                }
                document.getElementById("select2-available_dates-container").innerHTML=$("#available_dates").find('option:selected').text();
            }
            if (timelist.length>1){
                document.getElementById('buttons').style.display="block"
            }
            else{
                document.getElementById('buttons').style.display="none"
            }
            if (call_function==1){
                changeWMS();
            }
            if (call_function==2){
                change_aquifer();
            }
        }
    });


}

function confirm_delete(){
    var region=$("#select_region").find('option:selected').val()
    var aquifer=$("#select_aquifer").find('option:selected').text()
    var interpolation_type=$("#select_interpolation").find('option:selected').val();
    var name=$("#available_dates").find('option:selected').val();
    var x =confirm("Are you sure you want to delete the current NetCDF Raster? ("+name+")");
    if (x){
        $.ajax({
        url: '/apps/gw/deletenetcdf/',
        type: 'GET',
        data: {'region':region, 'aquifer':aquifer, 'interpolation_type':interpolation_type, 'name':name},
        contentType: 'application/json',
        error: function (status) {

        }, success: function (response) {
            list_dates(1);
        }
    });
    }
}

function confirm_default(){
    var region=$("#select_region").find('option:selected').val()
    var aquifer=$("#select_aquifer").find('option:selected').text()
    var interpolation_type=$("#select_interpolation").find('option:selected').val();
    var name=$("#available_dates").find('option:selected').val();
    var x =confirm("Are you sure you want to make the current NetCDF raster the default? ("+name+")");
    if (x){
        $.ajax({
        url: '/apps/gw/defaultnetcdf/',
        type: 'GET',
        data: {'region':region, 'aquifer':aquifer, 'interpolation_type':interpolation_type, 'name':name},
        contentType: 'application/json',
        error: function (status) {

        }, success: function (response) {
            list_dates(1);
        }
    });
    }
}

