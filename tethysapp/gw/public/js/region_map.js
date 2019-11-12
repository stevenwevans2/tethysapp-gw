//var thredds_url="https://tethys2.byu.edu/thredds/wms/testAll/groundwater/";
//var thredds_url = "http://localhost:8080/thredds/wms/testAll/groundwater/";
var units = "Metric"

//Get a CSRF cookie for request
//I am not sure that these 3 funtions actually do. I don't understand them. I just got some error message when I tried to run the app without them
// and then I copied these lines of code in from the GRACE app and it fixed it.
function getCookie(name) {
    var cookieValue = null
    if (document.cookie && document.cookie != "") {
        var cookies = document.cookie.split(";")
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i])
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == name + "=") {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
                break
            }
        }
    }
    return cookieValue
}

//find if method is csrf safe
function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return /^(GET|HEAD|OPTIONS|TRACE)$/.test(method)
}

//add csrf token to appropriate ajax requests
$(function() {
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", getCookie("csrftoken"))
            }
        }
    })
}) //document ready

//THis code edits the leaflet LayerGroup to include an id, that way a layer group can be reselected elsewhere in the code based on an assigned id
L.LayerGroup.include({
    customGetLayer: function(id) {
        for (var i in this._layers) {
            if (this._layers[i].id == id) {
                return this._layers[i]
            }
        }
    }
})

//This function is called when a new raster animation is selected on the app Regional Map page.
//The function clears the displayed Raster layers and then adds new raster layers based on the selected raster animation.
//The function calls the getLayerMinMax function to determine the bounds of the new raster and adjust the symbology and legend accordingly.
//The rasters are displayed using the leaflet time dimension and display netcdf files stored on the thredds server specified by the
// global variable "thredds_url" at the beginning of this page.
function changeWMS() {
    //    name is the filename of the netcdf file what will be displayed
    var name = $("#available_dates")
        .find("option:selected")
        .val()
    name = name.replace(/ /g, "_")
    clearwaterlevels()
    //    THe NetCDF files are organized by region on the Thredds server, so the region must be specified to find the proper directory on the THREDDS server
    var region = $("#select_region")
        .find("option:selected")
        .val()

    //    format the url for the file on the THREDDS server
    var testWMS = thredds_url + region + "/" + name
    if (name == "Blank.nc") {
        testWMS = thredds_url + "/" + name
    }

    var colormin = $("#col_min").val()
    var colormax = $("#col_max").val()
    var opac = $("#opacity_val").val()
    var wmsLayer = $("#select_view")
        .find("option:selected")
        .val()
    var palette = $("#select_symbology")
        .find("option:selected")
        .val()

    //    testLayer is a wms of the raster of groundwater levels from the specified NetCDF on the Thredds server
    var testLayer = L.tileLayer.wms(testWMS, {
        layers: wmsLayer,
        format: "image/png",
        transparent: true,
        opacity: opac,
        styles: "boxfill/" + palette,
        colorscalerange: colormin + "," + colormax,
        attribution: '<a href="https://ceen.et.byu.edu/">BYU</a>'
    })
    //    contourLayer is a wms of the contours of groundwater levels from the specified NetCDF on the Thredds server
    var contourLayer = L.tileLayer.wms(testWMS, {
        layers: wmsLayer,
        crs: L.CRS.EPSG4326,
        format: "image/png",
        transparent: true,
        colorscalerange: colormin + "," + colormax,
        styles: "contour/" + palette,
        attribution: '<a href="https://ceen.et.byu.edu/">BYU</a>'
    })
    var testTimeLayer = L.timeDimension.layer.wms(testLayer, {
        cache: 50
    })

    var url =
        thredds_url +
        region +
        "/" +
        name +
        "?service=WMS&version=1.3.0&request=GetCapabilities"
    if (name == "Blank.nc") {
        url =
            thredds_url +
            "/" +
            name +
            "?service=WMS&version=1.3.0&request=GetCapabilities"
    }

    //    This oreq function gets a string of the available times from the time dimension of the NetCDF file and stores them in the variable "substring"
    // Then the function updates the time dimension of the WMS layer accodingly.
    //Then the function calls getLayerMinMax, which determines the min and max values of a netCDF dataset on the Thredds server
    var oReq = new XMLHttpRequest()
    oReq.addEventListener("load", function(xhr) {
        var response = xhr.currentTarget.response
        pos1 = response.indexOf("T00:00:00.000Z") + 1
        pos2 = response.indexOf("T00:00:00.000Z", pos1) - 10
        pos3 = response.indexOf(">", pos2)
        pos4 = response.indexOf("<", pos2)
        pos3 = Math.min(pos3, pos4)
        substring = response.substring(pos2, pos3)
        map.timeDimension.setAvailableTimes(substring, "replace")
        //document.getElementById('waiting_output').innerHTML = '';
        getLayerMinMax(
            wmsLayer,
            testLayer,
            contourLayer,
            testWMS,
            addLegend,
            testTimeLayer
        )
    })
    oReq.open("GET", url)
    oReq.send()

    //getLayerMinMax(wmsLayer,testLayer,contourLayer,testWMS,addLegend,testTimeLayer);
}

//This function is called when the min, max, and opacity boxes are adjusted on the app Regional Map page. This function clears the netCDF rasters and legend
// and then reloads the rasters and legend from the Thredds Server with the specified changes to the symbology.
function updateWMS() {
    //    name is the filename of the netcdf file what will be displayed
    var name = $("#available_dates")
        .find("option:selected")
        .val()
    name = name.replace(/ /g, "_")
    clearwaterlevels()
    //    THe NetCDF files are organized by region on the Thredds server, so the region must be specified to find the proper directory on the THREDDS server
    var region = $("#select_region")
        .find("option:selected")
        .val()
    //testWMS is the url for the NetCDF file on the THREDDS server
    var testWMS = thredds_url + region + "/" + name
    if (name == "Blank.nc") {
        testWMS = thredds_url + "/" + name
    }

    var colormin = $("#col_min").val()
    var colormax = $("#col_max").val()
    var opac = $("#opacity_val").val()
    var wmsLayer = $("#select_view")
        .find("option:selected")
        .val()
    var palette = $("#select_symbology")
        .find("option:selected")
        .val()

    //    testLayer is a wms of the raster of groundwater levels from the specified NetCDF on the Thredds server
    var testLayer = L.tileLayer.wms(testWMS, {
        layers: wmsLayer,
        format: "image/png",
        transparent: true,
        opacity: opac,
        styles: "boxfill/" + palette,
        colorscalerange: colormin + "," + colormax,
        attribution: '<a href="https://ceen.et.byu.edu/">BYU</a>'
    })
    //    contourLayer is a wms of the contours of groundwater levels from the specified NetCDF on the Thredds server
    var contourLayer = L.tileLayer.wms(testWMS, {
        layers: wmsLayer,
        crs: L.CRS.EPSG4326,
        format: "image/png",
        transparent: true,
        colorscalerange: colormin + "," + colormax,
        styles: "contour/" + palette,
        attribution: '<a href="https://ceen.et.byu.edu/">BYU</a>'
    })
    var testTimeLayer = L.timeDimension.layer.wms(testLayer, {
        cache: 50
    })
    //THis code adds a legend for the raster to the map
    testLegend.onAdd = function(map) {
        var src =
            testWMS +
            "?REQUEST=GetLegendGraphic&LAYER=" +
            wmsLayer +
            "&PALETTE=" +
            palette +
            "&COLORSCALERANGE=" +
            colormin +
            "," +
            colormax
        var div = L.DomUtil.create("div", "info legend")
        div.innerHTML += '<img src="' + src + '" alt="legend">'
        return div
    }
    testLegend.addTo(map)
    var contourTimeLayer = L.timeDimension.layer.wms(contourLayer, {
        cache: 50
    })
    testTimeLayer.id = "timelayer"
    interpolation_group.addLayer(testTimeLayer)
    contour_group.addLayer(contourTimeLayer)

    var url =
        thredds_url +
        region +
        "/" +
        name +
        "?service=WMS&version=1.3.0&request=GetCapabilities"
    if (name == "Blank.nc") {
        url =
            thredds_url +
            "/" +
            name +
            "?service=WMS&version=1.3.0&request=GetCapabilities"
    }

    //    This oreq function gets a string of the available times from the time dimension of the NetCDF file and stores them in the variable "substring"
    // Then the function updates the time dimension of the WMS layer accodingly.
    //Then the function calls getLayerMinMax, which determines the min and max values of a netCDF dataset on the Thredds server
    var oReq = new XMLHttpRequest()
    oReq.addEventListener("load", function(xhr) {
        var response = xhr.currentTarget.response
        pos1 = response.indexOf("T00:00:00.000Z") + 1
        pos2 = response.indexOf("T00:00:00.000Z", pos1) - 10
        pos3 = response.indexOf(">", pos2)
        pos4 = response.indexOf("<", pos2)
        pos3 = Math.min(pos3, pos4)
        substring = response.substring(pos2, pos3)
        map.timeDimension.setAvailableTimes(substring, "replace")
        document.getElementById("waiting_output").innerHTML = ""
    })
    oReq.open("GET", url)
    oReq.send()
}

