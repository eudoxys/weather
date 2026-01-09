US weather data accessor for bulk power systems modeling and simulation

# Documentation

See https://www.eudoxys.com/weather

# Installation

    pip install git+https://github.com/eudoxys/weather

# Examples

## Command line

Get the Alameda county California reference weather data

    loads print -S=CA -C=Alameda

Outputs

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

## Python code

Get the COMstock data frame for medium office buildings in Alameda County CA.

    from weather import Weather
    Weather(state="CA",county="Alameda")

Outputs

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
