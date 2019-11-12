from __future__ import division
from __future__ import unicode_literals
import os
import json
import netCDF4
import datetime
import numpy as np
import calendar
import subprocess
import tempfile
import shutil
import scipy
from rasterio.transform import from_bounds, from_origin
from rasterio.warp import reproject, Resampling
import rasterio
import math
import pygslib
from scipy.optimize import least_squares
from scipy.optimize import curve_fit
from scipy.interpolate import UnivariateSpline
import elevation
import csv
from .app import Gw as app
import statsmodels.api as sm
import pandas as pd
from .model import *
# from ajax_controllers import *


#global variables
# thredds_serverpath='/opt/tomcat/content/thredds/public/testdata/groundwater/'
thredds_serverpath = app.get_custom_setting("thredds_path")
# thredds_serverpath="/home/student/tds/apache-tomcat-8.5.30/content/thredds/public/testdata/groundwater/"

# This function opens the Aquifers.csv file for the specified region and returns a JSON object listing the aquifers


def getaquiferlist(app_workspace, region):
    aquiferlist = []
    aquifercsv = os.path.join(app_workspace.path, region + '/' + region + '_Aquifers.csv')
    with open(aquifercsv) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            myaquifer = {
                'Id': int(row['ID']),
                'Name': row['Name'],
                # 'Type': row['Type'],
                'CapsName': row['CapsName'],
                # 'FieldName':row['NameField']
            }
            if 'Storage_Coefficient' in row:
                if row['Storage_Coefficient'] != '':
                    myaquifer['Storage_Coefficient'] = row['Storage_Coefficient']
            if 'Contains' in row:
                if row['Contains'] != "":
                    myaquifer['Contains'] = row['Contains'].split('.')
                    myaquifer['Contains'] = [int(i) for i in myaquifer['Contains']]
            aquiferlist.append(myaquifer)
    return aquiferlist


# The following functions are used to automatically fit a variogram to the input data
def great_circle_distance(lon1, lat1, lon2, lat2):
    """Calculate the great circle distance between one or multiple pairs of
    points given in spherical coordinates. Spherical coordinates are expected
    in degrees. Angle definition follows standard longitude/latitude definition.
    This uses the arctan version of the great-circle distance function
    (en.wikipedia.org/wiki/Great-circle_distance) for increased
    numerical stability.
    Parameters
    ----------
    lon1: float scalar or numpy array
        Longitude coordinate(s) of the first element(s) of the point
        pair(s), given in degrees.
    lat1: float scalar or numpy array
        Latitude coordinate(s) of the first element(s) of the point
        pair(s), given in degrees.
    lon2: float scalar or numpy array
        Longitude coordinate(s) of the second element(s) of the point
        pair(s), given in degrees.
    lat2: float scalar or numpy array
        Latitude coordinate(s) of the second element(s) of the point
        pair(s), given in degrees.
    Calculation of distances follows numpy elementwise semantics, so if
    an array of length N is passed, all input parameters need to be
    arrays of length N or scalars.
    Returns
    -------
    distance: float scalar or numpy array
        The great circle distance(s) (in degrees) between the
        given pair(s) of points.
    """
    # Convert to radians:
    lat1 = np.array(lat1)*np.pi/180.0
    lat2 = np.array(lat2)*np.pi/180.0
    dlon = (lon1-lon2)*np.pi/180.0

    # Evaluate trigonometric functions that need to be evaluated more
    # than once:
    c1 = np.cos(lat1)
    s1 = np.sin(lat1)
    c2 = np.cos(lat2)
    s2 = np.sin(lat2)
    cd = np.cos(dlon)

    # This uses the arctan version of the great-circle distance function
    # from en.wikipedia.org/wiki/Great-circle_distance for increased
    # numerical stability.
    # Formula can be obtained from [2] combining eqns. (14)-(16)
    # for spherical geometry (f=0).

    return 180.0 / np.pi * np.arctan2(np.sqrt((c2*np.sin(dlon))**2 + (c1*s2-s1*c2*cd)**2), s1*s2+c1*c2*cd)


