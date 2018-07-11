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
			 //timeInterval:"1950-01-01/2015-01-01",
			 //period:"P5Y"
    },
    timeDimensionControl: true,
    center: regioncenter,
});

//add the background imagery
var wmsLayer = L.tileLayer.wms('https://demo.boundlessgeo.com/geoserver/ows?', {
    //layers: 'nasa:bluemarble'
    layers:'ne:NE1_HR_LC_SR_W_DR'
}).addTo(map);


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
//$('#select_region').change(function(){
function displaywells(){
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
    testLegend.remove();
}


//This is the new function that I am working on
function displaygeojson(region_number, wellfunction,surfacefunction) {
    geolayer = 'MajorAquifers.json';
    $.ajax({
        url: '/apps/gw/displaygeojson/',
        type: 'GET',
        data: {'geolayer':geolayer},
        contentType: 'application/json',
        error: function (status) {

        }, success: function (response) {
            MajorAquifers=response.features;

            geolayer='MinorAquifers.json';
            $.ajax({
                url: '/apps/gw/displaygeojson/',
                type: 'GET',
                data: {'geolayer':geolayer},
                contentType: 'application/json',
                error: function (status) {

                }, success: function (response) {
                    MinorAquifers=response.features;

                    //add the shapefiles to the map
                    //var Major=L.geoJSON(MajorAquifers);
                    //var Minor=L.geoJSON(MinorAquifers);
                    //Major.addTo(map);
                    //Minor.addTo(map);
                    var aquifers=['HUECO_BOLSON','WEST TEXAS BOLSONS','PECOS VALLEY','SEYMOUR','BRAZOS RIVER ALLUVIUM','BLAINE','BLOSSOM','BONE SPRING-VICTORIO PEAK','CAPITAN REEF COMPLEX','CARRIZO','EDWARDS','EDWARDS-TRINITY (HIGH PLAINS)','EDWARDS-TRINITY','ELLENBURGER-SAN SABA','GULF_COAST','HICKORY','IGNEOUS','MARATHON','MARBLE FALLS','NACATOCH','OGALLALA','NONE','RITA BLANCA','QUEEN CITY','RUSTLER','DOCKUM','SPARTA','TRINITY','WOODBINE','LIPAN','YEGUA JACKSON'];
                    var aquifer=aquifers[region_number-1];
                    var AquiferShape=[];
                    for (i=0;i<MajorAquifers.length;i++){
                        if(MajorAquifers[i].properties.AQ_NAME==aquifer){
                            AquiferShape.push(MajorAquifers[i]);
                        }
                    }
                    for (i=0;i<MinorAquifers.length;i++){
                        if(MinorAquifers[i].properties.AQU_NAME==aquifer){
                            AquiferShape.push(MinorAquifers[i]);
                        }
                    }
                    var display_aquifer=document.getElementById("aquifer_display").checked;
                    var aquifer_center=[];
                    if (AquiferShape.length>0){
                        var AquiferLayer=L.geoJSON(AquiferShape,{
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
                        if (display_aquifer){
                            aquifer_group.addLayer(AquiferLayer);
                        }
                    }
                    else{
                        map.setView(regioncenter,5);
                    }

                    if (display_aquifer){
                        aquifer_group.addTo(map);
                    }
                    var display_wells=document.getElementById("well_display").checked;
                    var display_surface=document.getElementById("surface_display").checked;

                    min_num=$("#required_data").val();
                    id=region_number;
		            var aquifers=['Hueco Bolson','West Texas Bolsons','Pecos Valley','Seymour','Brazos River Alluvium','Blaine','Blossom','Bone Spring-Victorio Peak','Capitan Reef Complex','Carrizo','Edwards','Edwards-Trinity-High Plains','Edwards-Trinity','Ellenburger-San-Aba','Gulf Coast','Hickory','Igneous','Maratho','Marble Falls','Nacatoch','Ogallala','None','Rita Blanca','Queen City','Rustler','Dockum','Sparta','Trinity','Woodbine','Lipan','Yegua Jackson','Texas'];
    		        var name=aquifers[region_number-1];
    		        var interpolation_type=$("#select_interpolation").find('option:selected').val();
    		        if (display_wells){
                        $.ajax({
                            url: '/apps/gw/loaddata/',
                            type: 'GET',
                            data: {'id':id,'min_num':min_num, 'name':name, 'interpolation_type':interpolation_type},
                            contentType: 'application/json',
                            error: function (status) {

                            }, success: function (response) {
                                var well_points=response['data'];//.features;
                                console.log(well_points);
                                interpolate=Number(response['interpolate']);
                                if (display_surface){
                                    interpolate=1;
                                }
                                else{
                                    interpolate=0;
                                }
                                console.log(interpolate);
                                wellfunction(region_number, well_points,interpolate,min_num);
                            }
                        })
                    }
                    else if(display_surface){
                        showraster();
                    }
                    else{
                        document.getElementById('waiting_output').innerHTML = '';
                    }
                }
            })
        }
    })


}

function displayallwells(region_number,well_points,interpolate,required){

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
    if (interpolate==1){
        name=name.replace(/ /g,"_")
        var interpolation_type=$("#select_interpolation").find('option:selected').val();
        var testWMS="http://tethys.byu.edu:7000/thredds/wms/testAll/groundwater/"+interpolation_type+"/"+name+".nc";
        //var testWMS="http://localhost:8080/thredds/wms/testAll/groundwater/"+interpolation_type+"/"+name+".nc";
        var colormin=-500;
        var colormax=0;
        if (region_number==28){
              colormin=-1000;
        }
        var testLayer = L.tileLayer.wms(testWMS, {
            layers: 'depth',
            format: 'image/png',
            transparent: true,
            opacity:0.5,
            colorscalerange:colormin+','+colormax,
            attribution: '<a href="https://www.pik-potsdam.de/">PIK</a>'
        });
        var testTimeLayer = L.timeDimension.layer.wms(testLayer, {
        });
        testTimeLayer.addTo(map);
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
                        //var d = document.getElementById('chart');
                        //d.innerHTML =data;
                        mychart=Highcharts.chart('chart',{
                            chart: {
                                type: 'spline'
                            },
                            title: {
                                text: 'Well drawdown at Well ' +feature.properties.HydroID+", located at "+feature.geometry.coordinates
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
                                    text: 'Well Drawdown (ft)'}
                            },
                            series: [{
                                data: data,
                                name: "Well Drawdown (ft)"

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
        well_group.addLayer(well_layer);
        interpolation_group.addLayer(testTimeLayer);
        interpolation_group.addTo(map);

        testLegend.onAdd = function(map) {
        var colormin=-500;
        var colormax=0;
        if (region_number==28){
              colormin=-1000;
        }
        var src=testWMS+"?REQUEST=GetLegendGraphic&LAYER=depth&PALETTE=grace&COLORSCALERANGE="+colormin+","+colormax;
        var div = L.DomUtil.create('div', 'info legend');
        div.innerHTML +=
            '<img src="' + src + '" alt="legend">';
        return div;
        };
        testLegend.addTo(map);
    }
    else {
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
                        //var d = document.getElementById('chart');
                        //d.innerHTML =data;
                        mychart=Highcharts.chart('chart',{
                            chart: {
                                type: 'spline'
                            },
                            title: {
                                text: 'Well drawdown at Well ' +feature.properties.HydroID+", located at "+feature.geometry.coordinates
                            },
                            xAxis: {
                                type: 'datetime',

                                title: {
                                    text: 'Date'
                                }
                            },
                            yAxis:{
                                title: {
                                    text: 'Well Drawdown (ft)'}
                            },
                            series: [{
                                data: data,
                                name: "Well Drawdown (ft)"

                            }]
                        });
                    }

                });

                layer.bindPopup(popup_content);
            },
            pointToLayer:function(geoJsonPoint, latlng){
                return L.circleMarker(latlng,{radius:1, color:color});
        }
        });
        well_group.addLayer(well_layer);
    }
    //testTimeLayer.addTo(map);


    well_group.addTo(map);



    document.getElementById('waiting_output').innerHTML = '';
}

