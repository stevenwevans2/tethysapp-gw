var thredds_url="https://tethys2.byu.edu/thredds/wms/testAll/groundwater/";
//var thredds_url = "http://localhost:8080/thredds/wms/testAll/groundwater/";
var units="Metric";

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

L.LayerGroup.include({
    customGetLayer: function (id) {
        for (var i in this._layers) {
            if (this._layers[i].id == id) {
               return this._layers[i];
            }
        }
    }
});

//This function is called when the interpolation method or the data type is adjusted on the app Regional Map page.
//The function clears the displayed Raster layers and then adds new raster layers for the specified interpolation and data type.
//The function calls the getLayerMinMax function to determine the bounds of the new raster and adjust the symbology and legend accordingly.
function changeWMS(){

    var name=$("#available_dates").find('option:selected').val();
    name=name.replace(/ /g,"_");
    clearwaterlevels();
    var region=$("#select_region").find('option:selected').val();


    var testWMS=thredds_url+region+'/'+name;
    if (name=='Blank.nc'){
        testWMS=thredds_url+'/'+name;
    }

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

    var url=thredds_url+region+'/'+name+"?service=WMS&version=1.3.0&request=GetCapabilities";
    if (name=='Blank.nc'){
        url=thredds_url+'/'+name+"?service=WMS&version=1.3.0&request=GetCapabilities";
    }

    var oReq = new XMLHttpRequest();
    oReq.addEventListener("load", (function(xhr) {
        var response = xhr.currentTarget.response;
        pos1=response.indexOf("T00:00:00.000Z")+1
        pos2=response.indexOf("T00:00:00.000Z",pos1)-10
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
    var region=$("#select_region").find('option:selected').val();

    var testWMS=thredds_url+region+'/'+name;
    if (name=='Blank.nc'){
        testWMS=thredds_url+'/'+name;
    }

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
    testTimeLayer.id='timelayer';
    interpolation_group.addLayer(testTimeLayer);
    contour_group.addLayer(contourTimeLayer);

    var url=thredds_url+region+'/'+name+"?service=WMS&version=1.3.0&request=GetCapabilities";
    if (name=="Blank.nc"){
        url=thredds_url+'/'+name+"?service=WMS&version=1.3.0&request=GetCapabilities";
    }

    var oReq = new XMLHttpRequest();
    oReq.addEventListener("load", (function(xhr) {
        var response = xhr.currentTarget.response;
        pos1=response.indexOf("T00:00:00.000Z")+1
        pos2=response.indexOf("T00:00:00.000Z",pos1)-10
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
    if (testWMS.includes("Blank.nc")==false){
        testLegend.onAdd = function(map) {
                        var src=testWMS+"?REQUEST=GetLegendGraphic&LAYER="+layer+"&PALETTE="+palette+"&COLORSCALERANGE="+colormin+","+colormax;
                        var div = L.DomUtil.create('div', 'info legend');
                        div.innerHTML +=
                            '<img src="' + src + '" alt="legend">';
                        return div;
                    };
        testLegend.addTo(map);
    }
    var contourTimeLayer=L.timeDimension.layer.wms(contourLayer,{
        cache:50
    });
    testTimeLayer.id='timelayer';
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


document.getElementById('buttons').style.display="none";
document.getElementById('volbut').style.display="none";
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
//var TopoMap = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
//	maxZoom: 17,
//	attribution: 'Map data: &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
//});

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
var legend = L.control({position: 'bottomleft'});
legend.onAdd = function (map) {
    var div = L.DomUtil.create('div', 'info_legend');
    labels = ['<strong>Legend</strong>'],
    labels.push('<span class="greenwell"></span> Wells with Data spanning Time Period');
    labels.push('<span class="bluewell"></span> Wells with Data in Time Period');
    labels.push('<span class="greywell"></span> Wells with no Data in Time Period');
    labels.push('<span class="redwell"></span> Wells with Data Outliers');
    div.innerHTML = labels.join('<br>');
    return div;
};
map.on('overlayremove', function(e){
    if (e.name==="Wells"){
        legend.remove();
    }
    if (e.name==="Water Table Surface"){
        testLegend.remove();
    }
})
map.on('overlayadd', function(e){
    if (e.name==="Wells"){
        legend.addTo(map);
    }
    var aq=$("#available_dates").find('option:selected').val();
    if (e.name==="Water Table Surface" && aq!='Blank.nc'){
        testLegend.addTo(map);
    }
})

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
    legend.remove()
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

        var region=$("#select_region").find('option:selected').val();

            $.ajax({
                url: '/apps/gw/loaddata/',
                type: 'GET',
                data: {'id':id,'region':region, 'make_default':0, 'from_wizard':0},
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

    var length_unit="m";
    var vol_unit="Cubic Meters";
    if (units=="English"){
        length_unit="ft";
        vol_unit="Acre-ft"
    }
    var color='blue';
    var aquifer=$("#select_aquifer").find('option:selected').text();
    var name=$("#available_dates").find('option:selected').val();

    legend.addTo(map);

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
    var region=$("#select_region").find('option:selected').val();

    var testWMS=thredds_url+region+'/'+name;
    if (name=="Blank.nc"){
        testWMS=thredds_url+'/'+name;
    }

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
                if (feature.properties.FType){
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
                }
                popup_content+="<br>"+"Aquifer: "+aquifer;
                if (feature.properties.LandElev){
                    if (feature.properties.LandElev!=-9999){
                        popup_content+="<br>"+"Elevation: "+feature.properties.LandElev + " feet";
                    }
                    else{
                        feature.properties.LandElev=0;
                    }
                }

                if (feature.properties.WellDepth){
                    popup_content+="<br>"+"Well Depth: "+feature.properties.WellDepth + " feet";
                }

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

            function set_color(){
                var yearstring=$('#available_dates').find('option:selected').text();
                if (yearstring=='No Raster'){
                    var first_date=new Date(1800,0,1);
                    var last_date=new Date(2020,0,1);
                }
                else{
                    var start=yearstring.indexOf(': ')+1;
                    var stop1=yearstring.indexOf('-',start);
                    var stop2=yearstring.indexOf(' (',stop1);
                    var first_date=Number(yearstring.substring(start,stop1));
                    var last_date=Number(yearstring.substring(stop1+1,stop2));
                    first_date=new Date(first_date,0,1);
                    last_date=new Date(last_date,0,1);
                }
                if (!feature.properties.Outlier || feature.properties.Outlier==false){
                    if (feature.TsTime){
                        if (feature.TsTime[0]*1000<=first_date && feature.TsTime[feature.TsTime.length-1]*1000>=last_date){
                            layer.setStyle({
                                color:"green",
                                fillColor:"#ffffff",
                                radius:2,
                                fillOpacity:.9

                            })
                        }
                        else if (feature.TsTime[feature.TsTime.length-1]*1000>first_date && feature.TsTime[0]<last_date){
                            layer.setStyle({
                                color:"blue",
                                fillColor:"#ffffff",
                                radius:2,
                                fillOpacity:.9

                            })
                        }
                        else{
                            layer.setStyle({
                                color:"grey",
                                radius:1
                            })
                        }
                    }
                    else{
                        layer.setStyle({
                            color:"grey",
                            radius:1
                        })
                    }
                }
                else{
                    layer.setStyle({
                            color:"red",
                            radius:1
                        })
                }
            }

            function set_content(){
                //make a high charts
                if (feature.TsTime){
                    layer.on({
                        click: function showResultsInDiv() {
                            var data=[];
                            var elevation=[];
                            var drawdown=[];
                            var first_date=new Date(testTimeLayer._timeDimension.getAvailableTimes()[0])

                            if (feature.TsTime){
                                var tlocation = 0;
                                var stop_location = 0;
                                for (var i=0;i<feature.TsTime.length;i++){
                                    if ((feature.TsTime[i]*1000)>=first_date && stop_location==0){
                                        tlocation = i;
                                        stop_location = 1;
                                    }
                                }
                            }
                            // target time is larger than max date
                            if (tlocation == 0 && stop_location == 0){
                                tlocation = -999;
                            }

                            // target time is smaller than min date
                            if (tlocation == 0 && stop_location == 1){
                                tlocation = -888;
                            }

                            // for the case where the target time is in the middle
                            if (tlocation > 0){
                                var timedelta = first_date - (feature.TsTime[tlocation - 1]*1000);
                                var slope = (feature.TsValue[tlocation] - feature.TsValue[tlocation - 1]) / (
                                        (feature.TsTime[tlocation]*1000) - (feature.TsTime[tlocation - 1]*1000));
                                var timevalue = feature.TsValue[tlocation - 1] + slope * timedelta;
                            }

                            if (feature.TsTime){
                                for (var i=0;i<feature.TsTime.length;i++){
                                    data[i]=[feature.TsTime[i]*1000,feature.TsValue[i]];
                                    if (feature.properties.LandElev){
                                        elevation[i]=[feature.TsTime[i]*1000,feature.TsValue[i]+feature.properties.LandElev];
                                    }
                                    else{
                                        elevation[i]=[feature.TsTime[i]*1000,feature.TsValue[i]];
                                    }
                                    if (tlocation>0){
                                        drawdown[i]=[feature.TsTime[i]*1000,feature.TsValue[i]-timevalue];
                                    }
                                    else{
                                        drawdown[i]=[feature.TsTime[i]*1000,feature.TsValue[i]-feature.TsValue[0]];
                                    }
                                }
                            }
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
                                            var since='';
                                            type=$("#select_view").find('option:selected').val();
                                            if (type=="elevation"){
                                                type="Elevation of Water Table ";
                                            }
                                            else if(type=="drawdown"){
                                                type="Drawdown ";
                                                var blank_raster=$("#available_dates").find('option:selected').val();
                                                var first_entry=data[0][0];
                                                if (blank_raster!="Blank.nc"){
                                                    var first_time=new Date(testTimeLayer._timeDimension.getAvailableTimes()[0]);
                                                    var last_entry=data[data.length-1][0];
                                                    if (last_entry<first_time){
                                                        var min =first_entry;
                                                    }
                                                    else{
                                                        var min=Math.max(first_time,first_entry);
                                                    }
                                                }
                                                else{
                                                    var min=first_entry;
                                                }
                                                min=new Date(min)
                                                year=min.getFullYear();
                                                var months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
                                                var month = months[min.getMonth()];
                                                since="since "+month+", "+year+" ";
                                            }
                                            else{
                                                type="Depth to Water Table ";
                                            }
                                            type+=since+'at Well ' +feature.properties.HydroID+", located at "+feature.geometry.coordinates
                                            return type;
                                            })()
                                },
                                tooltip:{valueDecimals:2},
                                xAxis: {
                                    type: 'datetime',

                                    title: {
                                        text: 'Date'
                                    },
                                    min:(function(){
                                        var blank_raster=$("#available_dates").find('option:selected').val();
                                        var first_entry=data[0][0];
                                        if (blank_raster!="Blank.nc"){
                                            var first_time=new Date(testTimeLayer._timeDimension.getAvailableTimes()[0]);
                                            var min=Math.min(first_time,first_entry);
                                        }
                                        else{
                                            var min=first_entry;
                                        }
                                        return min;
                                    })(),
                                    max:(function(){
                                        var blank_raster=$("#available_dates").find('option:selected').val();
                                        var last_entry=data[data.length-1][0];
                                        if (blank_raster!="Blank.nc"){
                                            var last_time=new Date(testTimeLayer._timeDimension.getAvailableTimes()[testTimeLayer._timeDimension.getAvailableTimes().length-1]);
                                            var max=Math.max(last_time,last_entry);
                                        }
                                        else{
                                            var max=last_entry;
                                        }
                                        return max;
                                    })(),
                                    plotBands:[{
                                        color: 'rgba(0,0,0,0.05)',
                                        from: new Date(1850,0,1),
                                        to:new Date(testTimeLayer._timeDimension.getAvailableTimes()[0]),
                                        id:'band1'
                                    },
                                    {
                                        color: 'rgba(0,0,0,0.05)',
                                        from: new Date(testTimeLayer._timeDimension.getAvailableTimes()[testTimeLayer._timeDimension.getAvailableTimes().length-1]),
                                        to:new Date(2050,0,1),
                                        id:'band2'
                                    }],
                                    plotLines: [{
                                        color: 'red',
                                        dashStyle: 'solid',
                                        value: new Date(testTimeLayer._timeDimension.getCurrentTime()),
                                        width: 2,
                                        id: 'pbCurrentTime'
                                    }],

                                },
                                yAxis:{
                                    title: {
                                        text: (function(){
                                        //'Depth to Water Table (ft)'}
                                            type=$("#select_view").find('option:selected').val();
                                            if (type=="elevation"){
                                                type="Elevation of Water Table ("+length_unit+")";
                                            }
                                            else if(type=="drawdown"){
                                                type="Drawdown ("+length_unit+")";
                                            }
                                            else{
                                                type="Depth to Water Table ("+length_unit+")";
                                            }
                                            return type;
                                            })()
                                        }
                                },
                                series: [{
                                    data: data,
                                    name: "Depth to Water Table ("+length_unit+")",
                                    marker:{enabled: true},
                                    visible:(function(){
                                            type=$("#select_view").find('option:selected').val();
                                            if (type=="elevation"){
                                                type="Elevation of Water Table ("+length_unit+")";
                                            }
                                            else if(type=="drawdown"){
                                                type="Drawdown ("+length_unit+")";
                                            }
                                            else{
                                                type="Depth to Water Table ("+length_unit+")";
                                            }
                                            visible=false
                                            if (type=="Depth to Water Table ("+length_unit+")"){
                                                visible=true;
                                            }
                                            return visible;
                                        })()
                                    },
                                    {
                                    data:elevation,
                                    name: "Elevation of Water Table ("+length_unit+")",
                                    marker:{enabled: true},
                                    color:'blue',
                                    visible:(function(){
                                            type=$("#select_view").find('option:selected').val();
                                            if (type=="elevation"){
                                                type="Elevation of Water Table ("+length_unit+")";
                                            }
                                            else if(type=="drawdown"){
                                                type="Drawdown ("+length_unit+")";
                                            }
                                            else{
                                                type="Depth to Water Table ("+length_unit+")";
                                            }
                                            visible=false
                                            if (type=="Elevation of Water Table ("+length_unit+")"){
                                                visible=true;
                                            }
                                            return visible;
                                        })()
                                    },
                                    {
                                    data:drawdown,
                                    name: "Drawdown ("+length_unit+")",
                                    marker:{enabled: true},
                                    color:'#1A429E',
                                    visible:(function(){
                                            type=$("#select_view").find('option:selected').val();
                                            if (type=="elevation"){
                                                type="Elevation of Water Table ("+length_unit+")";
                                            }
                                            else if(type=="drawdown"){
                                                type="Drawdown ("+length_unit+")";
                                            }
                                            else{
                                                type="Depth to Water Table ("+length_unit+")";
                                            }
                                            visible=false
                                            if (type=="Drawdown ("+length_unit+")"){
                                                visible=true;
                                            }
                                            return visible;
                                        })()
                                    }]
                            });
//                          Ajax controller to get interpolation data for the well
                            $.ajax({
                                url: '/apps/gw/get_timeseries/',
                                type: 'GET',
                                data: {'region':region, 'netcdf':$("#available_dates").find('option:selected').val(), 'hydroid':feature.properties.HydroID},
                                contentType: 'application/json',
                                error: function (status) {

                                }, success: function (response) {
                                    if (response['depths']){
                                        var interp_depths=response['depths'];
                                        var interp_times=response['times'];
                                        var interpodata=[];
                                        var j=0;
                                        for (var i=0;i<interp_times.length;i++){
                                            if (interp_depths[i]!=-9999){
                                                interpodata[j]=[new Date(interp_times[i]*24*3600*1000)-new Date('3939-1-2'),interp_depths[i]];
                                                j=j+1;
                                            }
                                        }
                                        mychart.addSeries({
                                            name: "Well Depth Used in Interpolation",
                                            marker:{enabled: true},
                                            data:interpodata,
                                            visible:true
                                        });
                                    }
                                }
                            });
//                          End of added Ajax Controller

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
                            $("#select_view").bind("change", (function updateTitle() {
                                if (!mychart){
                                    return;
                                }
                                var since='';
                                type=$("#select_view").find('option:selected').val();
                                if (type=="elevation"){
                                    type="Elevation of Water Table ("+length_unit+")";
                                }
                                else if(type=="drawdown"){
                                    type="Drawdown ("+length_unit+")";
                                    var blank_raster=$("#available_dates").find('option:selected').val();
                                    var first_entry=data[0][0];
                                    if (blank_raster!="Blank.nc"){
                                        var first_time=new Date(testTimeLayer._timeDimension.getAvailableTimes()[0]);
                                        var last_entry=data[data.length-1][0];
                                        if (last_entry<first_time){
                                            var min =first_entry;
                                        }
                                        else{
                                            var min=Math.max(first_time,first_entry);
                                        }
                                    }
                                    else{
                                        var min=first_entry;
                                    }
                                    min=new Date(min)
                                    year=min.getFullYear();
                                    var months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
                                    var month = months[min.getMonth()];
                                    since="since "+month+", "+year+" ";
                                }
                                else{
                                    type="Depth to Water Table ("+length_unit+")";
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
                                mychart.setTitle({text:type +since+'at Well ' +feature.properties.HydroID+", located at "+feature.geometry.coordinates})

                            }).bind(this));
                            testTimeLayer._timeDimension.on('availabletimeschanged', (function updateTitle() {
                                if (!mychart){
                                    return;
                                }
                                var since='';
                                type=$("#select_view").find('option:selected').val();
                                if (type=="elevation"){
                                    type="Elevation of Water Table ("+length_unit+")";
                                }
                                else if(type=="drawdown"){
                                    type="Drawdown ("+length_unit+")";
                                    var blank_raster=$("#available_dates").find('option:selected').val();
                                    var first_entry=data[0][0];
                                    if (blank_raster!="Blank.nc"){
                                        var first_time=new Date(testTimeLayer._timeDimension.getAvailableTimes()[0]);
                                        var last_entry=data[data.length-1][0];
                                        if (last_entry<first_time){
                                            var min =first_entry;
                                        }
                                        else{
                                            var min=Math.max(first_time,first_entry);
                                        }
                                    }
                                    else{
                                        var min=first_entry;
                                    }
                                    min=new Date(min)
                                    year=min.getFullYear();
                                    var months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
                                    var month = months[min.getMonth()];
                                    since="since "+month+", "+year+" ";
                                }
                                else{
                                    type="Depth to Water Table ("+length_unit+")";
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
                                mychart.setTitle({text:type +since+'at Well ' +feature.properties.HydroID+", located at "+feature.geometry.coordinates})

                            }).bind(this));
                            testTimeLayer._timeDimension.on('availabletimeschanged', (function() {
                                if (!mychart){
                                    return;
                                }

                                var last_entry=data[data.length-1][0];
                                var max=Math.max(last_time,last_entry);
                                var first_entry=data[0][0];
                                var blank_raster=$("#available_dates").find('option:selected').val();
                                if (blank_raster!="Blank.nc"){
                                    var last_time=new Date(testTimeLayer._timeDimension.getAvailableTimes()[testTimeLayer._timeDimension.getAvailableTimes().length-1]);
                                    var first_time=new Date(testTimeLayer._timeDimension.getAvailableTimes()[0]);
                                    var min=Math.min(first_time,first_entry);
                                    var max=Math.max(last_time, last_entry);
                                }
                                else{
                                    var min=first_entry;
                                    var max=last_entry;
                                }

                                mychart.xAxis[0].removePlotBand('band1');
                                mychart.xAxis[0].removePlotBand('band2');
                                mychart.xAxis[0].addPlotBand({
                                    color: 'rgba(0,0,0,0.05)',
                                    from: new Date(1850,0,1),
                                    to:new Date(testTimeLayer._timeDimension.getAvailableTimes()[0]),
                                    id:'band1'
                                })
                                mychart.xAxis[0].addPlotBand({
                                    color: 'rgba(0,0,0,0.05)',
                                    from: new Date(testTimeLayer._timeDimension.getAvailableTimes()[testTimeLayer._timeDimension.getAvailableTimes().length-1]),
                                    to:new Date(2050,0,1),
                                    id:'band2'
                                })
                                mychart.xAxis[0].setExtremes(min,max);

                            }).bind(this));
                        }

                    });
                }
                else{
                    layer.on("click",function(){
                        document.getElementById("chart").innerHTML='<strong>No Time Series Data for Well ' +feature.properties.HydroID+", located at "+feature.geometry.coordinates+'</strong>';
                    })
                }
                layer.bindPopup(popup_content);
            }
            set_content();
            set_color();
            //option for highlighting selected point
            layer.on('popupopen', function(e){
                e.target.setStyle({color:"white", radius:8, fillColor:"red"});
                map.on('popupopen', function(){
                    set_color();
                })
            });

            $("#available_dates").on("change", (function(){set_color()}));
        },
        pointToLayer:function(geoJsonPoint, latlng){
            return L.circleMarker(latlng,{radius:1, color:color});
        }
    });
    well_group.addLayer(well_layer)

    well_group.addTo(map);


    var url=thredds_url+region+'/'+name+"?service=WMS&version=1.3.0&request=GetCapabilities";
    if (name=='Blank.nc'){
        url=thredds_url+'/'+name+"?service=WMS&version=1.3.0&request=GetCapabilities";
    }

    var oReq = new XMLHttpRequest();
    oReq.addEventListener("load", (function(xhr) {
        var response = xhr.currentTarget.response;
        pos1=response.indexOf("T00:00:00.000Z")+1
        pos2=response.indexOf("T00:00:00.000Z",pos1)-10
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
    document.getElementById('buttons').style.display="none";
    document.getElementById('volbut').style.display="none";
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

function toggleButtons(){

    animation=$("#available_dates").find('option:selected').val();
    if (animation!='Blank.nc'){
        document.getElementById('buttons').style.display="block";
    }
    else{
        document.getElementById('buttons').style.display="none";
    }
    region=$("#select_region").find('option:selected').val();
    $.ajax({
        url: '/apps/gw/checktotalvolume/',
        type: 'GET',
        data: {'region':region, 'name':animation},
        contentType: 'application/json',
        error: function (status) {

        }, success: function (response) {
            var exists=response.exists;
            if (exists==true){
                document.getElementById('volbut').style.display="block";
            }
            else{
                document.getElementById('volbut').style.display="none";document.getElementById('volbut').style.display="none";
            }
            $('#display-status').html('');
            $('#display-status').html('').removeClass('success');
            $('#resource-abstract').val(response.abstract);
            $('#resource-keywords').val(response.keywords);
            $('#resource-title').val(response.title);
            $('#resource-type').val(response.type);
            var filepath =response.filepath;
            var metadata=response.metadata
        }
    });
}

function list_dates(call_function){
    var region=$("#select_region").find('option:selected').val()
    //This ajax controller

    aquifer=$("#select_aquifer").find('option:selected').text();


    $.ajax({
        url: '/apps/gw/loadtimelist/',
        type: 'GET',
        data: {'region':region, 'aquifer':aquifer},
        contentType: 'application/json',
        error: function (status) {

        }, success: function (response) {
            var timelist=response.timelist;
            $("#available_dates").empty();
            $("#available_dates").append('<option value="'+'Blank.nc'+'">'+'No Raster'+'</option>');
            $("#available_dates").val('Blank.nc');
            for (i=0;i<timelist.length;i++){
                number=timelist[i].Full_Name;
                if (timelist[i].Interp_Options){
                    var myoptions="elevation"
                    if (timelist[i].Interp_Options=="both"){
                        myoptions="elevation and depth";
                    }
                    else if (timelist[i].Interp_Options=="depth"){
                        myoptions="depth";
                    }
                    name=timelist[i].Aquifer+' '+ timelist[i].Interpolation+' using '+myoptions+': '+timelist[i].Start_Date+'-'+timelist[i].End_Date+' ('+timelist[i].Interval+ " Year Increments, "+(timelist[i].Resolution)+" Degree Resolution, "+timelist[i].Min_Samples+" Min Samples, "+(timelist[i].Min_Ratio)+ " Min Ratio, "+timelist[i].Time_Tolerance+ " Year Time Tolerance)";
                }
                else{
                    name=timelist[i].Aquifer+' '+ timelist[i].Interpolation+': '+timelist[i].Start_Date+'-'+timelist[i].End_Date+' ('+timelist[i].Interval+ " Year Increments, "+(timelist[i].Resolution)+" Degree Resolution, "+timelist[i].Min_Samples+" Min Samples, "+(timelist[i].Min_Ratio)+ " Min Ratio, "+timelist[i].Time_Tolerance+ " Year Time Tolerance)";
                }
                $("#available_dates").append('<option value="'+number+'">'+name+'</option>');
                if (timelist.length==1){
                    $("#available_dates").val(number);
                }

                if (timelist[i].Default==1){
                    $("#available_dates").val(number);
                }
                units=timelist[i].Units;
            }
            document.getElementById("select2-available_dates-container").innerHTML=$("#available_dates").find('option:selected').text();
            toggleButtons();
            if (call_function==1){
                changeWMS(); //clears only raster layers and updates them
            }
            if (call_function==2){
                change_aquifer(); //clears all layers and updates them
            }
        }
    });


}

function confirm_delete(){
    var region=$("#select_region").find('option:selected').val()
    var name=$("#available_dates").find('option:selected').val();
    var x =confirm("Are you sure you want to delete the current NetCDF Raster? ("+name+")");
    if (x){
        $.ajax({
        url: '/apps/gw/deletenetcdf/',
        type: 'GET',
        data: {'region':region, 'name':name},
        contentType: 'application/json',
        error: function (status) {

        }, success: function (response) {
            list_dates(1);
            document.getElementById('chart').innerHTML='';
        }
    });
    }
}

function confirm_default(){
    var region=$("#select_region").find('option:selected').val()
    var aquifer=$("#select_aquifer").find('option:selected').text()
    var name=$("#available_dates").find('option:selected').val();
    var x =confirm("Are you sure you want to make the current NetCDF raster the default? ("+name+")");
    if (x){
        $.ajax({
        url: '/apps/gw/defaultnetcdf/',
        type: 'GET',
        data: {'region':region, 'aquifer':aquifer, 'name':name},
        contentType: 'application/json',
        error: function (status) {

        }, success: function (response) {
            list_dates(1);
        }
    });
    }
}


function totalvolume(){
    region=$("#select_region").find('option:selected').val();
    name=$("#available_dates").find('option:selected').val();
    var length_unit="m";
    var vol_unit="Cubic Meters";
    if (units=="English"){
        length_unit="ft";
        vol_unit="Acre-ft"
    }
    $.ajax({
        url: '/apps/gw/gettotalvolume/',
        type: 'GET',
        data: {'region':region, 'name':name},
        contentType: 'application/json',
        error: function (status) {

        }, success: function (response) {
            //add data to highchart
            volumelist=response['volumelist'];
            timelist=response['timelist'];
            var length=timelist.length;
            var data=[];
            var oneday=24*60*60*1000;
            var UTCconversion=280*24*60*60*1000;
            var oneyear= 24*60*60*1000*365.2
            for (var i=0; i<length; i++){
                timelist[i]=timelist[i]*oneday-oneyear*1970+UTCconversion;
                timelist[i]=new Date(timelist[i]).getTime();
                data[i] = [timelist[i],volumelist[i]];
            }
            document.getElementById('chart').innerHTML='';
            var TimeLayer=interpolation_group.customGetLayer('timelayer');
            mychart=Highcharts.chart('chart',{
                chart: {
                    type: 'area',
                },
                title: {
                    text: (function(){
                    var type="Change in Aquifer Storage Volume "
                    var since='';
                    var blank_raster=$("#available_dates").find('option:selected').val();
                    var min=data[0][0];
                    min=new Date(min)
                    year=min.getFullYear();
                    var months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
                    var month = months[min.getMonth()];
                    since="since "+month+", "+year+" ";
                    type+=since+'(Acre-ft)';
                    return type;
                    })()
                },
                tooltip:{valueDecimals:0},
                xAxis: {
                    type: 'datetime',

                    title: {
                        text: 'Date'
                    },
                    plotLines: [{
                        color: 'red',
                        dashStyle: 'solid',
                        value: new Date(TimeLayer._timeDimension.getCurrentTime()),
                        width: 2,
                        id: 'pbCurrentTime'
                    }],
                },
                yAxis:{
                    title: {
                        text: (function(){
                        //'Depth to Water Table (ft)'}
                            type="Change in aquifer storage volume ("+vol_unit+")";
                            return type;
                            })()
                        }
                },
                series: [{
                    data: data,
                    name: "Change in aquifer storage volume ("+vol_unit+")"
                }]
            })
            TimeLayer._timeDimension.on('timeload', (function() {
                if (!mychart){
                    return;
                }
                mychart.xAxis[0].removePlotBand("pbCurrentTime");
                mychart.xAxis[0].addPlotLine({
                    color: 'red',
                    dashStyle: 'solid',
                    value: new Date(TimeLayer._timeDimension.getCurrentTime()),
                    width: 2,
                    id: 'pbCurrentTime'
                });
            }).bind(this));
        }
    });
}

//This is a function for uploading the NetCDF file to HydroShare

$('#hydroshare-proceed').on('click', function ()  {
           //This function only works on HTML5 browsers.
    var displayStatus = $('#display-status');
    displayStatus.removeClass('error');
    displayStatus.addClass('uploading');
    displayStatus.html('<em>Uploading...</em>');
    var resourceTypeSwitch = function(typeSelection) {
        var options = {
            'GenericResource': 'GenericResource',
            'Geographic Raster': 'RasterResource',
            'HIS Referenced Time Series': 'RefTimeSeries',
            'Model Instance': 'ModelInstanceResource',
            'Model Program': 'ModelProgramResource',
            'Multidimensional (NetCDF)': 'NetcdfResource',
            'Time Series': 'TimeSeriesResource',
            'Application': 'ToolResource'
        };
        return options[typeSelection];
    };

    var name=$("#available_dates").find('option:selected').val();
    name=name.replace(/ /g,"_");
    var region=$("#select_region").find('option:selected').val();
    region=region.replace(/ /g,"_");
    var resourceAbstract = $('#resource-abstract').val();
    var resourceTitle = $('#resource-title').val();
    var resourceKeywords = $('#resource-keywords').val();
    var resourceType = $('#resource-type').val();

     if (!resourceTitle || !resourceKeywords || !resourceAbstract) {
        displayStatus.removeClass('uploading');
        displayStatus.addClass('error');
        displayStatus.html('<em>You must provide all metadata information.</em>');
        return;
    }

    $(this).prop('disabled', true);
    $.ajax({
        type: 'POST',
        url: '/apps/gw/upload-to-hydroshare/',
        dataType:'json',
        data: {
                'name':name,
                'region':region,
                'r_title': resourceTitle,
                'r_type': resourceType,
                'r_abstract': resourceAbstract,
                'r_keywords': resourceKeywords
                        },
        success: function (data) {
            $('#hydroshare-proceed').prop('disabled', false);
            if ('error' in data) {
                displayStatus.removeClass('uploading');
                displayStatus.addClass('error');
                displayStatus.html('<em>' + data.error + '</em>');
            }
            else
            {
                displayStatus.removeClass('uploading');
                displayStatus.addClass('success');
                displayStatus.html('<em>' + data.success + ' View in HydroShare <a href="https://' + data.hs_domain +'/resource/' + data.newResource +
                    '" target="_blank">HERE</a></em>');
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            alert("Error");
            debugger;
            $('#hydroshare-proceed').prop('disabled', false);
            console.log(jqXHR + '\n' + textStatus + '\n' + errorThrown);
            displayStatus.removeClass('uploading');
            displayStatus.addClass('error');
            displayStatus.html('<em>' + errorThrown + '</em>');
        }
    });
});