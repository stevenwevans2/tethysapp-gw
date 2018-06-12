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






var regioncenter=[30.0,-100.0];

//add a map to the html div "map" with time dimension capabilities. Times are currently hard coded, but will need to be changed as new GRACE data comes
var map = L.map('map', {
    crs: L.CRS.EPSG4326,
    zoom: 4,
    fullscreenControl: true,
    timeDimension: true,
    timeDimensionOptions:{

			 //times:"2000-01-01T00:00:00.000Z,2001-01-01T00:00:00.000Z"//,2002-01-01T00:00:00.000Z",
			 timeInterval:"1950-01-01/2015-01-01",
			 period:"P5Y"
			 //currentTime:"2000-01-01T00:00:00.000Z"
    },
    timeDimensionControl: true,
    center: regioncenter,
});

//add the background imagery
var wmsLayer = L.tileLayer.wms('https://demo.boundlessgeo.com/geoserver/ows?', {
    layers: 'nasa:bluemarble'
}).addTo(map);

var testLegend = L.control({
    position: 'topright'
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

    var region_number=$("#select_aquifer").find('option:selected').val();
    region_number=Number(region_number);
    displaygeojson(region_number,loadjson);
};

function clearwells(){
    well_group.clearLayers();
    aquifer_group.clearLayers();
    interpolation_group.clearLayers();
}

//This is the new function that I am working on
function displaygeojson(region_number, nextfunction) {
    var geolayer = 'MajorAquifers.json';
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
                    if (AquiferShape.length>0){
                        var AquiferLayer=L.geoJSON(AquiferShape//,{
//                            onEachFeature: function (feature, layer){
//                            if (feature.properties.AQ_NAME){
//                                //Major Aquifer
//                                popup_content=feature.properties.AQ_NAME +"<br>"+"Major Aquifer";
//                            }
//                            else{
//                                popup_content=feature.properties.AQU_NAME +"<br>"+"Minor Aquifer";
//                            }
//                            layer.bindPopup(popup_content);
//                            }
//                        }
                        );
                        aquifer_group.addLayer(AquiferLayer);
                    }
                    aquifer_group.addTo(map);

                    min_num=$("#required_data").val();
                    geolayer=region_number;
                    $.ajax({
                        url: '/apps/gw/retrieve_Wells/',
                        type: 'GET',
                        data: {'geolayer':geolayer,'min_num':min_num},
                        contentType: 'application/json',
                        error: function (status) {

                        }, success: function (response) {
                            var well_points=response;//.features;
                            nextfunction(region_number, well_points);
                        }
                    })
                }
            })
        }
    })


}