//This function is called by the getLayerMinMax function and adds a legend to the map as well as contour symbology
var addLegend = function(
    testWMS,
    contourLayer,
    testLayer,
    colormin,
    colormax,
    layer,
    testTimeLayer
) {
    var palette = $("#select_symbology")
        .find("option:selected")
        .val()
    if (testWMS.includes("Blank.nc") == false) {
        testLegend.onAdd = function(map) {
            var src =
                testWMS +
                "?REQUEST=GetLegendGraphic&LAYER=" +
                layer +
                "&PALETTE=" +
                palette +
                "&COLORSCALERANGE=" +
                colormin +
                "," +
                colormax
            var div = L.DomUtil.create("div", "info legend")
            div.innerHTML += '<img src="' + src + '" alt="legend">'
            return div
        }
        testLegend.addTo(map)
    }
    var contourTimeLayer = L.timeDimension.layer.wms(contourLayer, {
        cache: 50
    })
    testTimeLayer.id = "timelayer"
    interpolation_group.addLayer(testTimeLayer)
    interpolation_group.addTo(map)
    contour_group.addLayer(contourTimeLayer)
    contour_group.addTo(map)
    toggle.removeLayer(contour_group, "Contours")
    toggle.addOverlay(contour_group, "Contours")
}

//This function determines the min and max values of a netCDF dataset on the Thredds server and
//updates the symbology of the rasters and calls the addLegend function
var getLayerMinMax = function(
    layer,
    testLayer,
    contourWMS,
    testWMS,
    callback,
    testTimeLayer
) {
    var url = testWMS + "?service=WMS&version=1.1.1&request=GetMetadata&item=minmax"
    url = url + "&layers=" + testLayer.options.layers
    url = url + "&srs=EPSG:4326" //4326
    //size is a global variable obtained from var size = map.getSize();
    bounds = region_group.getBounds().toBBoxString()

    url = url + "&BBox=" + bounds //"-360.0,-90.0,360.0,90.0";//bounds
    url = url + "&height=" + 1000 //size.y
    url = url + "&width=" + 1000 //size.x

    var oReq = new XMLHttpRequest()
    oReq.addEventListener("load", function(xhr) {
        var response = xhr.currentTarget.response
        var data = JSON.parse(response)
        var range = data.max - data.min
        var min = Math.round(data.min / 100.0) * 100
        var max = Math.round(data.max / 100.0) * 100

        if (min == max) {
            min -= 50
            max += 50
        }
        if (min > data.min) {
            min -= 50
        }
        if (max < data.max) {
            max += 50
        }
        //        if (layer=="drawdown"){
        //            max=min*-1;
        //        }
        testLayer.options.colorscalerange = min + "," + max
        testLayer.wmsParams.colorscalerange = min + "," + max
        contourWMS.options.colorscalerange = min + "," + max
        contourWMS.wmsParams.colorscalerange = min + "," + max
        document.getElementById("col_min").value = min
        document.getElementById("col_max").value = max

        if (callback != undefined) {
            callback(testWMS, contourWMS, testLayer, min, max, layer, testTimeLayer)
        }
    })
    oReq.open("GET", url)
    oReq.send()
}

//THese two buttons are hidden by default, but become visible if certain criteria are met
document.getElementById("buttons").style.display = "none"
document.getElementById("volbut").style.display = "none"
var regioncenter = [31.2, -100.0]
var mychart = []
//add a map to the html div "map" with time dimension capabilities. T
var map = L.map("map", {
    crs: L.CRS.EPSG3857, //4326
    zoom: 5,
    fullscreenControl: true,
    timeDimension: true,
    timeDimensionControl: true,
    timeDimensionControlOptions: {
        loopButton: true,
        playerOptions: {
            loop: true
        }
    },
    center: regioncenter
})

//These two variables are global variables specifying the size and bounds of the overall region. This is used in the getLayerMinMax function.
var region = $("#select_region")
    .find("option:selected")
    .val()
var size = map.getSize()
var bounds = map.getBounds().toBBoxString()
//add the background imagery
//var wmsLayer = L.tileLayer.wms('https://demo.boundlessgeo.com/geoserver/ows?', {
//    //layers: 'nasa:bluemarble'
//    layers:'ne:NE1_HR_LC_SR_W_DR'
//}).addTo(map);
var StreetMap = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution:
        '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map)
//var TopoMap = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
//    maxZoom: 17,
//    attribution: 'Map data: &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
//});

//Define leaflet layergroups (rasters) and featuregroups (shpaefiles)
var region_group = L.featureGroup()
var well_group = L.featureGroup()
var aquifer_group = L.featureGroup()
var minor_group = L.featureGroup()
var major_group = L.featureGroup()
var interpolation_group = L.layerGroup()
var contour_group = L.layerGroup()
var overlayMaps = {}
var toggle = L.control.layers(null, overlayMaps).addTo(map)

//This ajax controller loads the JSON file for the Region boundary and adds it to the map
var geolayer = region + "_State_Boundary.json"
var region = $("#select_region")
    .find("option:selected")
    .val()