//}
function showraster(){
    var region_number=$("#select_aquifer").find('option:selected').val();
    region_number=Number(region_number);
    var aquifers=['Hueco Bolson','West Texas Bolsons','Pecos Valley','Seymour','Brazos River Alluvium','Blaine','Blossom','Bone Spring-Victorio Peak','Capitan Reef Complex','Carrizo','Edwards','Edwards-Trinity-High Plains','Edwards-Trinity','Ellenburger-San-Aba','Gulf Coast','Hickory','Igneous','Maratho','Marble Falls','Nacatoch','Ogallala','None','Rita Blanca','Queen City','Rustler','Dockum','Sparta','Trinity','Woodbine','Lipan','Yegua Jackson','Texas'];
    var name=aquifers[region_number-1];
    name=name.replace(/ /g,"_");
    var interpolation_type=$("#select_interpolation").find('option:selected').val();
    $.ajax({
        url: '/apps/gw/checkdata/',
        type: 'GET',
        data: {'name':name,'interpolation_type':interpolation_type},
        contentType: 'application/json',
        error: function (status) {

        }, success: function (response) {
            var exists=Number(response['exists']);
            if (exists==0){
                var wait_text = "<strong>Loading Data...</strong><br>" + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src='/static/gw/images/loading.gif'>";
                document.getElementById('waiting_output').innerHTML = wait_text;
                var min_num=$("#required_data").val();
                var id=region_number;
                var interpolation_type=$("#select_interpolation").find('option:selected').val();
                $.ajax({
                    url: '/apps/gw/loaddata/',
                    type: 'GET',
                    data: {'id':id,'min_num':min_num, 'name':name,'interpolation_type':interpolation_type},
                    contentType: 'application/json',
                    error: function (status) {

                    }, success: function (response) {
                        var well_points=response['data'];//.features;
                        var interpolation_type=$("#select_interpolation").find('option:selected').val();
                        var testWMS="http://tethys.byu.edu:7000/thredds/wms/testAll/groundwater/"+interpolation_type+"/"+name+".nc";
                        //var testWMS="http://localhost:8080/thredds/wms/testAll/groundwater/"+interpolation_type+"/"+name+".nc";
                        var colormin=-500;
                        var colormax=0;
                        if (id==28){
                            colormin=-1000;
                        }
                        var testLayer = L.tileLayer.wms(testWMS, {
                            layers: 'depth',
                            format: 'image/png',
                            transparent: true,
                            opacity:0.5,
                            colorscalerange=colormin+','+colormax,
                            attribution: '<a href="https://www.pik-potsdam.de/">PIK</a>'
                        });
                        var testTimeLayer = L.timeDimension.layer.wms(testLayer, {
                        });
                        interpolation_group.addLayer(testTimeLayer);
                        interpolation_group.addTo(map);


                        testLegend.onAdd = function(map) {
                            var src=testWMS+"?REQUEST=GetLegendGraphic&LAYER=depth&PALETTE=grace&COLORSCALERANGE="+colormin+","+colormax;
                            var div = L.DomUtil.create('div', 'info legend');
                            div.innerHTML +=
                                '<img src="' + src + '" alt="legend">';
                            return div;
                        };
                        testLegend.addTo(map);
                        document.getElementById('waiting_output').innerHTML = '';
                    }
                })
            }
            else{
                var interpolation_type=$("#select_interpolation").find('option:selected').val();
                var id=region_number;
                var testWMS="http://tethys.byu.edu:7000/thredds/wms/testAll/groundwater/"+interpolation_type+"/"+name+".nc";
                //var testWMS="http://localhost:8080/thredds/wms/testAll/groundwater/"+interpolation_type+"/"+name+".nc";
                var colormin=-500;
                        var colormax=0;
                        if (id==28){
                            colormin=-1000;
                        }
                var testLayer = L.tileLayer.wms(testWMS, {
                    layers: 'depth',
                    format: 'image/png',
                    transparent: true,
                    opacity:0.5,
                    colorscalerange=colormin+','+colormax,
                    attribution: '<a href="https://www.pik-potsdam.de/">PIK</a>'
                });
                var testTimeLayer = L.timeDimension.layer.wms(testLayer, {
                });
                interpolation_group.addLayer(testTimeLayer);
                interpolation_group.addTo(map);


                testLegend.onAdd = function(map) {
                    var src=testWMS+"?REQUEST=GetLegendGraphic&LAYER=depth&PALETTE=grace&COLORSCALERANGE="+colormin+","+colormax;
                    var div = L.DomUtil.create('div', 'info legend');
                    div.innerHTML +=
                        '<img src="' + src + '" alt="legend">';
                    return div;
                };
                testLegend.addTo(map);
                document.getElementById('waiting_output').innerHTML = '';
            }
        }
    })

}