def _variogram_residuals(params, x, y, variogram_function, weight):
    """Function used in variogram model estimation. Returns residuals between
    calculated variogram and actual data (lags/semivariance).
    Called by _calculate_variogram_model.
    Parameters
    ----------
    params: list or 1D array
        parameters for calculating the model variogram
    x: ndarray
        lags (distances) at which to evaluate the model variogram
    y: ndarray
        experimental semivariances at the specified lags
    variogram_function: callable
        the actual funtion that evaluates the model variogram
    weight: bool
        flag for implementing the crude weighting routine, used in order to
        fit smaller lags better
    Returns
    -------
    resid: 1d array
        residuals, dimension same as y
    """

    # this crude weighting routine can be used to better fit the model
    # variogram to the experimental variogram at smaller lags...
    # the weights are calculated from a logistic function, so weights at small
    # lags are ~1 and weights at the longest lags are ~0;
    # the center of the logistic weighting is hard-coded to be at 70% of the
    # distance from the shortest lag to the largest lag
    if weight:
        drange = np.amax(x) - np.amin(x)
        k = 2.1972 / (0.1 * drange)
        x0 = 0.7 * drange + np.amin(x)
        weights = 1. / (1. + np.exp(-k * (x0 - x)))
        weights /= np.sum(weights)
        resid = (variogram_function(params, x) - y) * weights
    else:
        resid = variogram_function(params, x) - y

    return resid


def spherical_variogram_model(m, d):
    """Spherical model, m is [psill, range, nugget]"""
    psill = float(m[0])
    range_ = float(m[1])
    nugget = float(m[2])
    return np.piecewise(d, [d <= range_, d > range_],
                        [lambda x: psill * ((3.*x)/(2.*range_) - (x**3.)/(2.*range_**3.)) + nugget, psill + nugget])


'''The generate_variogram function automatically fits a variogram to the data
    Inputs:
        X: a 2d array of geographical coordinates of sample points (longitude, latitude) of length n
        y: an array of length n containing the values at sample points, ordered the same as X
        variogram_function: a function for the variogram model (Spherical, Gaussian)
    Returns:
        variogram_model_parameters: a list of 1. the sill, 2. the range, 3. the nugget'''


def generate_variogram(X, y, variogram_function):
    # This calculates the pairwise geographic distance and variance between pairs of points
    x1, x2 = np.meshgrid(X[:, 0], X[:, 0], sparse=True)
    y1, y2 = np.meshgrid(X[:, 1], X[:, 1], sparse=True)
    z1, z2 = np.meshgrid(y, y, sparse=True)
    d = great_circle_distance(x1, y1, x2, y2)
    g = 0.5 * (z1 - z2) ** 2.
    indices = np.indices(d.shape)
    d = d[(indices[0, :, :] > indices[1, :, :])]
    g = g[(indices[0, :, :] > indices[1, :, :])]
    # d=squareform(pdist(X,metric='euclidean'))
    # g = 0.5 * pdist(y[:, None], metric='sqeuclidean')
    # print(d)

    # Now we will sort the d and g into bins
    nlags = 10
    weight = False
    dmax = np.amin(d) + (np.amax(d) - np.amin(d)) / 2.0
    # dmax = np.amax(d)

    dmin = np.amin(d)
    dd = (dmax - dmin) / nlags
    bins = [dmin + n * dd for n in range(nlags)]
    dmax += 0.001
    bins.append(dmax)

    lags = np.zeros(nlags)
    semivariance = np.zeros(nlags)

    for n in range(nlags):
        # This 'if... else...' statement ensures that there are data
        # in the bin so that numpy can actually find the mean. If we
        # don't test this first, then Python kicks out an annoying warning
        # message when there is an empty bin and we try to calculate the mean.
        if d[(d >= bins[n]) & (d < bins[n + 1])].size > 0:
            lags[n] = np.mean(d[(d >= bins[n]) & (d < bins[n + 1])])
            semivariance[n] = np.mean(g[(d >= bins[n]) & (d < bins[n + 1])])
        else:
            lags[n] = np.nan
            semivariance[n] = np.nan
    lags = lags[~np.isnan(semivariance)]
    semivariance = semivariance[~np.isnan(semivariance)]

    # First entry is the sill, then the range, then the nugget
    if len(lags) > 3:
        x0 = [np.amax(semivariance) - np.amin(semivariance), lags[2], 0]
        bnds = ([0., lags[2], 0.], [10. * np.amax(semivariance), np.amax(lags), 1])
    elif len(lags) > 1:
        x0 = [np.amax(semivariance) - np.amin(semivariance), lags[0], 0]
        bnds = ([0., lags[0], 0.], [10. * np.amax(semivariance), np.amax(lags), 1])
    else:
        x0 = [0, 0, 0]
        bnds = ([0., 0, 0.], [1000, 10, 1])

    # use 'soft' L1-norm minimization in order to buffer against
    # potential outliers (weird/skewed points)
    res = least_squares(_variogram_residuals, x0, bounds=bnds, loss='soft_l1',
                        args=(lags, semivariance, variogram_function, weight))
    variogram_model_parameters = res.x
    print("sill, range, nugget")
    print(variogram_model_parameters)
    return variogram_model_parameters