//Calls python code in the ajax_controllers.py. Calls the displaygeojson function, which returns json objects of the
//region and aquifer boundaries in the response['state'], response['major'], and response['minor'] dict
$.ajax({
    url: apiServer + "displaygeojson/",
    type: "GET",
    data: { geolayer: geolayer, region: region },
    contentType: "application/json",
    error: function(status) {},
    success: function(response) {
        //  Code to add the region boundary (texasboundary) to the region_group and then add to the map
        texasboundary = response["state"].features
        texasborder = L.geoJSON(texasboundary, {
            color: "red",
            weight: 1,
            fillOpacity: 0.0
        })
        region_group.addLayer(texasborder)
        region_group.addTo(map)
        //        Code to add any major aquifers to the major_group and then add to the map
        if (response["major"]) {
            major = response["major"]
            majoraquifers = L.geoJSON(major, {
                weight: 1,
                fillOpacity: 0.2,
                onEachFeature: function(feature, layer) {
                    //Hovering over the layer will display the aquifer name
                    tooltip_content = "Major Aquifer: " + feature.properties.Name
                    layer.bindTooltip(tooltip_content, { sticky: true })
                    //                  Clicking on the layer will select that aquifer and will zoom to it and display its wells by calling the list_dates(2) function
                    layer.on({
                        click: function jumpaquifer() {
                            $("#select_aquifer").val(feature.properties.Id)
                            document.getElementById(
                                "select2-select_aquifer-container"
                            ).innerHTML = $("#select_aquifer")
                                .find("option:selected")
                                .text()
                            list_dates(2)
                        }
                    })
                }
            })
            majoraquifers.addTo(major_group)
            major_group.addTo(map)
            toggle.addOverlay(major_group, "Major Aquifers")
        }
        //        Code to add any major aquifers to the major_group and then add to the map
        if (response["minor"]) {
            minor = response["minor"]
            minoraquifers = L.geoJSON(minor, {
                color: "green",
                weight: 1,
                fillOpacity: 0.2,
                onEachFeature: function(feature, layer) {
                    //Hovering over the layer will display the aquifer name
                    tooltip_content = "Minor Aquifer: " + feature.properties.Name
                    layer.bindTooltip(tooltip_content, { sticky: true })
                    //                  Clicking on the layer will select that aquifer and will zoom to it and display its wells by calling the list_dates(2) function
                    layer.on({
                        click: function jumpaquifer() {
                            $("#select_aquifer").val(feature.properties.Id)
                            document.getElementById(
                                "select2-select_aquifer-container"
                            ).innerHTML = $("#select_aquifer")
                                .find("option:selected")
                                .text()
                            list_dates(2)
                        }
                    })
                }
            })
            minoraquifers.addTo(minor_group)
            minor_group.addTo(map)
            toggle.addOverlay(minor_group, "Minor Aquifers")
        }
    }
})
//Code to define and add a legend to the map display. testLegend is the legend for raster coloring of the NetCDF
var testLegend = L.control({
    position: "bottomright"
})
//legend is a legend in the bottom left corner that defines the different types of wells
var legend = L.control({ position: "bottomleft" })
legend.onAdd = function(map) {
    var div = L.DomUtil.create("div", "info_legend")
    ;(labels = ["<strong>Legend</strong>"]),
        labels.push(
            '<span class="greenwell"></span> Wells with Data spanning Time Period'
        )
    labels.push('<span class="bluewell"></span> Wells with Data in Time Period')
    labels.push('<span class="greywell"></span> Wells with no Data in Time Period')
    labels.push('<span class="redwell"></span> Wells with Data Outliers')
    div.innerHTML = labels.join("<br>")
    return div
}
//Code to remove the well type legend if the wells are removed from the display
//plus code to remove the raster legend if the raster is removed from the display
map.on("overlayremove", function(e) {
    if (e.name === "Wells") {
        legend.remove()
    }
    if (e.name === "Water Table Surface") {
        testLegend.remove()
    }
})
//Code to add the well legend to the map if the wells are added to the display
//plus code to add the raster legend to the map if the raster is added to the display
map.on("overlayadd", function(e) {
    if (e.name === "Wells") {
        legend.addTo(map)
    }
    var aq = $("#available_dates")
        .find("option:selected")
        .val()
    if (e.name === "Water Table Surface" && aq != "Blank.nc") {
        testLegend.addTo(map)
    }
})

//This function is called when the amount of wells visible changes
function change_filter() {
    if (
        $("#select_aquifer")
            .find("option:selected")
            .val() != 9999
    ) {
        change_aquifer()
    }
}

//This function is called when the aquifer is changed in the Select Aquifer dropdown.
function change_aquifer() {
    //    remove the blank option that is currently selected when no aquifer is selected yet
    $("#select_aquifer option[value=9999]").remove()
    //    remove the timeseries shown in the chart below the map
    document.getElementById("chart").innerHTML = ""
    //    display loading pinwheel
    var wait_text =
        "<strong>Loading Data...</strong><br>" +
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src='/static/gw/images/loading.gif'>"
    document.getElementById("waiting_output").innerHTML = wait_text
    //    call these two functions to remove all the features from the old aquifer from the map
    clearwells()
    clearwaterlevels()
    //Code checks whether there area any rasters for the aquifer. Then calls the displaygeojson function
    aquifer_number = $("#select_aquifer")
        .find("option:selected")
        .val()
    aq_name = $("#available_dates")
        .find("option:selected")
        .val()
    if (typeof aq_name == "undefined") {
        document.getElementById("waiting_output").innerHTML = ""
        alert("The selected aquifer does not have any associated interpolation rasters .")
        return
    }
    aquifer_number = Number(aquifer_number)
    region = $("#select_region")
        .find("option:selected")
        .val()
    displaygeojson(aquifer_number, displayallwells)
}

function clearwells() {
    well_group.clearLayers()
    aquifer_group.clearLayers()
    document.getElementById("chart").innerHTML = ""
    minor_group.clearLayers()
    major_group.clearLayers()
    legend.remove()
}

function clearwaterlevels() {
    interpolation_group.clearLayers()
    contour_group.clearLayers()
    testLegend.remove()
}

