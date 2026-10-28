[![Validation](https://github.com/eudoxys/weather/actions/workflows/validate.yaml/badge.svg)](https://github.com/eudoxys/weather/actions/workflows/validate.yaml)
[![Documentation](https://github.com/eudoxys/weather/actions/workflows/deploy-pages.yaml/badge.svg)](https://github.com/eudoxys/weather/actions/workflows/deploy-pages.yaml)

US weather data accessor for bulk power systems modeling and simulation

`weather` produces hourly county weather (temperature, humidity, and global,
direct, and diffuse solar irradiance) on a UTC time index, from the
RESstock/COMstock 2018 reference weather or, for a given year, from the NSRDB.
It is for modelers who need consistent weather inputs for load and power
system studies.

# Documentation

See https://www.eudoxys.com/weather

# Installation

Install using Eudoxys Package Manager:

    pip install --upgrade eudoxys
    epm install weather

Install using `pip`:

    pip install git+https://github.com/eudoxys/weather

# Maintenance

## Update docs

    make docs

## Run tests

    pip install -e . pytest
    pytest

The tests run offline against generated fixture data. The optional live
NSRDB test runs only when NSRDB credentials are installed (`weather register`).
See [`weather/_test/README.md`](weather/_test/README.md).

## Cache build

Downloaded weather is cached by the Eudoxys `cache` package, which first
looks in the Eudoxys WECC data archive (https://github.com/eudoxys/wecc).
To rebuild the cache for every WECC county and the years 2018–2022 from the
sources (slow; needs NSRDB credentials), run

    python3 -m weather.weather --refresh

Add `--debug` for progress messages.

# Examples

## Command line

Get the Alameda County CA reference weather data

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

Get the reference weather data frame Alameda County CA.

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

# Acknowledgments

- This material is based on work supported by the U.S. Department of Energy’s Office of Electricity through a grant from the Grid Controls and Communications Division
