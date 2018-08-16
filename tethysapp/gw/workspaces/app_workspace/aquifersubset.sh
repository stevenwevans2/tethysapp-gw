#!/bin/bash
# $1 is the name of the region to process
# $2 is the directory where files are located
# $3 is the type of interpolation
# $4 is the region
# $5 is the grid resolution
echo "called shellscript"
cd $2
pwd
gdal_rasterize -burn 1 -l shapefile -of netcdf -tr $5 $5 -co "FORMAT=NC4" shapefile.json Aquifer.nc

ncremap -i Aquifer.nc -a nds -d $1 -o Region25.nc

ncap2 -s 'Band1=Band1/Band1;' Region25.nc Region2.nc

ncatted -a _FillValue,,o,d,-9999 Region2.nc

ncks -A Region25.nc $1

ncatted -a _FillValue,,o,d,-9999 $1

ncap2 -s 'Band1=Band1/Band1' $1 temp3.nc

ncap2 -s 'depth=Band1*depth;' temp3.nc temp2.nc

ncap2 -s 'elevation=Band1*elevation;' temp2.nc temp1.nc

ncap2 -s 'drawdown=Band1*drawdown;' temp1.nc temp.nc

#d='/home/student/tds/apache-tomcat-8.5.30/content/thredds/public/testdata/groundwater/'
d='/home/tethys/Thredds/groundwater/'

destination=$d$4'/'$3

sudo rm Aquifer.nc
sudo rm temp3.nc
sudo rm temp2.nc
sudo rm temp1.nc
sudo rm Region2.nc
sudo rm Region25.nc
sudo rm $1
sudo mv temp.nc $1
sudo mv $1 $destination