//This function takes the aquifer_number and displayallwells as parameters.
//aquifer_number identifies the aquifer_number for which the function will perform
//Displayallwells is a callback funtcion to be called by this function
//THe Function calls the loadjson ajax controlled for a specified aquifer_number in a specified region
//THe ajax function returns the name of the aquifer (response['aquifer']) and the geojson object of the aquifer boundary (response['data'])
function displaygeojson(aquifer_number, displayallwells) {
    var region = $("#select_region")
        .find("option:selected")
        .val()
    //calls the loadjson ajax controller to open the aquifer shapefiles and return the appropriate geoJSON object for the aquifer
    $.ajax({
        url: apiServer + "loadjson/",
        type: "GET",
        data: { aquifer_number: aquifer_number, region: region },
        contentType: "application/json",
        error: function(status) {},
        success: function(response) {
            AquiferShape = response["data"]
            name = response["aquifer"]
            name = name.replace(/ /g, "_")
            var aquifer_center = []

            //find the center of the aquifer if an aquifer is selected. Add the aquifer to the map and zoom and pan to the center
            if (AquiferShape) {
                var AquiferLayer = L.geoJSON(AquiferShape, {
                    onEachFeature: function(feature, layer) {
                        feature.properties.bounds_calculated = layer.getBounds()
                        var latcenter =
                            (feature.properties.bounds_calculated._northEast.lat +
                                feature.properties.bounds_calculated._southWest.lat) /
                            2
                        var loncenter =
                            (feature.properties.bounds_calculated._northEast.lng +
                                feature.properties.bounds_calculated._southWest.lng) /
                            2
                        aquifer_center = [latcenter, loncenter]
                    },
                    fillOpacity: 0.0,
                    weight: 1
                })
                aquifer_group.addLayer(AquiferLayer)
                map.fitBounds(aquifer_group.getBounds())
            }
            //if no aquifer is loaded, zoom to the region boundaries
            else {
                map.fitBounds(region_group.getBounds())
            }

            aquifer_group.addTo(map)

            min_num = $("#required_data")
                .find("option:selected")
                .val()
            min_num = Number(min_num)
            id = aquifer_number

            var region = $("#select_region")
                .find("option:selected")
                .val()
            //        This code calls the ajax controller get_aquifer_wells for a specific aquifer_id in a specific region
            //          The code for get_aquifer_wells is in the model.py file
            //          The controller queries the database for the appropriate region and aquifer_id number and returns response['data']
            //          response['data'] is the geojson object of all wells in the aquifer with their properties and associated timeseries info
            $.ajax({
                url: apiServer + "get_aquifer_wells/",
                type: "GET",
                data: { aquifer_id: id, region: region },
                contentType: "application/json",
                error: function(status) {},
                success: function(response) {
                    var well_points = response["data"] //.features;
                    //calls displayallwells
                    displayallwells(aquifer_number, well_points, min_num)
                    //                    Update the options that will be shown on the layer togglke for the map
                    overlayMaps = {
                        "Aquifer Boundary": aquifer_group,
                        Wells: well_group,
                        "Water Table Surface": interpolation_group
                    }

                    toggle.remove()
                    toggle = L.control.layers(null, overlayMaps).addTo(map)
                }
            })
        }
    })
}
//This function displays all wells as a geojson object on the map
//Each well has functionality such that it will display its timeseries when it is clicked
function displayallwells(aquifer_number, well_points, required) {
    var length_unit = "m"
    var vol_unit = "Cubic Meters"
    if (units == "English") {
        length_unit = "ft"
        vol_unit = "Acre-ft"
    }
    var color = "blue"
    var aquifer = $("#select_aquifer")
        .find("option:selected")
        .text()
    var name = $("#available_dates")
        .find("option:selected")
        .val()

    legend.addTo(map)

    var points = '{"type":"FeatureCollection","features":[]}'
    points = JSON.parse(points)
    if (required > 0) {
        for (i = 0; i < well_points.features.length; i++) {
            if (well_points.features[i].TsTime) {
                if (well_points.features[i].TsTime.length >= required) {
                    points.features.push(well_points.features[i])
                }
            }
        }
    } else {
        points = well_points
    }

    name = name.replace(/ /g, "_")
    var region = $("#select_region")
        .find("option:selected")
        .val()

    var testWMS = thredds_url + region + "/" + name
    if (name == "Blank.nc") {
        testWMS = thredds_url + "/" + name
    }

    var colormin = -500
    var colormax = 0
    if (aquifer_number == 28) {
        colormin = -1000
    }
    var wmsLayer = $("#select_view")
        .find("option:selected")
        .val()
    var palette = $("#select_symbology")
        .find("option:selected")
        .val()

    var testLayer = L.tileLayer.wms(testWMS, {
        layers: wmsLayer,
        format: "image/png",
        transparent: true,
        opacity: 0.7,
        styles: "boxfill/" + palette,
        colorscalerange: colormin + "," + colormax,
        attribution: '<a href="https://ceen.et.byu.edu/>BYU</a>'
    })
    var contourLayer = L.tileLayer.wms(testWMS, {
        layers: wmsLayer,
        crs: L.CRS.EPSG4326,
        format: "image/png",
        transparent: true,
        colorscalerange: colormin + "," + colormax,
        styles: "contour/" + palette,
        attribution: '<a href="https://ceen.et.byu.edu/">BYU</a>'
    })
    var testTimeLayer = L.timeDimension.layer.wms(testLayer, {
        cache: 50
    })

    getLayerMinMax(wmsLayer, testLayer, contourLayer, testWMS, addLegend, testTimeLayer)

    var well_layer = L.geoJSON(points, {
        onEachFeature: function(feature, layer) {
            function getpopup_content() {
                var popup_content = "Hydro ID: " + feature.properties.HydroID
                if (feature.properties.FType) {
                    var type = feature.properties.FType
                    if (type == "W") {
                        type = "Water Withdrawal"
                    } else if (type == "P") {
                        type = "Petroleum"
                    } else if (type == "O") {
                        type = "Observation"
                    } else if (type == "M") {
                        type = "Mine"
                    }
                    popup_content += "<br>" + "Well Type: " + type
                }
                popup_content += "<br>" + "Aquifer: " + aquifer
                if (feature.properties.LandElev) {
                    if (feature.properties.LandElev != -9999) {
                        popup_content +=
                            "<br>" + "Elevation: " + feature.properties.LandElev + " feet"
                    } else {
                        feature.properties.LandElev = 0
                    }
                }

                if (feature.properties.WellDepth) {
                    popup_content +=
                        "<br>" + "Well Depth: " + feature.properties.WellDepth + " feet"
                }

                if (!feature.properties.Outlier || feature.properties.Outlier == false) {
                    var container =
                        '<a href="#" class=' +
                        feature.properties.HydroID +
                        ">Flag as Outlier</a>"
                    layer.setStyle({
                        color: "blue"
                    })
                } else {
                    var warning = "Outlier"
                    warning = warning.fontcolor("red").bold()
                    var container =
                        '<a href="#" class=' +
                        feature.properties.HydroID +
                        ">Unflag as Outlier</a>" +
                        "<br>" +
                        warning
                    layer.setStyle({
                        color: "red"
                    })
                }
                popup_content += "<br>" + container
                return popup_content
            }
            popup_content = getpopup_content()

            function set_color() {
                var yearstring = $("#available_dates")
                    .find("option:selected")
                    .text()
                if (yearstring == "No Raster") {
                    var first_date = new Date(1800, 0, 1)
                    var last_date = new Date(2020, 0, 1)
                } else {
                    var start = yearstring.indexOf(": ") + 1
                    var stop1 = yearstring.indexOf("-", start)
                    var stop2 = yearstring.indexOf(" (", stop1)
                    var first_date = Number(yearstring.substring(start, stop1))
                    var last_date = Number(yearstring.substring(stop1 + 1, stop2))
                    first_date = new Date(first_date, 0, 1)
                    last_date = new Date(last_date, 0, 1)
                }
                if (!feature.properties.Outlier || feature.properties.Outlier == false) {
                    if (feature.TsTime) {
                        if (
                            feature.TsTime[0] * 1000 <= first_date &&
                            feature.TsTime[feature.TsTime.length - 1] * 1000 >= last_date
                        ) {
                            layer.setStyle({
                                color: "green",
                                fillColor: "#ffffff",
                                radius: 2,
                                fillOpacity: 0.9
                            })
                        } else if (
                            feature.TsTime[feature.TsTime.length - 1] * 1000 >
                                first_date &&
                            feature.TsTime[0] < last_date
                        ) {
                            layer.setStyle({
                                color: "blue",
                                fillColor: "#ffffff",
                                radius: 2,
                                fillOpacity: 0.9
                            })
                        } else {
                            layer.setStyle({
                                color: "grey",
                                radius: 1
                            })
                        }
                    } else {
                        layer.setStyle({
                            color: "grey",
                            radius: 1
                        })
                    }
                } else {
                    layer.setStyle({
                        color: "red",
                        radius: 1
                    })
                }
            }

            function set_content() {
                //make a high charts
                if (feature.TsTime) {
                    layer.on({
                        click: function showResultsInDiv() {
                            var data = []
                            var elevation = []
                            var drawdown = []
                            var first_date = new Date(
                                testTimeLayer._timeDimension.getAvailableTimes()[0]
                            )

                            if (feature.TsTime) {
                                var tlocation = 0
                                var stop_location = 0
                                for (var i = 0; i < feature.TsTime.length; i++) {
                                    if (
                                        feature.TsTime[i] * 1000 >= first_date &&
                                        stop_location == 0
                                    ) {
                                        tlocation = i
                                        stop_location = 1
                                    }
                                }
                            }
                            // target time is larger than max date
                            if (tlocation == 0 && stop_location == 0) {
                                tlocation = -999
                            }

                            // target time is smaller than min date
                            if (tlocation == 0 && stop_location == 1) {
                                tlocation = -888
                            }

                            // for the case where the target time is in the middle
                            if (tlocation > 0) {
                                var timedelta =
                                    first_date - feature.TsTime[tlocation - 1] * 1000
                                var slope =
                                    (feature.TsValue[tlocation] -
                                        feature.TsValue[tlocation - 1]) /
                                    (feature.TsTime[tlocation] * 1000 -
                                        feature.TsTime[tlocation - 1] * 1000)
                                var timevalue =
                                    feature.TsValue[tlocation - 1] + slope * timedelta
                            }

                            if (feature.TsTime) {
                                for (var i = 0; i < feature.TsTime.length; i++) {
                                    data[i] = [
                                        feature.TsTime[i] * 1000,
                                        feature.TsValue[i]
                                    ]
                                    if (feature.properties.LandElev) {
                                        elevation[i] = [
                                            feature.TsTime[i] * 1000,
                                            feature.TsValue[i] +
                                                feature.properties.LandElev
                                        ]
                                    } else {
                                        elevation[i] = [
                                            feature.TsTime[i] * 1000,
                                            feature.TsValue[i]
                                        ]
                                    }
                                    if (tlocation > 0) {
                                        drawdown[i] = [
                                            feature.TsTime[i] * 1000,
                                            feature.TsValue[i] - timevalue
                                        ]
                                    } else {
                                        drawdown[i] = [
                                            feature.TsTime[i] * 1000,
                                            feature.TsValue[i] - feature.TsValue[0]
                                        ]
                                    }
                                }
                            }
                            count = 0
                            map.on("popupopen", function() {
                                $("." + feature.properties.HydroID).click(function() {
                                    if (count == 0) {
                                        if (
                                            !feature.properties.Outlier ||
                                            feature.properties.Outlier == false
                                        ) {
                                            feature.properties.Outlier = true
                                            popup_content = getpopup_content()
                                            var edit = "add"
                                            $.ajax({
                                                url: apiServer + "addoutlier/",
                                                type: "GET",
                                                data: {
                                                    region: region,
                                                    aquifer: aquifer,
                                                    hydroId: feature.properties.HydroID,
                                                    edit: edit
                                                },
                                                contentType: "application/json",
                                                error: function(status) {},
                                                success: function(response) {
                                                    layer._popup.setContent(popup_content)
                                                }
                                            })
                                        } else {
                                            feature.properties.Outlier = false
                                            popup_content = getpopup_content()
                                            var edit = "remove"
                                            $.ajax({
                                                url: apiServer + "addoutlier/",
                                                type: "GET",
                                                data: {
                                                    region: region,
                                                    aquifer: aquifer,
                                                    hydroId: feature.properties.HydroID,
                                                    edit: edit
                                                },
                                                contentType: "application/json",
                                                error: function(status) {},
                                                success: function(response) {
                                                    layer._popup.setContent(popup_content)
                                                }
                                            })
                                        }
                                        count += 1
                                        map.closePopup()
                                    }
                                })
                            })

                            mychart = Highcharts.chart("chart", {
                                chart: {
                                    type: "spline"
                                },
                                title: {
                                    text: (function() {
                                        //'Depth to Water Table (ft)'}
                                        var since = ""
                                        type = $("#select_view")
                                            .find("option:selected")
                                            .val()
                                        if (type == "elevation") {
                                            type = "Elevation of Water Table "
                                        } else if (type == "drawdown") {
                                            type = "Drawdown "
                                            var blank_raster = $("#available_dates")
                                                .find("option:selected")
                                                .val()
                                            var first_entry = data[0][0]
                                            if (blank_raster != "Blank.nc") {
                                                var first_time = new Date(
                                                    testTimeLayer._timeDimension.getAvailableTimes()[0]
                                                )
                                                var last_entry = data[data.length - 1][0]
                                                if (last_entry < first_time) {
                                                    var min = first_entry
                                                } else {
                                                    var min = Math.max(
                                                        first_time,
                                                        first_entry
                                                    )
                                                }
                                            } else {
                                                var min = first_entry
                                            }
                                            min = new Date(min)
                                            year = min.getFullYear()
                                            var months = [
                                                "January",
                                                "February",
                                                "March",
                                                "April",
                                                "May",
                                                "June",
                                                "July",
                                                "August",
                                                "September",
                                                "October",
                                                "November",
                                                "December"
                                            ]
                                            var month = months[min.getMonth()]
                                            since = "since " + month + ", " + year + " "
                                        } else {
                                            type = "Depth to Water Table "
                                        }
                                        type +=
                                            since +
                                            "at Well " +
                                            feature.properties.HydroID +
                                            ", located at " +
                                            feature.geometry.coordinates
                                        return type
                                    })()
                                },
                                tooltip: { valueDecimals: 2 },
                                xAxis: {
                                    type: "datetime",

                                    title: {
                                        text: "Date"
                                    },
                                    min: (function() {
                                        var blank_raster = $("#available_dates")
                                            .find("option:selected")
                                            .val()
                                        var first_entry = data[0][0]
                                        if (blank_raster != "Blank.nc") {
                                            var first_time = new Date(
                                                testTimeLayer._timeDimension.getAvailableTimes()[0]
                                            )
                                            var min = Math.min(first_time, first_entry)
                                        } else {
                                            var min = first_entry
                                        }
                                        return min
                                    })(),
                                    max: (function() {
                                        var blank_raster = $("#available_dates")
                                            .find("option:selected")
                                            .val()
                                        var last_entry = data[data.length - 1][0]
                                        if (blank_raster != "Blank.nc") {
                                            var last_time = new Date(
                                                testTimeLayer._timeDimension.getAvailableTimes()[
                                                    testTimeLayer._timeDimension.getAvailableTimes()
                                                        .length - 1
                                                ]
                                            )
                                            var max = Math.max(last_time, last_entry)
                                        } else {
                                            var max = last_entry
                                        }
                                        return max
                                    })(),
                                    plotBands: [
                                        {
                                            color: "rgba(0,0,0,0.05)",
                                            from: new Date(1850, 0, 1),
                                            to: new Date(
                                                testTimeLayer._timeDimension.getAvailableTimes()[0]
                                            ),
                                            id: "band1"
                                        },
                                        {
                                            color: "rgba(0,0,0,0.05)",
                                            from: new Date(
                                                testTimeLayer._timeDimension.getAvailableTimes()[
                                                    testTimeLayer._timeDimension.getAvailableTimes()
                                                        .length - 1
                                                ]
                                            ),
                                            to: new Date(2050, 0, 1),
                                            id: "band2"
                                        }
                                    ],
                                    plotLines: [
                                        {
                                            color: "red",
                                            dashStyle: "solid",
                                            value: new Date(
                                                testTimeLayer._timeDimension.getCurrentTime()
                                            ),
                                            width: 2,
                                            id: "pbCurrentTime"
                                        }
                                    ]
                                },
                                yAxis: {
                                    title: {
                                        text: (function() {
                                            //'Depth to Water Table (ft)'}
                                            type = $("#select_view")
                                                .find("option:selected")
                                                .val()
                                            if (type == "elevation") {
                                                type =
                                                    "Elevation of Water Table (" +
                                                    length_unit +
                                                    ")"
                                            } else if (type == "drawdown") {
                                                type = "Drawdown (" + length_unit + ")"
                                            } else {
                                                type =
                                                    "Depth to Water Table (" +
                                                    length_unit +
                                                    ")"
                                            }
                                            return type
                                        })()
                                    }
                                },
                                series: [{
                                    data: data,
                                    name: "Depth to Water Table ("+length_unit+")",
                                    marker:{enabled: true},
                                    visible:(function(){
                                            type=$("#select_view").find('option:selected').val();
                                            visible=false
                                            if (type=="depth"){
                                                visible=true;
                                            }
                                            return visible
                                        })()
                                    },
                                    {
                                    data:elevation,
                                    name: "Elevation of Water Table ("+length_unit+")",
                                    marker:{enabled: true},
                                    color:'blue',
                                    visible:(function(){
                                            type=$("#select_view").find('option:selected').val();
                                            visible=false
                                            if (type=="elevation"){
                                                visible=true;
                                            }
                                            return visible
                                        })()
                                    },
                                    {
                                    data:drawdown,
                                    name: "Drawdown ("+length_unit+")",
                                    marker:{enabled: true},
                                    color:'#1A429E',
                                    visible:(function(){
                                            type=$("#select_view").find('option:selected').val();
                                            visible=false
                                            if (type=="drawdown"){
                                                visible=true;
                                            }
                                            return visible
                                        })()
                                    }
                                ]
                            })
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
                                        var interpelev=[];
                                        var interpdrawdown=[];
                                        var j=0;
                                        for (var i=0;i<interp_times.length;i++){
                                            if (interp_depths[i]!=-9999){
                                                interpodata[j]=[new Date(interp_times[i]*24*3600*1000)-new Date('3939-1-2'),interp_depths[i]];
                                                interpelev[j]=[new Date(interp_times[i]*24*3600*1000)-new Date('3939-1-2'),interp_depths[i]+feature.properties.LandElev];
                                                interpdrawdown[j]=[new Date(interp_times[i]*24*3600*1000)-new Date('3939-1-2'),interp_depths[i]-interpodata[0][1]];
                                                j=j+1;
                                            }
                                        }
                                        mychart.addSeries({
                                            name: "Depth Used in Interpolation("+length_unit+")",
                                            marker:{enabled: true},
                                            data:interpodata,
                                            visible:(function(){
                                            type=$("#select_view").find('option:selected').val();
                                            visible=false
                                            if (type=="depth"){
                                                visible=true;
                                            }
                                            return visible;
                                        })()
                                        });
                                        mychart.addSeries({
                                            name: "Elevation Used in Interpolation("+length_unit+")",
                                            marker:{enabled: true},
                                            data:interpelev,
                                            visible:(function(){
                                            type=$("#select_view").find('option:selected').val();
                                            visible=false
                                            if (type=="elevation"){
                                                visible=true;
                                            }
                                            return visible;
                                        })()
                                        });
                                        mychart.addSeries({
                                            name: "Drawdown Used in Interpolation("+length_unit+")",
                                            marker:{enabled: true},
                                            data:interpdrawdown,
                                            visible:(function(){
                                            type=$("#select_view").find('option:selected').val();
                                            visible=false
                                            if (type=="drawdown"){
                                                visible=true;
                                            }
                                            return visible;
                                        })()
                                        });
                                    }
                                }
                            })
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
                                document.getElementById('chart').innerHTML='';
                                set_color();
                                map.closePopup();
                                return;
//                                THis code slows down the app and makes it freeze too much
//                                var since='';
//                                type=$("#select_view").find('option:selected').val();
//                                if (type=="elevation"){
//                                    type="Elevation of Water Table ("+length_unit+")";
//                                }
//                                else if(type=="drawdown"){
//                                    type="Drawdown ("+length_unit+")";
//                                    var blank_raster=$("#available_dates").find('option:selected').val();
//                                    var first_entry=data[0][0];
//                                    if (blank_raster!="Blank.nc"){
//                                        var first_time=new Date(testTimeLayer._timeDimension.getAvailableTimes()[0]);
//                                        var last_entry=data[data.length-1][0];
//                                        if (last_entry<first_time){
//                                            var min =first_entry;
//                                        }
//                                        else{
//                                            var min=Math.max(first_time,first_entry);
//                                        }
//                                    }
//                                    else{
//                                        var min=first_entry;
//                                    }
//                                    min=new Date(min)
//                                    year=min.getFullYear();
//                                    var months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
//                                    var month = months[min.getMonth()];
//                                    since="since "+month+", "+year+" ";
//                                }
//                                else{
//                                    type="Depth to Water Table ("+length_unit+")";
//                                }
//                                for (var i=0;i<mychart.series.length;i++){
//                                    if (mychart.series[i].name==type){
//                                        mychart.series[i].show();
//                                    }
//                                    else{
//                                        mychart.series[i].hide();
//                                    }
//                                }
//                                mychart.yAxis[0].setTitle({text: type});
//                                type=type.substring(0,type.length-4)
//                                mychart.setTitle({text:type +since+'at Well ' +feature.properties.HydroID+", located at "+feature.geometry.coordinates})

                            }).bind(this));
                            testTimeLayer._timeDimension.on('availabletimeschanged', (function updateTitle() {
                                if (!mychart){
                                    return;
                                }
                                document.getElementById('chart').innerHTML='';
                                set_color();
                                map.closePopup();
                                return;
//                                this code slows down the app and makes it freeze too much
//                                var since='';
//                                type=$("#select_view").find('option:selected').val();
//                                if (type=="elevation"){
//                                    type="Elevation of Water Table ("+length_unit+")";
//                                }
//                                else if(type=="drawdown"){
//                                    type="Drawdown ("+length_unit+")";
//                                    var blank_raster=$("#available_dates").find('option:selected').val();
//                                    var first_entry=data[0][0];
//                                    if (blank_raster!="Blank.nc"){
//                                        var first_time=new Date(testTimeLayer._timeDimension.getAvailableTimes()[0]);
//                                        var last_entry=data[data.length-1][0];
//                                        if (last_entry<first_time){
//                                            var min =first_entry;
//                                        }
//                                        else{
//                                            var min=Math.max(first_time,first_entry);
//                                        }
//                                    }
//                                    else{
//                                        var min=first_entry;
//                                    }
//                                    min=new Date(min)
//                                    year=min.getFullYear();
//                                    var months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
//                                    var month = months[min.getMonth()];
//                                    since="since "+month+", "+year+" ";
//                                }
//                                else{
//                                    type="Depth to Water Table ("+length_unit+")";
//                                }
//                                for (var i=0;i<mychart.series.length;i++){
//                                    if (mychart.series[i].name==type){
//                                        mychart.series[i].show();
//                                    }
//                                    else{
//                                        mychart.series[i].hide();
//                                    }
//                                }
//                                mychart.yAxis[0].setTitle({text: type});
//                                type=type.substring(0,type.length-4)
//                                mychart.setTitle({text:type +since+'at Well ' +feature.properties.HydroID+", located at "+feature.geometry.coordinates})
//
////                              code to update the shaded region of the chart
//                                var last_entry=data[data.length-1][0];
//                                var max=Math.max(last_time,last_entry);
//                                var first_entry=data[0][0];
//                                var blank_raster=$("#available_dates").find('option:selected').val();
//                                if (blank_raster!="Blank.nc"){
//                                    var last_time=new Date(testTimeLayer._timeDimension.getAvailableTimes()[testTimeLayer._timeDimension.getAvailableTimes().length-1]);
//                                    var first_time=new Date(testTimeLayer._timeDimension.getAvailableTimes()[0]);
//                                    var min=Math.min(first_time,first_entry);
//                                    var max=Math.max(last_time, last_entry);
//                                }
//                                else{
//                                    var min=first_entry;
//                                    var max=last_entry;
//                                }
//
//                                mychart.xAxis[0].removePlotBand('band1');
//                                mychart.xAxis[0].removePlotBand('band2');
//                                mychart.xAxis[0].addPlotBand({
//                                    color: 'rgba(0,0,0,0.05)',
//                                    from: new Date(1850,0,1),
//                                    to:new Date(testTimeLayer._timeDimension.getAvailableTimes()[0]),
//                                    id:'band1'
//                                })
//                                mychart.xAxis[0].addPlotBand({
//                                    color: 'rgba(0,0,0,0.05)',
//                                    from: new Date(testTimeLayer._timeDimension.getAvailableTimes()[testTimeLayer._timeDimension.getAvailableTimes().length-1]),
//                                    to:new Date(2050,0,1),
//                                    id:'band2'
//                                })
//                                mychart.xAxis[0].setExtremes(min,max);
                            }).bind(this));
                        }
                    })
                } else {
                    layer.on("click", function() {
                        document.getElementById("chart").innerHTML =
                            "<strong>No Time Series Data for Well " +
                            feature.properties.HydroID +
                            ", located at " +
                            feature.geometry.coordinates +
                            "</strong>"
                    })
                }
                layer.bindPopup(popup_content)
            }
            set_content()
            set_color()
            //option for highlighting selected point
            layer.on("popupopen", function(e) {
                e.target.setStyle({ color: "white", radius: 8, fillColor: "red" })
                map.on("popupopen", function() {
                    set_color()
                })
            })

            $("#available_dates").on("change", function() {
                set_color()
            })
        },
        pointToLayer: function(geoJsonPoint, latlng) {
            return L.circleMarker(latlng, { radius: 1, color: color })
        }
    })
    well_group.addLayer(well_layer)

    well_group.addTo(map)

    var url =
        thredds_url +
        region +
        "/" +
        name +
        "?service=WMS&version=1.3.0&request=GetCapabilities"
    if (name == "Blank.nc") {
        url =
            thredds_url +
            "/" +
            name +
            "?service=WMS&version=1.3.0&request=GetCapabilities"
    }

    var oReq = new XMLHttpRequest()
    oReq.addEventListener("load", function(xhr) {
        var response = xhr.currentTarget.response
        pos1 = response.indexOf("T00:00:00.000Z") + 1
        pos2 = response.indexOf("T00:00:00.000Z", pos1) - 10
        pos3 = response.indexOf(">", pos2)
        pos4 = response.indexOf("<", pos2)
        pos3 = Math.min(pos3, pos4)
        substring = response.substring(pos2, pos3)
        map.timeDimension.setAvailableTimes(substring, "replace")
        document.getElementById("waiting_output").innerHTML = ""
    })
    oReq.open("GET", url)
    oReq.send()

    //document.getElementById('waiting_output').innerHTML = '';
}

