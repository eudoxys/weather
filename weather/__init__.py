"""Weather data accessor

Syntax
------
    
    weather [-S STATE] [-C COUNTY] [-Y YEAR]
            [-d] [-h] [-w] [-o OUTPUT]
            {help,info,plot,print,register,viewer}

Commands
--------

  - `help`: open online documentation

  - `info`: get package URLs for source code, documentation, issues and
    license.

  - `plot`: output plot

  - `print`: output data

  - `register`: open the NSRDB registration form

  - `viewer`: open Marimo notebook

Options
-------
  
  - `-C|--county COUNTY`: county name of weather data to collect
  
  - `-d|--debug`: enable debug traceback on exceptions

  - `-h|--help`: show this help message and exit
  
  - `-o|--output OUTPUT`: output file name

  - `-S|--state STATE`: state abbreviation of county
  
  - `-w|--warning`: enable warning messages from python

  - `-Y|--year YEAR`: year of weather data to collect
  

Description
-----------

The `weather` package provides access to RESstock/COMstock reference weather
and NSRDB actual weather.

The following weather data are obtained:

  - `temperature_degF`: the outdoor air temperature in degrees Fahrenheit,

  - `humidity_pc`: the relative humidity in %,

  - `global_Wpms`: the global horizontal solar irradiance in Watts per square meter,

  - `direct_Wpms`: the direct normal solar irradiance in Watts per square meter, and

  - `diffuse_Wpms`: the global diffuse solar irradiance in Watts per square meter.

The time index is provided in UTC. A year is defined as starting January 1 at
midnight UTC and ending December 31 at 23:59:59 UTC regardless of the local
timezone.  Weather data is provided in hourly time-steps and rounded to 1
decimal place. Leap years have 8784 hours of data and non-leap years have
8760 hours of data.

Example
-------

To print the reference weather for Alameda County CA use the command

    weather print -S=CA -C=Alameda

which outputs the following

                               temperature_degF  humidity_pc  global_Wpms  direct_Wpms  diffuse_Wpms
    timestamp                                                                                       
    2018-01-01 00:00:00+00:00              54.0         23.4         40.5         63.0          32.0
    2018-01-01 01:00:00+00:00              52.0         26.3          2.0         12.0           2.0
    2018-01-01 02:00:00+00:00              51.1         28.6          0.0          0.0           0.0
    .
    .
    .
    2018-12-31 21:00:00+00:00              57.9         21.2        489.5        927.0          63.5
    2018-12-31 22:00:00+00:00              57.9         20.3        397.5        880.0          58.5
    2018-12-31 23:00:00+00:00              57.0         20.9        254.0        746.0          52.0

To access the same weather data using Python, use the command

    from weather import Weather
    Weather("CA","Alameda")

which outputs the following

                               temperature_degF  humidity_pc  global_Wpms  direct_Wpms  diffuse_Wpms
    timestamp                                                                                       
    2018-01-01 00:00:00+00:00              54.0         23.4         40.5         63.0          32.0
    2018-01-01 01:00:00+00:00              52.0         26.3          2.0         12.0           2.0
    2018-01-01 02:00:00+00:00              51.1         28.6          0.0          0.0           0.0
    2018-01-01 03:00:00+00:00              51.1         24.7          0.0          0.0           0.0
    2018-01-01 04:00:00+00:00              51.1         26.0          0.0          0.0           0.0
    ...                                     ...          ...          ...          ...           ...
    2018-12-31 19:00:00+00:00              57.0         23.0        495.5        943.0          58.0
    2018-12-31 20:00:00+00:00              57.9         21.2        523.5        951.0          61.5
    2018-12-31 21:00:00+00:00              57.9         21.2        489.5        927.0          63.5
    2018-12-31 22:00:00+00:00              57.9         20.3        397.5        880.0          58.5
    2018-12-31 23:00:00+00:00              57.0         20.9        254.0        746.0          52.0

    [8760 rows x 5 columns]

Package information
-------------------

- Source code: https://github.com/eudoxys/weather

- Documentation: https://www.eudoxys.com/weather

- Issues: https://github.com/eudoxys/weather/issues

- License: https://github.com/eudoxys/weather/blob/main/LICENSE
"""

from .weather import Weather
from .cli import main