def upload_netcdf(points,aq_name,app_workspace,aquifer_number,region,interpolation_type,interpolation_options,temporal_interpolation,start_date,end_date,interval,resolution, min_samples, min_ratio, time_tolerance, date_name, make_default, units,porosity,ndmin,ndmax,searchradius,seasonal):

    # Execute the following code to interpolate groundwater levels and create a netCDF File and upload it to the server
    # Download and Set up the DEM for the aquifer
    iterations = int((end_date - start_date) / interval + 1)
    start_time = calendar.timegm(datetime.datetime(start_date, 1, 1).timetuple())
    end_time = calendar.timegm(datetime.datetime(end_date, 1, 1).timetuple())
    sixmonths = False
    threemonths = False
    time_u = "Y"
    time_v = 0
    date_shift = 2
    if interval <= .5:
        sixmonths = True
        time_u = "M"
        time_v = 6
        iterations += 1
        date_shift = 1
        if interval == .25:
            threemonths = True
            iterations += 2
            time_v = 3
    else:
        time_v = int(interval)
    resample_rate = str(time_v) + time_u
    existing_interp = False
    directory = os.path.join(thredds_serverpath, region)
    aquifer = aq_name.replace(" ", "_")
    list = []
    for filename in os.listdir(directory):
        if filename.startswith(aquifer + "."):
            list.append(filename)
    # for item in list:
    #     nc_file = os.path.join(directory, item)
    #     h = netCDF4.Dataset(nc_file, 'r+', format="NETCDF4")
    #     if h.start_date==start_date and h.end_date==end_date and h.interval==interval:
    #         if 'tsvalue' in h.variables and h.temporal_interpolation in h.ncattrs():
    #             if h.temporal_interpolation==temporal_interpolation:
    #                 times = h.variables['time'][:]
    #                 depths=h.variables['tsvalue'][:, :]
    #                 hydroids=h.variables['hydroid'][:]
    #                 h.close()
    #                 newinterpolation_df=pd.DataFrame(columns=hydroids,data=depths)
    #                 existing_interp=True
    #                 print("Used existing temporal interpolation")
    #                 break
    #     h.close()
    if existing_interp==False:
        if temporal_interpolation=="MLR":
            #THe following code predicts the timeseries values for each well at specified time intervals using multi-linear regression with
            #nearby wells as the regressors.
            combined_df = pd.DataFrame()
            for well in points['features']:
                if 'TsTime' in well:
                    # If statement to check whether the timeseries has the minimum samples required
                    if len(well['TsTime']) >= min_samples:
                        listlength = len(well['TsTime'])
                        length_time = end_time - start_time
                        mylength_time = min(well['TsTime'][listlength - 1] - well['TsTime'][0],
                                            max(well['TsTime'][listlength - 1] - start_time, 0), max(end_time - well['TsTime'][0], 0))
                        ratio = abs((float(mylength_time) / length_time))
                        # If Statement checks whether the timeseries spans enough of the dataset
                        if ratio > min_ratio:
                            # If statement checks whether the timeseries spans the user specified time interval from start_date to end_date
                            if np.array(well['TsTime']).max() > calendar.timegm(
                                    datetime.datetime(end_date-time_tolerance, 1, 1).timetuple()) and np.array(
                                    well['TsTime']).min() < calendar.timegm(datetime.datetime(start_date+time_tolerance, 1, 1).timetuple()):
                                # If the timeseries spans the time interval, then name is just HydroID, otherwise add 'Short' to the end of the name
                                name = str(well['properties']['HydroID'])
                            else:
                                name = str(well['properties']['HydroID']) + 'Short'
                            # add the data from the well to the combined_df pd dataframe after resampling it to 3 month intervals
                            wells_df = pd.DataFrame(index=pd.to_datetime(well['TsTime'], unit='s', origin='unix'),
                                                    data=well['TsValue'], columns=[name])
                            wells_df.index.drop_duplicates(keep="first")
                            if seasonal!=999 and interval>=1:
                                wells_df = wells_df.resample('Q-APR').mean()
                            else:
                                wells_df = wells_df.resample('Q').mean()
                            if 'Short' not in name:
                                first_date = wells_df.first_valid_index() - pd.DateOffset(years=time_tolerance)
                                last_date = wells_df.last_valid_index() + pd.DateOffset(years=time_tolerance)
                                wells_df = pd.concat([wells_df, pd.DataFrame(index=[first_date, last_date])],
                                                     join="outer", axis=1)
                                if seasonal!=999 and interval>=1:
                                    wells_df = wells_df.interpolate('nearest', limit=time_tolerance*2, limit_area='outside',
                                                                    limit_direction='both',
                                                                    fill_value="extrapolate").resample('Q-APR').mean()
                                else:
                                    wells_df = wells_df.interpolate('nearest', limit=time_tolerance * 2,
                                                                    limit_area='outside',
                                                                    limit_direction='both',
                                                                    fill_value="extrapolate").resample('Q').nearest()
                            combined_df = pd.concat([combined_df, wells_df], join="outer", axis=1)
                            combined_df.drop_duplicates(inplace=True)
            # combined_df is a pandas dataframe containing the ts depth to water table values for each well in the aquifer with the min number of points
            # The columns of combined_df are the HydroIDs of the wells. If the well timeseries data spans the period of interpolation, the column title
            # is the HydroID. If the timeseries does not span the time period, then the column title is the HydroID + "Short"
            # The rows of the database are the timeseries values for 3 month intervals from start_date to end_date
            if seasonal != 999 and interval >= 1:
                minp=12
                lim=8
            else:
                minp=12
                lim=8
            corrs_df = combined_df.interpolate(method='pchip', limit_area='inside', limit=lim)
            combined_df.interpolate(method='pchip', inplace=True, limit_area='inside')
            if seasonal!=999 and interval>=1:
                offset = combined_df.index[0].month
                offset = ( offset + 2) / 3 - 1  # 0 for winter(nov-jan), 1 for spring (feb-apr), 2 for summer (may-jul), 3 for fall (aug-oct)
                st_season = int(seasonal - offset)
                if st_season < 0:
                    st_season += 4
                combined_df = combined_df.resample('Q-APR').mean()
                combined_df = combined_df.iloc[st_season::4, :]
            else:
                combined_df = combined_df.resample('3M').mean()
            combined_df.interpolate(method='pchip',inplace=True,limit_area='inside')
            interpolation_df = combined_df.drop(combined_df.filter(regex='Short').columns, axis=1)
            combined_df['linear'] = np.linspace(0, 1, len(combined_df))
            corr_df = corrs_df.corr(min_periods=minp)
            corr_df = corr_df - np.identity(len(corr_df))
            length = len(corr_df) - 1
            for row in corr_df.index:
                if 'Short' in str(row):
                    corr_df = corr_df.drop(row)

            for i in range(length):  # length
                reflist = np.array(corr_df.nlargest(5, corr_df.columns[i]).index)
                welli = corr_df.columns[i]
                if 'Short' in str(welli):
                    reflist = np.append(reflist, 'linear')
                    mydf = combined_df[[welli]].copy()
                    print("Well ", welli)
                    corr_values = corr_df.nlargest(5, corr_df.columns[i]).values[:, i]
                    print(corr_values)
                    delete_list = []
                    for j in range(len(corr_values)):
                        if corr_values[j] <= 0.75:
                            delete_list.append(j)
                    if len(delete_list) > 0:
                        reflist = np.delete(reflist, delete_list)
                    if len(reflist) >= 1:
                        for ref in reflist:
                            mydf = pd.concat([mydf, combined_df[ref]], axis=1)
                        norm_exdf = mydf.dropna(how="any", subset=reflist)
                        normz_exdf = norm_exdf.copy()
                        for column in norm_exdf.columns[0:]:
                            normz_exdf[column] = (norm_exdf[column] - norm_exdf[column].min()) / (
                                norm_exdf[column].max() - norm_exdf[column].min())
                        exdf = normz_exdf.copy()
                        try:
                            mymin = max(exdf[welli].first_valid_index(), exdf[reflist[0]].first_valid_index())
                        except:
                            print("error in mymin")
                            continue
                        mymax = exdf[welli].last_valid_index()
                        exdf = exdf[mymin:mymax]  # exdf[welli].first_valid_index()+pd.DateOffset(years=10)
                        y = exdf[welli]
                        x = exdf.as_matrix(columns=reflist)
                        try:
                            # THese three lines are new
                            n,m=x.shape
                            x0=np.ones((n,1))
                            x=np.hstack((x,x0))
                            model = sm.OLS(y, x)
                            model_fit = model.fit_regularized(alpha=0.005)
                            b = np.array(model_fit.params)
                            A = normz_exdf.as_matrix(columns=reflist)
                            n, m = A.shape
                            A0 = np.ones((n, 1))
                            A = np.hstack((A, A0))
                            norm_exdf['prediction'] = np.dot(A, b)
                            norm_exdf['prediction'] = norm_exdf['prediction'] * (norm_exdf[welli].max() - norm_exdf[welli].min()) + \
                                                      norm_exdf[welli].min()
                            norm_exdf.loc[corrs_df[welli].notnull(), 'prediction'] = corrs_df[welli]
                            newname = str(welli).replace('Short', '')
                            interpolation_df = pd.concat([interpolation_df, norm_exdf['prediction']], join="outer", axis=1)
                            interpolation_df = interpolation_df.rename(columns={"prediction": newname})
                        except:
                            print("error for well ",welli,". ")
            print("Finished MLR temporal interpolation")
            newinterpolation_df = interpolation_df[str(start_date):str(
                end_date)].resample(resample_rate, closed='left').nearest()
        else:
            # This code interpolates the timeseries values at each well using the pchip interpolation method. The data is extended up to the
            # time_tolerance limit using the value of the nearest data point.
            wells_df = pd.DataFrame()
            for well in points['features']:
                welli = well['properties']['HydroID']
                if 'TsTime' in well:
                    if len(well['TsTime']) >= min_samples:
                        listlength = len(well['TsTime'])
                        length_time = end_time - start_time
                        mylength_time = min(well['TsTime'][listlength - 1] - well['TsTime'][0],
                                            max(well['TsTime'][listlength - 1] - start_time, 0),
                                            max(end_time - well['TsTime'][0], 0))
                        ratio = abs((float(mylength_time) / length_time))
                        if ratio > min_ratio:
                            df = pd.DataFrame(index=pd.to_datetime(
                                well['TsTime'], unit='s', origin='unix'), data=well['TsValue'], columns=[welli])
                            df = df[np.logical_not(df.index.duplicated())]
                            try:
                                wells_df = pd.concat([wells_df, df], join="outer", axis=1)
                            except:
                                print("exception")
                                continue
            if seasonal!=999 and interval>=1:
                offset = wells_df.index[0].month
                offset = ( offset + 2) / 3 - 1  # 0 for winter(nov-jan), 1 for spring (feb-apr), 2 for summer (may-jul), 3 for fall (aug-oct)
                st_season = seasonal - offset
                if st_season < 0:
                    st_season += 4
                wells_df = wells_df.resample('Q-APR').mean()
                wells_df = wells_df.iloc[st_season::4, :]
                wells_df = wells_df[str(start_date):str(end_date)].interpolate('nearest', limit=time_tolerance, limit_direction='both',
                                                fill_value="extrapolate").resample(resample_rate).nearest()
            else:
                stime=str(start_date-date_shift)+'-12-25 00:00:00'
                if date_shift==2:
                    date_shift=0
                etime=str(end_date-date_shift+1)
                wells_df = wells_df.interpolate(method='pchip', limit_area='inside').resample('3M').nearest()[
                           stime:etime]
                wells_df = wells_df[str(start_date):str(end_date)].interpolate('nearest', limit=4 * time_tolerance, limit_direction='both',
                                                fill_value="extrapolate").resample(resample_rate).nearest()
            print("Completed pchip temporal interpolation")
            newinterpolation_df = wells_df

    lons = []
    lats = []
    values = []
    elevations = []
    heights = []
    ids = []
    mylon = []
    mylat = []
    myelevs = []
    myids = []
    for wellid in newinterpolation_df.columns:
        for well in points['features']:
            if wellid == str(well['properties']['HydroID']) or wellid == well['properties']['HydroID']:
                mylon.append(well['geometry']['coordinates'][0])
                mylat.append(well['geometry']['coordinates'][1])
                myelevs.append(well['properties']['LandElev'])
                myids.append(str(wellid))
                break
    mylon = np.array(mylon)
    mylat = np.array(mylat)
    myelevs = np.array(myelevs)
    myids = np.array(myids)
    valueslist = []
    for i in range(iterations):
        myvalue = np.array(newinterpolation_df.iloc[i].tolist())
        heights.append(myelevs)
        valueslist.append(myvalue)
        x = np.isnan(myvalue)
        myelev = np.add(np.array(myelevs), myvalue)
        lons.append(mylon[np.logical_not(x)])
        lats.append(mylat[np.logical_not(x)])
        values.append(myvalue[np.logical_not(x)])
        elevations.append(myelev[np.logical_not(x)])
        ids.append(myids)
        print(len(mylon))
    lons = np.array(lons)
    lats = np.array(lats)
    values = np.array(values)
    elevations = np.array(elevations)
    ids = np.array(ids)
    valueslist = np.array(valueslist)
    # Now we prepare the data for the generate_variogram function
    coordinates = []
    all_empty = True
    for i in range(0, iterations):
        coordinate = np.array((lons[i], lats[i])).T
        coordinates.append(coordinate)
        if len(coordinate) > 1:
            all_empty = False
    if all_empty == True:
        message = "There is not enough data to perform interpolation"
        print(message)
        return message
    coordinates = np.array(coordinates)
    variogram_function = spherical_variogram_model
    variogram_model_parameters = []
    for i in range(0, iterations):
        print(len(coordinates[i]))
        if len(coordinates[i]) > 2:
            X = coordinates[i]
            if interpolation_options == "depth":
                y = values[i]
            else:
                y = elevations[i]
            variogram_model_parameters.append(generate_variogram(X, y, variogram_function))
        else:
            variogram_model_parameters.append([0, 0, 0])
    print(variogram_model_parameters)

    AquiferShape = {
        'type': 'FeatureCollection',
        'features': []
    }

    Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
    session = Session()

    aquifersession = session.query(Aquifers).filter(Aquifers.RegionName == region.replace("_", " "),
                                                    Aquifers.AquiferID == str(aquifer_number))
    for object in aquifersession:
        dem_json = object.AquiferDEM
        AquiferShape = object.AquiferShapeJSON

    if len(AquiferShape['features']) < 1:
        regionsession = session.query(Regions).filter(Regions.RegionName == region.replace("_", " "))
        for object in regionsession:
            AquiferShape = object.RegionJSON

    session.close()
    lonmin, latmin, lonmax, latmax = bbox(AquiferShape['features'][0])
    latgrid = np.mgrid[latmin:latmax:resolution]
    longrid = np.mgrid[lonmin:lonmax:resolution]
    latrange = len(latgrid)
    lonrange = len(longrid)
    nx = (lonmax - lonmin) / resolution
    ny = (latmax - latmin) / resolution

    # Reproject DEM to 0.01 degree resolution using rasterio
    src_crs = dem_json['src_crs']
    src_transform = dem_json['src_transform']
    source = dem_json['source']

    dst_crs = {'init': 'EPSG:4326'}
    dst_transform = from_origin(lonmin, latmax, resolution, resolution)
    dem_array = np.zeros((latrange, lonrange))
    dem_array[:] = np.nan
    reproject(source,
              dem_array,
              src_transform=src_transform,
              src_crs=src_crs,
              dst_transform=dst_transform,
              dst_crs=dst_crs,
              resampling=Resampling.bilinear)
    dem_array = np.array(dem_array)
    dem_array = np.flipud(dem_array)
    dem = np.reshape(dem_array.T, ((lonrange) * latrange))
    if units == "English":
        dem = dem*3.28084  # use this to convert from meters to feet
    dem_grid = np.reshape(dem, (lonrange, latrange))
    dem_grid[dem_grid <= -99] = -9999
    outx = np.repeat(longrid, latrange)
    outy = np.tile(latgrid, lonrange)
    depth_grids = []
    elev_grids = []

    for i in range(0, iterations):
        # searchradius = 2#((latmin-latmax)**2+(lonmin-lonmax)**2)**.5
        # ndmax = 15#len(elevations[i])/5
        # ndmin = 5#max(ndmax /4,1)
        if ndmin == 999:
            ndmin = len(lons[i])
        if ndmax == 999:
            ndmax = len(lons[i])
        noct = 0
        nugget = 0
        sill = variogram_model_parameters[i][0]
        vrange = variogram_model_parameters[i][1]
        if len(lons[i]) > 2:
            params = {
                'x': lons[i],
                'y': lats[i],
                'vr': values[i],
                'nx': nx,
                'ny': ny,
                'nz': 1,
                'xmn': lonmin,
                'ymn': latmin,
                'zmn': 0,
                'xsiz': resolution,
                'ysiz': resolution,
                'zsiz': 1,
                'nxdis': 1,
                'nydis': 1,
                'nzdis': 1,
                'outx': outx,
                'outy': outy,
                'radius': searchradius,
                'radius1': searchradius,
                'radius2': searchradius,
                'ndmax': ndmax,
                'ndmin': ndmin,
                'noct': noct,
                'ktype': 1,
                'idbg': 0,
                'c0': nugget,
                'it': 1,
                'cc': sill,
                'aa': vrange,
                'aa1': vrange,
                'aa2': vrange
            }
            if interpolation_type == "Kriging with External Drift":
                params['vr'] = elevations[i]
                params['ve'] = heights[i]
                params['outextve'] = dem
                params['ktype'] = 3
            elif interpolation_options == "elev":
                params['vr'] = elevations[i]
            estimate = pygslib.gslib.kt3d(params)
            idwarray = estimate[0]['outidpower']
            if interpolation_type == "IDW":
                array = idwarray
            else:
                array = estimate[0]['outest']
            if interpolation_options == "both":
                params['vr'] = elevations[i]
                elev_estimate = pygslib.gslib.kt3d(params)
                elev_idwarray = elev_estimate[0]['outidpower']
                if interpolation_type == "IDW":
                    elev_array = elev_idwarray
                else:
                    elev_array = elev_estimate[0]['outest']
                elev_grid = np.reshape(elev_array, (lonrange, latrange))
                idw_elev_grid = np.reshape(elev_idwarray, (lonrange, latrange))
                x = np.isnan(elev_grid)
                print(np.isnan(elev_grid).sum() / elev_grid.size * 100.0, " % idw in Elev Grid")
                elev_grid[x] = idw_elev_grid[x]

            depth_grid = np.reshape(array, (lonrange, latrange))
            idw_grid = np.reshape(idwarray, (lonrange, latrange))
            x = np.isnan(depth_grid)
            print(np.isnan(depth_grid).sum() / depth_grid.size * 100.0, " % idw in Depth Grid")
            depth_grid[x] = idw_grid[x]

            if interpolation_type == "Kriging with External Drift" or interpolation_options == "elev":
                elev_grid = depth_grid
                depth_grid = elev_grid - dem_grid
            elif interpolation_options != "both":
                elev_grid = dem_grid + depth_grid
                elev_grid[elev_grid <= -9000] = -9999
            depth_grids.append(depth_grid)
            elev_grids.append(elev_grid)
            print(i)
        else:
            depth_grid = np.full((lonrange, latrange), -9999)
            elev_grid = depth_grid
            depth_grids.append(depth_grid)
            elev_grids.append(elev_grid)
    depth_grids = np.array(depth_grids)
    elev_grids = np.array(elev_grids)

    temp_dir = tempfile.mkdtemp()

    myshapefile = os.path.join(temp_dir, "shapefile.json")
    with open(myshapefile, 'w') as outfile:
        json.dump(AquiferShape, outfile)
    # end if statement

    latlen = len(latgrid)
    lonlen = len(longrid)

    # name=name.replace(' ','_')
    # name=name+'.nc'
    # filename = name
    myunit = "m"
    volunit = "Cubic Meters"
    if units == "English":
        myunit = "ft"
        volunit = "Acre-ft"

    filename = date_name+".nc"
    nc_file = os.path.join(temp_dir, filename)
    h = netCDF4.Dataset(nc_file, 'w', format="NETCDF4")

    # Global Attributes
    h.start_date = start_date
    h.end_date = end_date
    h.interval = interval
    h.resolution = resolution
    h.min_samples = min_samples
    h.min_ratio = min_ratio
    h.time_tolerance = time_tolerance
    h.default = make_default
    h.interpolation = interpolation_type
    h.interp_options = interpolation_options
    h.units = units
    h.temporal_interpolation = temporal_interpolation

    time = h.createDimension("time", 0)
    lat = h.createDimension("lat", latlen)
    lon = h.createDimension("lon", lonlen)
    hydroid = h.createDimension("hydroid", len(ids[0]))
    latitude = h.createVariable("lat", np.float64, ("lat"))
    longitude = h.createVariable("lon", np.float64, ("lon"))
    time = h.createVariable("time", np.float64, ("time"), fill_value="NaN")
    depth = h.createVariable("depth", np.float64, ('time', 'lon', 'lat'), fill_value=-9999)
    elevation = h.createVariable("elevation", np.float64, ('time', 'lon', 'lat'), fill_value=-9999)
    hydroids = h.createVariable("hydroid", str, ("hydroid"), fill_value="NaN")
    hydroids.axis = "H"

    tsvalue = h.createVariable("tsvalue", np.float64, ('time', 'hydroid'), fill_value=-9999)
    tsvalue.units = myunit
    tsvalue.coordinates = "time hydroid"

    elevation.long_name = "Elevation of Water Table"
    elevation.units = myunit
    elevation.grid_mapping = "WGS84"
    elevation.cell_measures = "area: area"
    elevation.coordinates = "time lat lon"

    depth.long_name = "Depth to Water Table"
    depth.units = myunit
    depth.grid_mapping = "WGS84"
    depth.cell_measures = "area: area"
    depth.coordinates = "time lat lon"

    drawdown = h.createVariable("drawdown", np.float64, ('time', 'lon', 'lat'), fill_value=-9999)
    drawdown.long_name = "Well Drawdown Since "+str(start_date)
    drawdown.units = myunit
    drawdown.grid_mapping = "WGS84"
    drawdown.cell_measures = "area: area"
    drawdown.coordinates = "time lat lon"

    volume = h.createVariable("volume", np.float64, ('time', 'lon', 'lat'), fill_value=-9999)
    volume.long_name = "Change in aquifer storage volume since " + str(start_date)
    volume.units = volunit
    volume.grid_mapping = "WGS84"
    volume.cell_measures = "area: area"
    volume.coordinates = "time lat lon"

    latitude.long_name = "Latitude"
    latitude.units = "degrees_north"
    latitude.axis = "Y"
    longitude.long_name = "Longitude"
    longitude.units = "degrees_east"
    longitude.axis = "X"
    time.axis = "T"
    time.units = 'days since 0001-01-01 00:00:00 UTC'
    latitude[:] = latgrid[:]
    longitude[:] = longrid[:]
    hydroids[:] = ids[0, :]
    year = start_date
    timearray = []  # [datetime.datetime(2000,1,1).toordinal()-1,datetime.datetime(2002,1,1).toordinal()-1]
    t = 0
    for i in range(0, iterations):
        month_to_put=1
        if seasonal!=999:
            month_to_put=(seasonal+1)*3-2
        tsvalue[i, :] = valueslist[i, :]
        interpolatable = True
        if len(values[i]) < 3 or len(elevations[i]) < 3:
            interpolatable = False

        if sixmonths == False:
            year = int(year)
            timearray.append(datetime.datetime(year, month_to_put, 1).toordinal())
        elif threemonths == False:
            monthyear = start_date + interval * i
            doubleyear = monthyear * 2
            if doubleyear % 2 == 0:
                monthyear = int(monthyear)
                timearray.append(datetime.datetime(monthyear, 1, 1).toordinal())
            else:
                monthyear = int(monthyear - .5)
                timearray.append(datetime.datetime(monthyear, 7, 1).toordinal())
        else:
            monthyear = start_date + interval * i
            print(monthyear)
            quadyear = monthyear * 4
            if quadyear % 4 == 0:
                targetyear = int(monthyear)
                timearray.append(datetime.datetime(targetyear, 1, 1).toordinal())
            elif quadyear % 4 == 1:
                targetyear = int(monthyear - .25)
                timearray.append(datetime.datetime(targetyear, 4, 1).toordinal())
            elif quadyear % 4 == 2:
                targetyear = int(monthyear - .50)
                timearray.append(datetime.datetime(targetyear, 7, 1).toordinal())
            elif quadyear % 4 == 3:
                targetyear = int(monthyear - .75)
                timearray.append(datetime.datetime(targetyear, 10, 1).toordinal())

        year += interval

        if interpolatable != False:  # for IDW, Kriging, and Kriging with External Drift
            time[t] = timearray[i]
            for y in range(0, latrange):
                depth[t, :, y] = depth_grids[i, :, y]
                elevation[t, :, y] = elev_grids[i, :, y]
                if t == 0:
                    drawdown[t, :, y] = 0
                else:
                    drawdown[t, :, y] = depth[t, :, y] - depth[0, :, y]
                mylatmin = math.radians(latitude[y] - resolution / 2)
                mylatmax = math.radians(latitude[y] + resolution / 2)
                area = 6371000 * math.radians(resolution) * 6371000 * abs(
                    (math.sin(mylatmin) - math.sin(mylatmax)))  # 3959 is the radius of the earth in miles, 6,371,000 is radius in meters
                if units == "English":
                    area = 3959 * math.radians(resolution) * 3959 * abs(
                        (math.sin(mylatmin) - math.sin(mylatmax)))
                    area = area * 640  # convert from square miles to acres by multiplying by 640
                volume[t, :, y] = drawdown[t, :, y] * porosity * area
            t += 1

    h.close()

    # Calls a shellscript that uses NCO to clip the NetCDF File created above to aquifer boundaries
    myshell = 'aquifersubset.sh'
    directory = temp_dir
    shellscript = os.path.join(app_workspace.path, myshell)
    subprocess.call([shellscript, filename, directory, interpolation_type, region,
                     str(resolution), app_workspace.path, thredds_serverpath])
    return "Success. NetCDF File Created"