function list_aquifer() {
    document.getElementById("buttons").style.display = "none"
    document.getElementById("volbut").style.display = "none"
    region = $("#select_region")
        .find("option:selected")
        .val()
    region_group.clearLayers()
    clearwells()
    clearwaterlevels()
    toggle.remove()
    toggle = L.control.layers(null, null).addTo(map)
    minor_group.clearLayers()
    major_group.clearLayers()
    //This ajax controller loads the JSON file for the Texas State boundary and adds it to the map
    var geolayer = region + "_State_Boundary.json"
    var region = $("#select_region")
        .find("option:selected")
        .val()
    $.ajax({
        url: apiServer + "displaygeojson/",
        type: "GET",
        data: { geolayer: geolayer, region: region },
        contentType: "application/json",
        error: function(status) {},
        success: function(response) {
            texasboundary = response["state"].features
            var aquifer_center = regioncenter
            texasborder = L.geoJSON(texasboundary, {
                color: "red",
                weight: 1,
                fillOpacity: 0.0,
                onEachFeature: function(feature, layer) {
                    feature.properties.bounds_calculated = layer.getBounds()
                    var latcenter =
                        (feature.properties.bounds_calculated._northEast.lat +
                            feature.properties.bounds_calculated._southWest.lat) /
                        2
                    var loncenter =
                        (feature.properties.bounds_calculated._northEast.lng +
                            feature.properties.bounds_calculated._southWest.lng) /
                        2
                    aquifer_center = [latcenter, loncenter]
                }
            })
            region_group.addLayer(texasborder)
            region_group.addTo(map)
            regioncenter = aquifer_center
            if (response["major"]) {
                major = response["major"]
                majoraquifers = L.geoJSON(major, {
                    weight: 1,
                    fillOpacity: 0.2,
                    onEachFeature: function(feature, layer) {
                        tooltip_content = "Major Aquifer: " + feature.properties.Name
                        layer.bindTooltip(tooltip_content, { sticky: true })
                        layer.on({
                            click: function jumpaquifer() {
                                $("#select_aquifer").val(feature.properties.Id)
                                document.getElementById(
                                    "select2-select_aquifer-container"
                                ).innerHTML = $("#select_aquifer")
                                    .find("option:selected")
                                    .text()
                                list_dates(2) //,feature.properties.Name,feature.properties.Id)
                            }
                        })
                    }
                })
                majoraquifers.addTo(major_group)
                major_group.addTo(map)
                toggle.addOverlay(major_group, "Major Aquifers")
            }
            if (response["minor"]) {
                minor = response["minor"]
                minoraquifers = L.geoJSON(minor, {
                    color: "green",
                    weight: 1,
                    fillOpacity: 0.2,
                    onEachFeature: function(feature, layer) {
                        tooltip_content = "Minor Aquifer: " + feature.properties.Name
                        layer.bindTooltip(tooltip_content, { sticky: true })
                        layer.on({
                            click: function jumpaquifer() {
                                $("#select_aquifer").val(feature.properties.Id)
                                document.getElementById(
                                    "select2-select_aquifer-container"
                                ).innerHTML = $("#select_aquifer")
                                    .find("option:selected")
                                    .text()
                                list_dates(2) //,feature.properties.Name,feature.properties.Id)
                            }
                        })
                    }
                })
                minoraquifers.addTo(minor_group)
                minor_group.addTo(map)
                toggle.addOverlay(minor_group, "Minor Aquifers")
            }

            map.fitBounds(region_group.getBounds())
            size = map.getSize()
            bounds = map.getBounds().toBBoxString()

            $.ajax({
                url: apiServer + "loadaquiferlist/",
                type: "GET",
                data: { region: region },
                contentType: "application/json",
                error: function(status) {},
                success: function(response) {
                    aquiferlist = response.aquiferlist
                    $("#select_aquifer").empty()
                    $("#select_aquifer").append(
                        '<option value="' + 9999 + '">' + "" + "</option>"
                    )
                    for (i = 0; i < aquiferlist.length; i++) {
                        name = aquiferlist[i].Name
                        number = aquiferlist[i].Id
                        $("#select_aquifer").append(
                            '<option value="' + number + '">' + name + "</option>"
                        )
                    }
                    document.getElementById(
                        "select2-select_aquifer-container"
                    ).innerHTML = $("#select_aquifer")
                        .find("option:selected")
                        .text()
                    $("#available_dates").empty()
                    document.getElementById(
                        "select2-available_dates-container"
                    ).innerHTML = ""
                }
            })
        }
    })
}

