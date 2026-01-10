"""Weather data accessor

Syntax
------
    
    weather [-h] [-S STATE] [-C COUNTY] [-Y YEAR] [-o OUTPUT] [-w] [-d] {viewer,print,plot}

Commands
--------

  - `viewer`: open Marimo notebook

  - `print`: output data
  
  - `plot`: output plot

  - `register`: open the NSRDB registration form

  - `help`: open online documentation

Options
-------
  
  - `-h|--help`: show this help message and exit
  
  - `-S|--state STATE`: state abbreviation of county
  
  - `-C|--county COUNTY`: county name of weather data to collect
  
  - `-Y|--year YEAR`: year of weather data to collect
  
  - `-o|--output OUTPUT`: output file name

  - `-w|--warning`: enable warning messages from python

  - `-d|--debug`: enable debug traceback on exceptions

Description
-----------

The `weather` package provides access to RESstock/COMstock reference weather
and NSRDB actual weather.

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

Package information
-------------------

- Source code: https://github.com/eudoxys/weather

- Documentation: https://www.eudoxys.com/weather

- Issues: https://github.com/eudoxys/weather/issues

- License: https://github.com/eudoxys/weather/blob/main/LICENSE
"""

from .weather import Weather
from .cli import main
