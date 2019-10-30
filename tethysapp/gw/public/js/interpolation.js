function update_aquifers() {
    var region = $("#select_region")
        .find("option:selected")
        .val()
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
                '<option value="' + 9999 + '">' + "Interpolate All Aquifers" + "</option>"
            )
            for (i = 0; i < aquiferlist.length; i++) {
                name = aquiferlist[i].Name
                number = aquiferlist[i].Id
                $("#select_aquifer").append(
                    '<option value="' + number + '">' + name + "</option>"
                )
            }
            document.getElementById("select2-select_aquifer-container").innerHTML = $(
                "#select_aquifer"
            )
                .find("option:selected")
                .text()
        }
    })
}

function get_porosity() {
    var region = $("#select_region")
        .find("option:selected")
        .val()
    var aquifer = $("#select_aquifer")
        .find("option:selected")
        .text()
    console.log(aquifer)
    $.ajax({
        url: apiServer + "loadaquiferlist/",
        type: "GET",
        data: { region: region },
        contentType: "application/json",
        error: function(status) {},
        success: function(response) {
            aquiferlist = response.aquiferlist
            for (i = 0; i < aquiferlist.length; i++) {
                if (aquiferlist[i].Name == aquifer) {
                    if ("Storage_Coefficient" in aquiferlist[i]) {
                        var porosity = aquiferlist[i].Storage_Coefficient
                        document.getElementById("select_porosity").value = porosity
                    }
                }
            }
        }
    })
}

function submit_form() {
    document.getElementById("chart").innerHTML = ""
    var wait_text =
        "<strong>Loading Data...</strong><br>" +
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src='/static/gw/images/loading.gif'>"
    document.getElementById("waiting_output").innerHTML = wait_text

    var interpolation_type = $("#select_interpolation")
        .find("option:selected")
        .val()
    var region = $("#select_region")
        .find("option:selected")
        .val()
    var start_date = $("#start_date")
        .find("option:selected")
        .val()
    var end_date = $("#end_date")
        .find("option:selected")
        .val()
    var interval = $("#frequency")
        .find("option:selected")
        .val()
    var resolution = $("#resolution")
        .find("option:selected")
        .val()
    var id = $("#select_aquifer option:selected").val()
    var length = $("#select_aquifer option").length - 1
    var time_tolerance = $("#time_tolerance")
        .find("option:selected")
        .val()
    var make_default = $("#default")
        .find("option:selected")
        .val()
    var min_samples = $("#min_samples")
        .find("option:selected")
        .val()
    var min_ratio = $("#min_ratio")
        .find("option:selected")
        .val()
    var units = $("#select_units")
        .find("option:selected")
        .val()
    var interpolation_options = $("#interpolation_options")
        .find("option:selected")
        .val()
    var temporal_interpolation = $("#temporal_interpolation")
        .find("option:selected")
        .val()
    var porosity = $("#select_porosity").val()
    var ndmin = $("#select_ndmin")
        .find("option:selected")
        .val()
    var ndmax = $("#select_ndmax")
        .find("option:selected")
        .val()
    var searchradius = $("#select_searchradius")
        .find("option:selected")
        .val()
    console.log(porosity)
    if (start_date >= end_date) {
        alert("Error, Start Date must be before End Date")
        document.getElementById("waiting_output").innerHTML = ""
    } else {
        $.ajax({
            url: apiServer + "loaddata/",
            type: "GET",
            data: {
                id: id,
                temporal_interpolation: temporal_interpolation,
                interpolation_options: interpolation_options,
                interpolation_type: interpolation_type,
                region: region,
                start_date: start_date,
                end_date: end_date,
                interval: interval,
                resolution: resolution,
                length: length,
                make_default: make_default,
                min_samples: min_samples,
                min_ratio: min_ratio,
                time_tolerance: time_tolerance,
                from_wizard: 1,
                units: units,
                porosity: porosity,
                ndmin: ndmin,
                ndmax: ndmax,
                searchradius: searchradius
            },
            contentType: "application/json",
            error: function(status) {},
            success: function(response) {
                document.getElementById("waiting_output").innerHTML = ""
                document.getElementById("chart").innerHTML = response["message"]
            }
        })
    }
}