function toggleButtons() {
    animation = $("#available_dates")
        .find("option:selected")
        .val()
    if (animation != "Blank.nc") {
        document.getElementById("buttons").style.display = "block"
    } else {
        document.getElementById("buttons").style.display = "none"
    }
    region = $("#select_region")
        .find("option:selected")
        .val()
    $.ajax({
        url: apiServer + "checktotalvolume/",
        type: "GET",
        data: { region: region, name: animation },
        contentType: "application/json",
        error: function(status) {},
        success: function(response) {
            var exists = response.exists
            if (exists == true) {
                document.getElementById("volbut").style.display = "block"
            } else {
                document.getElementById("volbut").style.display = "none"
                document.getElementById("volbut").style.display = "none"
            }
            $("#display-status").html("")
            $("#display-status")
                .html("")
                .removeClass("success")
            $("#resource-abstract").val(response.abstract)
            $("#resource-keywords").val(response.keywords)
            $("#resource-title").val(response.title)
            $("#resource-type").val(response.type)
            var filepath = response.filepath
            var metadata = response.metadata
        }
    })
}

function list_dates(call_function) {
    var region = $("#select_region")
        .find("option:selected")
        .val()
    //This ajax controller

    aquifer = $("#select_aquifer")
        .find("option:selected")
        .text()

    $.ajax({
        url: apiServer + "loadtimelist/",
        type: "GET",
        data: { region: region, aquifer: aquifer },
        contentType: "application/json",
        error: function(status) {},
        success: function(response) {
            var timelist = response.timelist
            $("#available_dates").empty()
            $("#available_dates").append(
                '<option value="' + "Blank.nc" + '">' + "No Raster" + "</option>"
            )
            $("#available_dates").val("Blank.nc")
            for (i = 0; i < timelist.length; i++) {
                number = timelist[i].Full_Name
                if (timelist[i].Interp_Options) {
                    var myoptions = "elevation"
                    if (timelist[i].Interp_Options == "both") {
                        myoptions = "elevation and depth"
                    } else if (timelist[i].Interp_Options == "depth") {
                        myoptions = "depth"
                    }
                    name =
                        timelist[i].Aquifer +
                        " " +
                        timelist[i].Interpolation +
                        " using " +
                        myoptions +
                        ": " +
                        timelist[i].Start_Date +
                        "-" +
                        timelist[i].End_Date +
                        " (" +
                        timelist[i].Interval +
                        " Year Increments, " +
                        timelist[i].Resolution +
                        " Degree Resolution, " +
                        timelist[i].Min_Samples +
                        " Min Samples, " +
                        timelist[i].Min_Ratio +
                        " Min Ratio, " +
                        timelist[i].Time_Tolerance +
                        " Year Time Tolerance)"
                } else {
                    name =
                        timelist[i].Aquifer +
                        " " +
                        timelist[i].Interpolation +
                        ": " +
                        timelist[i].Start_Date +
                        "-" +
                        timelist[i].End_Date +
                        " (" +
                        timelist[i].Interval +
                        " Year Increments, " +
                        timelist[i].Resolution +
                        " Degree Resolution, " +
                        timelist[i].Min_Samples +
                        " Min Samples, " +
                        timelist[i].Min_Ratio +
                        " Min Ratio, " +
                        timelist[i].Time_Tolerance +
                        " Year Time Tolerance)"
                }
                $("#available_dates").append(
                    '<option value="' + number + '">' + name + "</option>"
                )
                if (timelist.length == 1) {
                    $("#available_dates").val(number)
                }

                if (timelist[i].Default == 1) {
                    $("#available_dates").val(number)
                }
                units = timelist[i].Units
            }
            document.getElementById("select2-available_dates-container").innerHTML = $(
                "#available_dates"
            )
                .find("option:selected")
                .text()
            toggleButtons()
            if (call_function == 1) {
                changeWMS() //clears only raster layers and updates them
            }
            if (call_function == 2) {
                change_aquifer() //clears all layers and updates them
            }
        }
    })
}

