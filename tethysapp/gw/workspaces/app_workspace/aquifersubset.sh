#!/bin/bash
# $1 is the name of the region to process
# $2 is the directory where files are located
# $3 is the type of interpolation
echo "called shellscript"
cd $2
pwd
gdal_rasterize -burn 1 -l shapefile -of netcdf -tr 0.05 0.05 -co "FORMAT=NC4" shapefile.json Aquifer.nc

ncremap -i Aquifer.nc -a nds -d $1 -o Region25.nc

ncap2 -s 'Band1=Band1/Band1;' Region25.nc Region2.nc

ncatted -a _FillValue,,o,d,-9999 Region2.nc

ncks -A Region25.nc $1

ncatted -a _FillValue,,o,d,-9999 $1

ncap2 -s 'Band1=Band1/Band1' $1 temp2.nc

ncap2 -s 'depth=Band1*depth;' temp2.nc temp1.nc

ncap2 -s 'elevation=Band1*elevation;' temp1.nc temp.nc

d='/home/student/tds/apache-tomcat-8.5.30/content/thredds/public/testdata/groundwater/'
#d='/home/tethys/Thredds/groundwater/'

destination=$d$3

rm Aquifer.nc
rm temp2.nc
rm temp1.nc
rm Region2.nc
rm Region25.nc
rm $1
mv temp.nc $1
mv $1 $destination