//This is the new function I am working on for the persistent store method
function loadjson(region_number, well_points) {

    var colors=['blue','red','yellow','green','orange','purple'];
    var aquifers=['Hueco Bolson','West Texas Bolsons','Pecos Valley','Seymour','Brazos River Alluvium','Blaine','Blossom','Bone Spring-Victorio Peak','Capitan Reef Complex','Carrizo','Edwards','Edwards-Trinity (High Plains)','Edwards-Trinity','Ellenburger-San-Aba','Gulf Coast','Hickory','Igneous','Maratho','Marble Falls','Nacatoch','Ogallala','None','Rita Blanca','Queen City','Rustler','Dockum','Sparta','Trinity','Woodbine','Lipan','Yegua Jackson'];
    num=region_number%6;
    var color=colors[num];
    var aquifer=aquifers[region_number-1];
    var required=$("#required_data").val();
    var time_points='{"type":"FeatureCollection","features":[]}';
    time_points=JSON.parse(time_points);
    if (required==0){
        popup_layer(well_points,color,aquifer);
    }
    else{
        for (i=0, ilength=well_points.features.length;i<ilength;i++){
            if (well_points.features[i].timeseries){
                if (well_points.features[i].timeseries.TsTime.length>=required){
                    time_points.features.push(well_points.features[i]);
                }
            }

        }
        popup_layer(time_points,color,aquifer);
    }
    function popup_layer(points,color,aquifer){
	var iterationyear=1950;
	var grid=[];
	var aquifermin=0;
	for (x=0;x<points.features.length;x++){
	    for (y=0;y<points.features[x].timeseries.TsTime.length;y++){
	        if (points.features[x].timeseries.TsValue[y]<aquifermin){
	            aquifermin=points.features[x].timeseries.TsValue[y];
	        }
	    }
	}
	for (iteration=0;iteration<14;iteration++){
//	    var interp_points='{"type":"FeatureCollection","features":[]}';
//        interp_points=JSON.parse(interp_points);
		var well_layer=L.geoJSON(points,{
		    onEachFeature: function (feature, layer){
		        var data=[];
		        var interpdata=[];
		        var popup_content="Hydro ID: "+feature.properties.HydroID;
		        popup_content+="<br>"+"Aquifer: "+aquifer;
		        popup_content+="<br>"+"Elevation: "+feature.properties.LandElev + " feet";
		        popup_content+="<br>"+"Well Depth: "+feature.properties.WellDepth + " feet";
		        var j=0;
		        console.log("another feature");
		        if (feature.timeseries){
		            for (i=0;i<feature.timeseries.TsTime.length;i++){
		                    var this_time = new Date();
		                    var this_data = null;
		                    //var norm_data=null;
		                    this_time = feature.timeseries.TsTime[i];
		                    //time is currently in format 3/14/2001  12:00:00 AM
		                    var pos=this_time.indexOf("/");
		                    var pos2=this_time.indexOf("/",pos+1);
		                    var month=this_time.substring(0,pos);
		                    var day=this_time.substring(pos+1,pos2);
		                    var year=this_time.substring(pos2+1,pos2+5);
		                    month=Number(month)-1;
		                    year=Number(year);
		                    day=Number(day);
		                    this_time=Date.UTC(year,month,day);

		                    this_data = feature.timeseries.TsValue[i];
		                    //norm_data = feature.timeseries.TsValue_normalized[i];
		                    data[j] = [this_time,this_data];
		                    //interpdata[j]=[this_time,norm_data];
		                    interpdata[j]=[this_time,this_data];
		                    j++;
		            }
		        }
		        popup_content+="<br>"+"Number of well samplings: "+j;
		        data.sort(function(a, b){return a[0] - b[0]});
		        interpdata.sort(function(a, b){return a[0] - b[0]});

		        //attempt interpolation
		        var target_time=Date.UTC(iterationyear,0,1);
		        var listlength=j;
		        var location=0;
		        var tlocation=0;
		        var stop_location=0;
		        var timedelta=1000000000000000000;
		        var fiveyears=157680000000;//5*365*24*60*60*1000;
		        var timevalue=null;
		        var slope=0;

		        if (listlength>0){

                    for (i=0;i<listlength;i++){
                        if (interpdata[i][0]>=target_time && stop_location==0){
                            tlocation=i;
                            stop_location=1;
                        }
                    }
                    //target time is larger than max date
                    if (tlocation==0 && stop_location==0){
                        tlocation=-999;
                    }
                    //target time is smaller than max date
                    if (tlocation==0 && stop_location==1){
                        tlocation=-888;
                    }

                    //for the case where the target time is in the middle
                    if (tlocation>=0){
                        timedelta=target_time-interpdata[tlocation-1][0];
                        slope=(interpdata[tlocation][1]-interpdata[tlocation-1][1])/(interpdata[tlocation][0]-interpdata[tlocation-1][0]);
                        timevalue=interpdata[tlocation-1][1]+slope*timedelta;
                        feature.properties.timevalue=timevalue;
                    }

                    //for the case where the target time is before
                    if (tlocation==-888){
                        timedelta=interpdata[0][0]-target_time;
                        if (timedelta>fiveyears){
                            feature.properties.timevalue=interpdata[0][1];//null;
                        }
                        else if(listlength>1){
                            slope=(interpdata[1][1]-interpdata[0][1])/(interpdata[1][0]-interpdata[0][0]);
                            if (Math.abs(slope)>(1.0/(24*60*60*1000))){
                                timevalue=interpdata[0][1];
                            }
                            else{
                                timevalue=interpdata[0][1]-slope*timedelta;
                            }
                            if (timevalue>0){
                                timevalue=interpdata[0][1];
                            }
                            feature.properties.timevalue=timevalue;
                        }
                        else{
                            feature.properties.timevalue=interpdata[0][1];
                        }
                        if (feature.properties.timevalue<aquifermin){
                            feature.properties.timevalue=interpdata[0][1];
                        }
                    }
                    //for the case where the target time is after
                    if (tlocation==-999){
                        timedelta=target_time-interpdata[listlength-1][0];
                        if (timedelta>fiveyears){
                            feature.properties.timevalue=interpdata[listlength-1][1];//null;
                        }
                        else if(listlength>1){
                            slope=(interpdata[listlength-1][1]-interpdata[listlength-2][1])/(interpdata[listlength-1][0]-interpdata[listlength-2][0]);
                            if (Math.abs(slope)>(1.0/(24*60*60*1000))){
                                timevalue=interpdata[listlength-1][1];
                            }
                            else{
                                timevalue=interpdata[listlength-1][1]+slope*timedelta;
                            }
                            if (timevalue>0){
                                timevalue=interpdata[listlength-1][1];
                            }
                            feature.properties.timevalue=timevalue;
                        }
                        else{
                            feature.properties.timevalue=interpdata[listlength-1][1];
                        }
                        if (feature.properties.timevalue<aquifermin){
                            feature.properties.timevalue=interpdata[listlength-1][1];
                        }
                    }
                    popup_content+="<br>"+"Depth at " +iterationyear+": "+feature.properties.timevalue + " feet";
                }
                else{
                    feature.properties.timevalue=null;
                }

//                if (feature.properties.timevalue!=null){
//                    interp_points.features.push(feature);
//                }

		        //make a high charts
		        layer.on({
		            click: function showResultsInDiv() {
		                //var d = document.getElementById('chart');
		                //d.innerHTML =data;
		                Highcharts.chart('chart',{
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
		var options={gridType: 'points', property: 'timevalue', units: 'miles',weight:2};
		grid[iteration]=turf.interpolate(points,5,options);// maybe do with interp_points


		geolayer=JSON.stringify(grid[iteration]);
		name=aquifer;
		console.log(geolayer);
		$.ajax({
		    url: '/apps/gw/savejson/',
		    type: 'POST',
		    data: {'geolayer':geolayer,'name':name,'iteration':iteration},
		    contentType: 'application/x-www-form-urlencoded',
		    error: function (status) {

		    }, success: function (response) {
		        console.log("success")
		    }
		})
		iterationyear+=5;
	}
	
        well_group.addLayer(well_layer);
        well_group.addTo(map);
        document.getElementById('waiting_output').innerHTML = '';
        name=name.replace(" ","_");

        var testWMS="http://localhost:8080/thredds/wms/testAll/groundwater/"+name+".nc";
        var testLayer = L.tileLayer.wms(testWMS, {
            layers: 'depth',
            format: 'image/png',
            transparent: true,
            opacity:0.5,
            attribution: '<a href="https://www.pik-potsdam.de/">PIK</a>'
        });
        var testTimeLayer = L.timeDimension.layer.wms(testLayer, {
            //updateTimeDimension: true,
	        //setDefaultTime: true,
        });
        //testTimeLayer.addTo(map);
        interpolation_group.addLayer(testTimeLayer);
        interpolation_group.addTo(map);

        testLegend.onAdd = function(map) {
            var src=testWMS+"?REQUEST=GetLegendGraphic&LAYER=depth&PALETTE=grace";
            var div = L.DomUtil.create('div', 'info legend');
            div.innerHTML +=
                '<img src="' + src + '" alt="legend">';
            return div;
        };
        testLegend.addTo(map);
    };

}
