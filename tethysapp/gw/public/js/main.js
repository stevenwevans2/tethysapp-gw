function add_aquifer_settings() {
    var region = $("#select_region")
        .find("option:selected")
        .val()
    var AquiferID = $("#select_AquiferID")
        .find("option:selected")
        .val()
    var DisplayName = $("#select_DisplayName")
        .find("option:selected")
        .val()
    var Aquifer_Name = $("#select_Aquifer_Name")
        .find("option:selected")
        .val()
    var porosity = $("#select_porosity")
        .find("option:selected")
        .val()
    var toggle_region = $("#toggle_region")
        .find("option:selected")
        .val()
    var minor_AquiferID = ""
    var minor_DisplayName = ""
    var minor_Aquifer_Name = ""
    var minor_porosity = ""
    var showminor = document.getElementById("showminor").value
    if (showminor == true || showminor == "True") {
        minor_AquiferID = $("#select_minor_AquiferID")
            .find("option:selected")
            .val()
        minor_DisplayName = $("#select_minor_DisplayName")
            .find("option:selected")
            .val()
        minor_Aquifer_Name = $("#select_minor_Aquifer_Name")
            .find("option:selected")
            .val()
        minor_porosity = $("#select_minor_porosity")
            .find("option:selected")
            .val()
    }
    var latlon=document.getElementById("latlon").value
    var wlat=""
    var wlon=""
    if (latlon==true || latlon=="True"){
        wlat=$("#select_lat")
            .find("option:selected")
            .val()
        wlon=$("#select_lon")
            .find("option:selected")
            .val()
    }
    var HydroID = $("#select_hydroid")
        .find("option:selected")
        .val()
    var AqID = $("#select_aqid")
        .find("option:selected")
        .val()
    var Elev = $("#select_elev")
        .find("option:selected")
        .val()
    var Type = $("#select_type")
        .find("option:selected")
        .val()
    var Depth = $("#select_depth")
        .find("option:selected")
        .val()
    var come_from = "upload"
    var units = $("#select_units")
        .find("option:selected")
        .val()
    $.ajax({
        url: apiServer + "finish_addregion/",
        type: "GET",
        data: {
            region: region,
            AquiferID: AquiferID,
            DisplayName: DisplayName,
            Aquifer_Name: Aquifer_Name,
            HydroID: HydroID,
            AqID: AqID,
            Elev: Elev,
            Type: Type,
            Depth: Depth,
            porosity: porosity,
            come_from: come_from,
            units: units,
            minor_AquiferID: minor_AquiferID,
            minor_DisplayName: minor_DisplayName,
            minor_Aquifer_Name: minor_Aquifer_Name,
            minor_porosity: minor_porosity,
            toggle_region: toggle_region,
            wlat: wlat,
            wlon: wlon
        },
        contentType: "application/json",
        error: function(status) {},
        success: function(response) {
            url = response["url"]
            window.location.href = url
        }
    })
}

function enlarge_map() {
    var height = $("#map_height")
        .find("option:selected")
        .val()
    document.getElementById("map").style.height = height
}

function add_aquifer_nwis_settings() {
    var region = $("#select_region")
        .find("option:selected")
        .val()
    var AquiferID = $("#select_AquiferID")
        .find("option:selected")
        .val()
    var DisplayName = $("#select_DisplayName")
        .find("option:selected")
        .val()
    var Aquifer_Name = $("#select_Aquifer_Name")
        .find("option:selected")
        .val()
    var porosity = $("#select_porosity")
        .find("option:selected")
        .val()
    var toggle_region = $("#toggle_region")
        .find("option:selected")
        .val()
    var minor_AquiferID = ""
    var minor_DisplayName = ""
    var minor_Aquifer_Name = ""
    var minor_porosity = ""
    var showminor = document.getElementById("showminor").value
    if (showminor == true || showminor == "True") {
        minor_AquiferID = $("#select_minor_AquiferID")
            .find("option:selected")
            .val()
        minor_DisplayName = $("#select_minor_DisplayName")
            .find("option:selected")
            .val()
        minor_Aquifer_Name = $("#select_minor_Aquifer_Name")
            .find("option:selected")
            .val()
        minor_porosity = $("#select_minor_porosity")
            .find("option:selected")
            .val()
    }

    var come_from = "nwis"
    var units = "English"
    $.ajax({
        url: apiServer + "finish_addregion/",
        type: "GET",
        data: {
            region: region,
            AquiferID: AquiferID,
            DisplayName: DisplayName,
            Aquifer_Name: Aquifer_Name,
            porosity: porosity,
            come_from: come_from,
            units: units,
            minor_AquiferID: minor_AquiferID,
            minor_DisplayName: minor_DisplayName,
            minor_Aquifer_Name: minor_Aquifer_Name,
            minor_porosity: minor_porosity,
            toggle_region: toggle_region
        },
        contentType: "application/json",
        error: function(status) {},
        success: function(response) {
            url = response["url"]
            window.location.href = url
        }
    })
}

function enlarge_map() {
    var height = $("#map_height")
        .find("option:selected")
        .val()
    document.getElementById("map").style.height = height
}

function delete_region() {
    var region = $("#select_region")
        .find("option:selected")
        .val()
    var x = confirm(
        "Are you sure you want to delete the selected region? (" + region + ")"
    )
    if (x) {
        $.ajax({
            url: apiServer + "deleteregion/",
            type: "GET",
            data: { region: region },
            contentType: "application/json",
            error: function(status) {},
            success: function(response) {
                url = response["url"]
                window.location.href = url
            }
        })
    }
}