function confirm_delete(){
    var region=$("#select_region").find('option:selected').val()
    var name=$("#available_dates").find('option:selected').val();
    var x =confirm("Are you sure you want to delete the current NetCDF Raster? ("+name+")");
    if (x){
        clearwaterlevels();
        $.ajax({
            url: apiServer + "deletenetcdf/",
            type: "GET",
            data: { region: region, name: name },
            contentType: "application/json",
            error: function(status) {},
            success: function(response) {
                list_dates(1)
                document.getElementById("chart").innerHTML = ""
            }
        })
    }
}

function confirm_default() {
    var region = $("#select_region")
        .find("option:selected")
        .val()
    var aquifer = $("#select_aquifer")
        .find("option:selected")
        .text()
    var name = $("#available_dates")
        .find("option:selected")
        .val()
    var x = confirm(
        "Are you sure you want to make the current NetCDF raster the default? (" +
            name +
            ")"
    )
    if (x) {
        $.ajax({
            url: apiServer + "defaultnetcdf/",
            type: "GET",
            data: { region: region, aquifer: aquifer, name: name },
            contentType: "application/json",
            error: function(status) {},
            success: function(response) {
                list_dates(1)
            }
        })
    }
}

function totalvolume() {
    region = $("#select_region")
        .find("option:selected")
        .val()
    name = $("#available_dates")
        .find("option:selected")
        .val()
    var length_unit = "m"
    var vol_unit = "Cubic Meters"
    if (units == "English") {
        length_unit = "ft"
        vol_unit = "Acre-ft"
    }
    $.ajax({
        url: apiServer + "gettotalvolume/",
        type: "GET",
        data: { region: region, name: name },
        contentType: "application/json",
        error: function(status) {},
        success: function(response) {
            //add data to highchart
            volumelist = response["volumelist"]
            timelist = response["timelist"]
            var length = timelist.length
            var data = []
            var oneday = 24 * 60 * 60 * 1000
            var UTCconversion = 280 * 24 * 60 * 60 * 1000
            var oneyear = 24 * 60 * 60 * 1000 * 365.2
            for (var i = 0; i < length; i++) {
                timelist[i] = timelist[i] * oneday - oneyear * 1970 + UTCconversion
                timelist[i] = new Date(timelist[i]).getTime()
                data[i] = [timelist[i], volumelist[i]]
            }
            document.getElementById("chart").innerHTML = ""
            var TimeLayer = interpolation_group.customGetLayer("timelayer")
            mychart = Highcharts.chart("chart", {
                chart: {
                    type: "area"
                },
                title: {
                    text: (function() {
                        var type = "Change in Aquifer Storage Volume "
                        var since = ""
                        var blank_raster = $("#available_dates")
                            .find("option:selected")
                            .val()
                        var min = data[0][0]
                        min = new Date(min)
                        year = min.getFullYear()
                        var months = [
                            "January",
                            "February",
                            "March",
                            "April",
                            "May",
                            "June",
                            "July",
                            "August",
                            "September",
                            "October",
                            "November",
                            "December"
                        ]
                        var month = months[min.getMonth()]
                        since = "since " + month + ", " + year + " "
                        type += since + "(Acre-ft)"
                        return type
                    })()
                },
                tooltip: { valueDecimals: 0 },
                xAxis: {
                    type: "datetime",

                    title: {
                        text: "Date"
                    },
                    plotLines: [
                        {
                            color: "red",
                            dashStyle: "solid",
                            value: new Date(TimeLayer._timeDimension.getCurrentTime()),
                            width: 2,
                            id: "pbCurrentTime"
                        }
                    ]
                },
                yAxis: {
                    title: {
                        text: (function() {
                            //'Depth to Water Table (ft)'}
                            type = "Change in aquifer storage volume (" + vol_unit + ")"
                            return type
                        })()
                    }
                },
                series: [
                    {
                        data: data,
                        name: "Change in aquifer storage volume (" + vol_unit + ")"
                    }
                ]
            })
            TimeLayer._timeDimension.on(
                "timeload",
                function() {
                    if (!mychart) {
                        return
                    }
                    mychart.xAxis[0].removePlotBand("pbCurrentTime")
                    mychart.xAxis[0].addPlotLine({
                        color: "red",
                        dashStyle: "solid",
                        value: new Date(TimeLayer._timeDimension.getCurrentTime()),
                        width: 2,
                        id: "pbCurrentTime"
                    })
                }.bind(this)
            )
        }
    })
}

