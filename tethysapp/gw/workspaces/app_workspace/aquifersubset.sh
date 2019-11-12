#!/bin/bash
# $1 is the name of the region to process
# $2 is the directory where files are located
# $3 is the type of interpolation
# $4 is the region
# $5 is the grid resolution
# $6 is the app_workspace
# $7 is the thredds_serverpath
echo "called shellscript"
#. /home/tethys/tethys/miniconda/bin/activate nco
cd $2
pwd
gdal_rasterize -burn 1 -l shapefile -of netcdf -tr $5 $5 -co "FORMAT=NC4" shapefile.json Aquifer.nc

ncremap -i Aquifer.nc -a nds -d $1 -o Region25.nc

ncap2 -s 'Band1=Band1/Band1;' Region25.nc Region2.nc

ncatted -a _FillValue,,o,d,-9999 Region2.nc

ncks -A Region25.nc $1

ncatted -a _FillValue,,o,d,-9999 $1

ncap2 -s 'Band1=Band1/Band1' $1 temp4.nc

ncap2 -s 'volume=Band1*volume;' temp4.nc temp3.nc

ncap2 -s 'depth=Band1*depth;' temp3.nc temp2.nc

ncap2 -s 'elevation=Band1*elevation;' temp2.nc temp1.nc

ncap2 -s 'drawdown=Band1*drawdown;' temp1.nc temp.nc

ncwa -N -v volume -a lat,lon temp.nc volume.nc

ncrename -O -v volume,totalvolume volume.nc volume.nc

ncks -O -x -v volume temp.nc temp.nc

ncks -C -A -v totalvolume volume.nc temp.nc

d=$7
#d='/opt/tomcat/content/thredds/public/testdata/groundwater/'

destination=$d$4

rm shapefile.json
rm Aquifer.nc
rm volume.nc
rm temp4.nc
rm temp3.nc
rm temp2.nc
rm temp1.nc
rm Region2.nc
rm Region25.nc
rm $1
mv temp.nc $1
mv $1 $destination

cd $6
python deletetemp.py $2

