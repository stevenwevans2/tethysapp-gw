import os
import sys
from setuptools import setup, find_packages
from tethys_apps.app_installation import custom_develop_command, custom_install_command

### Apps Definition ###
app_package = 'gw'
release_package = 'tethysapp-' + app_package
app_class = 'gw.app:Gw'
app_package_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tethysapp', app_package)

### Python Dependencies ###
dependencies = [
        'pykrige',
        'ujson',
        'numpy',
        'netCDF4',
        'cython',
        'pygslib',
        'rasterio',
        'elevation'
]

setup(
    name=release_package,
    version='0.0.1',
    tags='Hydrology,Groundwater,Timeseries',
    description='This application uses spatial and temporal interpolation of well data to create groundwater level maps and time series.',
    long_description='',
    keywords='',
    author='Steven Evans',
    author_email='stevenwevans2@gmail.com',
    url='',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['tethysapp', 'tethysapp.' + app_package],
    include_package_data=True,
    zip_safe=False,
    install_requires=dependencies,
    cmdclass={
        'install': custom_install_command(app_package, app_package_dir, dependencies),
        'develop': custom_develop_command(app_package, app_package_dir, dependencies)
    }
)