//This is a function for uploading the NetCDF file to HydroShare

$("#hydroshare-proceed").on("click", function() {
    //This function only works on HTML5 browsers.
    var displayStatus = $("#display-status")
    displayStatus.removeClass("error")
    displayStatus.addClass("uploading")
    displayStatus.html("<em>Uploading...</em>")
    var resourceTypeSwitch = function(typeSelection) {
        var options = {
            GenericResource: "GenericResource",
            "Geographic Raster": "RasterResource",
            "HIS Referenced Time Series": "RefTimeSeries",
            "Model Instance": "ModelInstanceResource",
            "Model Program": "ModelProgramResource",
            "Multidimensional (NetCDF)": "NetcdfResource",
            "Time Series": "TimeSeriesResource",
            Application: "ToolResource"
        }
        return options[typeSelection]
    }

    var name = $("#available_dates")
        .find("option:selected")
        .val()
    name = name.replace(/ /g, "_")
    var region = $("#select_region")
        .find("option:selected")
        .val()
    region = region.replace(/ /g, "_")
    var resourceAbstract = $("#resource-abstract").val()
    var resourceTitle = $("#resource-title").val()
    var resourceKeywords = $("#resource-keywords").val()
    var resourceType = $("#resource-type").val()

    if (!resourceTitle || !resourceKeywords || !resourceAbstract) {
        displayStatus.removeClass("uploading")
        displayStatus.addClass("error")
        displayStatus.html("<em>You must provide all metadata information.</em>")
        return
    }

    $(this).prop("disabled", true)
    $.ajax({
        type: "POST",
        url: apiServer + "upload-to-hydroshare/",
        dataType: "json",
        data: {
            name: name,
            region: region,
            r_title: resourceTitle,
            r_type: resourceType,
            r_abstract: resourceAbstract,
            r_keywords: resourceKeywords
        },
        success: function(data) {
            $("#hydroshare-proceed").prop("disabled", false)
            if ("error" in data) {
                displayStatus.removeClass("uploading")
                displayStatus.addClass("error")
                displayStatus.html("<em>" + data.error + "</em>")
            } else {
                displayStatus.removeClass("uploading")
                displayStatus.addClass("success")
                displayStatus.html(
                    "<em>" +
                        data.success +
                        ' View in HydroShare <a href="https://' +
                        data.hs_domain +
                        "/resource/" +
                        data.newResource +
                        '" target="_blank">HERE</a></em>'
                )
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            alert("Error")
            debugger
            $("#hydroshare-proceed").prop("disabled", false)
            console.log(jqXHR + "\n" + textStatus + "\n" + errorThrown)
            displayStatus.removeClass("uploading")
            displayStatus.addClass("error")
            displayStatus.html("<em>" + errorThrown + "</em>")
        }
    })
})
