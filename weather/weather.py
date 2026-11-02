"""Weather data accessor

Access the RESstock/COMstock reference weather or the NSRDB actual weather
for US counties.

Credentials
-----------

Reference weather needs no credentials. Actual weather (a `year` argument)
is downloaded from the NSRDB, which needs an API key from the NLR (formerly
NREL) Developer Network. To get one, run

    weather register

and fill out the form in the browser window (the URL is printed when no
browser is available). Save the credentials in the file given by
`weather.weather.CREDENTIALS` (`~/.nsrdb/credentials.json`) as

    {"YOUR.EMAIL@EXAMPLE.COM": "YOUR_TOKEN"}

Alternatively, when an NSRDB download is first attempted without
credentials, the sign-up form is opened in a browser if one is available,
and a `RuntimeError` is raised that names the credentials file and the
expected format.

Examples
--------

To get the RESstock/COMstock reference weather data for Alameda County CA
use the command

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

To get the actual weather data for Alameda County CA in 2020 use the command

    from weather import Weather
    Weather("CA","Alameda",year=2020)

which outputs the following (2020 is a leap year, so there are 8784 hours)

                               temperature_degF  humidity_pc  global_Wpms  direct_Wpms  diffuse_Wpms
    timestamp                                                                                       
    2020-01-01 00:00:00+00:00              50.9         83.2         37.0         40.0          34.0
    2020-01-01 01:00:00+00:00              49.5         79.7          0.0          0.0           0.0
    2020-01-01 02:00:00+00:00              48.9         80.9          0.0          0.0           0.0
    2020-01-01 03:00:00+00:00              48.7         79.8          0.0          0.0           0.0
    2020-01-01 04:00:00+00:00              48.0         80.3          0.0          0.0           0.0
    ...                                     ...          ...          ...          ...           ...
    2020-12-31 19:00:00+00:00              54.9         60.5        497.0        891.0          70.0
    2020-12-31 20:00:00+00:00              56.7         53.4        506.0        890.0          72.0
    2020-12-31 21:00:00+00:00              57.4         50.7        456.0        859.0          71.0
    2020-12-31 22:00:00+00:00              57.2         50.5        351.0        797.0          63.0
    2020-12-31 23:00:00+00:00              53.6         58.6        207.0        668.0          51.0

    [8784 rows x 5 columns]

Cache
-----

Downloaded weather is saved by the Eudoxys `cache` package in
`CACHEDIR/weather/VERSION/ST/COUNTY/W.csv.gz` (reference weather) or
`W_YEAR.csv.gz` (actual weather), where `CACHEDIR` is the `cache` package
default (inside its installed package folder) unless `Weather.CACHEDIR` is
set. Missing files are first fetched from the Eudoxys WECC data archive
(https://github.com/eudoxys/wecc). Use `Weather(...,refresh=True)` to
download one county again from the source, or `cache clear` to delete the
cache.

To rebuild the cache for every county, for the reference weather and every
year from 2018 to last year (slow; needs NSRDB credentials), run

    python3 -m weather.weather [--refresh] [--verbose] [--quiet] [--debug] [RO[,RO[,...]]]

where `RO` is the code for one of the reliability organizations, e.g., `WECC`.

The options are

- `refresh`: force refresh of the cache from the source
- `verbose`: output informational progress messages
- `quiet`: suppress error messages
- `debug`: output debug log messages

Caveats
-------

- Actual weather is available for the years covered by the NSRDB GOES
  Aggregated v4 dataset (1998 to 2024 when this was written; later years
  are added as they are released). Years outside the dataset fail with a
  `RuntimeError`.

- Reference weather is the COMstock 2018 actual meteorological year only.

References
----------

- Reference weather: NREL, *End-Use Load Profiles for the U.S. Building
  Stock* (2021), ComStock AMY2018 release 1 weather files,
  https://dx.doi.org/10.25984/1876417, licensed CC BY 4.0.

- Actual weather: NSRDB GOES Aggregated v4.0.0,
  https://developer.nlr.gov/docs/solar/nsrdb/nsrdb-GOES-aggregated-v4-0-0-download/,
  downloaded with `pvlib.iotools.get_nsrdb_psm4_aggregated`; use is subject
  to the NLR Developer Network terms of use.
"""

import os
import sys
import datetime as dt
import pytz
import json
import webbrowser
import logging

import pandas as pd
import numpy as np
import pvlib

from cache import Cache
from fips.counties import Counties, County

_version = 1 # cache schema version (1: reference weather uses the county time zone, #3)

CREDENTIALS = "{HOME}/.nsrdb/credentials.json"
"""Location of credentials file"""

SIGNUP = "https://developer.nlr.gov/signup/"
"""URL of NSRDB Developer Network sign-up form"""

_logger = logging.getLogger(__file__)

def credentials_path() -> str:
    """@private Return the path of the NSRDB credentials file

    The path is `CREDENTIALS` with `{HOME}` replaced by the user's home
    folder, resolved when called (not at import) so that importing the
    package does not need the `HOME` environment variable (#6).
    """
    return CREDENTIALS.format(HOME=os.path.expanduser("~"))

def nsrdb_credentials(path:str|None=None) -> tuple[str,str]:
    """@private
    Read NSRDB credentials

    Arguments
    ---------

    - `path`: path to credentials file (default is `credentials_path()`)

    Returns
    -------

    - `str`: email address

    - `str`: access token

    Exceptions
    ----------

    - `RuntimeError`: the credentials file is missing or malformed. When it
      is missing, the NSRDB sign-up form is also opened in a browser if one
      is available.
    """
    if path is None:
        path = credentials_path()
    expected = 'it must contain {"YOUR.EMAIL@EXAMPLE.COM": "YOUR_TOKEN"}'
    try:
        with open(path,"r",encoding="utf-8") as fh:
            credentials = json.load(fh)
    except FileNotFoundError as err:
        opened = False
        try:
            opened = webbrowser.open(SIGNUP)
        except Exception: # pylint: disable=broad-exception-caught
            pass
        _logger.debug(f"browser {'opened' if opened else 'not available'} for {SIGNUP}")
        raise RuntimeError(f"NSRDB credentials file {path} not found; "
            f"register at {SIGNUP} (or run `weather register`) and save "
            f"your credentials in that file ({expected})") from err
    except (OSError,ValueError) as err:
        raise RuntimeError(f"NSRDB credentials file {path} is not readable "
            f"JSON ({expected})") from err

    if not isinstance(credentials,dict) or len(credentials) != 1 \
            or not all(isinstance(x,str) and x for x in next(iter(credentials.items()))):
        raise RuntimeError(f"NSRDB credentials file {path} is malformed ({expected})")
    return next(iter(credentials.items()))

def nsrdb_weather(
    lat:str,
    lon:str,
    year:int,
    ):
    """@private
    Pull NSRDB data for a particular year and location. 
    
    Parameters
    ----------
    
    - `lat`: latitude of weather location

    - `lon`: longitude of weather location

    - `year`: year for which we want weather data
    
    Returns
    -------

    - `pandas.DataFrame`: data frame containing requested weather data
    """
    email, api_key = nsrdb_credentials()
    # Pull from API and save locally
    columns = ["temp_air","relative_humidity","ghi", "dni", "dhi",]
    psm4, _= pvlib.iotools.get_nsrdb_psm4_aggregated(
        lat,
        lon,
        api_key,
        email,
        year=year,
        time_step=60, 
        parameters=columns,
        utc=True, # Set to True for UTC timestamps
        map_variables=True # Renames columns to pvlib standard names
    )
    psm4 = psm4.drop(columns=set(psm4.columns)-set(columns))
    psm4.index = pd.to_datetime(psm4.index)
    return psm4.sort_index()
         
class Weather(pd.DataFrame):
    """Weather data frame implementation"""

    # pylint: disable=invalid-name
    CACHEDIR = None
    """Cache folder path (`None` is default cache folder)"""

    REFERENCE_SOURCE = \
        "https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/"\
        "end-use-load-profiles-for-us-building-stock/2021/comstock_amy2018_release_1/"\
        "weather/amy2018"
    """Source for reference weather when no year is provided"""

    def __init__(self,
        state:str,
        county:str,
        year:int|None=None,
        refresh:bool=False,
        ):
        """Construct weather data frame for a county

        Arguments
        ---------

        - `state`: specify the state abbreviation (required)

        - `county`: specify the county name (required)

        - `year`: specify the actual weather year (default is reference weather)

        - `refresh`: force download of data from source repository, bypassing
          both the local cache and the archive

        Data is obtained from the first of these that has it:

          1. the local cache file;

          2. the cache archives (by default the Eudoxys WECC data archive at
             https://github.com/eudoxys/wecc), which is downloaded into the
             local cache;

          3. the source repository (`REFERENCE_SOURCE` without a `year`, or
             the NSRDB PSM4 aggregated data through `pvlib` with a `year`),
             which is saved to the local cache.

        A cache file that cannot be read is deleted and rebuilt from the
        source repository.

        Exceptions
        ----------

        - `RuntimeError`: the data is not in the cache or the archive and
          the download from the source repository failed (the original
          error is chained as `__cause__`), or the downloaded data is empty
          or lacks a required column
        """

        if self.CACHEDIR:
            Cache.CACHEDIR = self.CACHEDIR
        cache = Cache([state,county,"W.csv.gz" if year is None else f"W_{year}.csv.gz"],
            package="weather",
            version=_version)

        # read from cache, downloading it from the archive if it's not local
        if not refresh and cache.download():

            # load from cache
            try:

                data = pd.read_csv(cache.pathname,
                    index_col=["timestamp"],
                    parse_dates=["timestamp"],
                    )
                _logger.debug(f"{cache.pathname} ok" if cache.archive is None
                    else f"{cache.pathname} ok (downloaded from {cache.archive})")

            except Exception as err:

                data = None
                _logger.debug(f"{cache.pathname} error ({err})")
                cache.delete()

        else:

            _logger.debug(f"{cache.pathname} (re)generation needed")
            data = None

        # download data and save to cache
        if data is None:
            fips = County(ST=state,COUNTY=county).FIPS
            tzoffset = float(Counties(use_index=["ST","COUNTY"]).loc[[(state,county)]].TZOFFSET.iloc[0])
            if year is None:

                # locate the COMstock weather file
                url = f"{self.REFERENCE_SOURCE}/G{fips[:2]}0{fips[2:]}0_2018.csv"

                # download the weather file
                try:
                    data = pd.read_csv(url,
                        usecols=[
                            "date_time",
                            "Dry Bulb Temperature [°C]",
                            "Relative Humidity [%]",
                            "Global Horizontal Radiation [W/m2]", 
                            "Direct Normal Radiation [W/m2]",
                            "Diffuse Horizontal Radiation [W/m2]",
                            ],
                        index_col=["date_time"]
                        )
                except Exception as err:
                    raise RuntimeError(f"{state} {county} reference weather "
                        f"download from {url} failed ({err})") from err

                # fix the timezone
                data.index = pd.DatetimeIndex(data.index,tz=pytz.UTC) - dt.timedelta(hours=tzoffset+1)

                # rename the columns
                data.columns = [
                    "temperature_degF",
                    "humidity_pc",
                    "global_Wpms",
                    "direct_Wpms",
                    "diffuse_Wpms",
                    ]

                # convert to Fahrenheit
                data["temperature_degF"] = (data["temperature_degF"]*9/5+32).round(1)

                # round the humidity and solar values
                data = data.round(1)

                # rotate the records so they're all in the same year
                data.index = pd.DatetimeIndex([str(x).replace("2019","2018") for x in data.index])

            else:

                # get the lat/lon of the county
                latlon = Counties(use_index=["ST","COUNTY"]).loc[[(state,county)]][["LAT","LON"]].values.tolist()[0]

                # download the weather data
                try:
                    data = nsrdb_weather(*latlon, year)
                    if not isinstance(data,pd.DataFrame) or data.empty:
                        raise ValueError("no weather data found")
                except Exception as err:
                    raise RuntimeError(f"{state} {county} {year} NSRDB weather "
                        f"download at {latlon=} failed ({err})") from err

                # rename columns
                columns = {
                    "temp_air":"temperature_degF",
                    "relative_humidity":"humidity_pc",
                    "ghi":"global_Wpms",
                    "dni":"direct_Wpms",
                    "dhi":"diffuse_Wpms",
                }
                missing = [x for x in columns if x not in data.columns]
                if missing:
                    raise RuntimeError(f"{state} {county} {year} NSRDB weather "
                        f"is missing column(s) {missing}")
                data = data.rename(columns,axis=1)

                # convert temperature to Fahrenheit
                data.temperature_degF = data.temperature_degF * 1.8 + 32

                # reorder and round columns 
                data = data[columns.values()].round(1)

                # change date/time index from end-of-interval to start-of-interval
                data.index = (data.index - dt.timedelta(minutes=30)).tz_convert("UTC")

            data = data.sort_index()
            data.index.name = "timestamp"
            data.to_csv(cache.pathname,
                index=True,
                header=True,
                compression="gzip" if cache.name.endswith(".gz") else None,
                )

        super().__init__(data)

    @classmethod
    def makeargs(cls,**kwargs):
        """@private Return dict of accepted kwargs by this class constructor"""
        return {x:y for x,y in kwargs.items()
            if x in cls.__init__.__annotations__}

if __name__ == '__main__':
    
    # script to maintain venv weather cache
    
    from fips.counties import Counties

    pd.options.display.width = None
    pd.options.display.max_columns = None

    if "-h" in sys.argv or "--help" in sys.argv or "help" in sys.argv:
        print("Syntax: python3",os.path.basename(sys.argv[0]),"[--{help,debug,refresh,verbose,quiet}] [RO[,RO[,...]]]")
        exit(0)

    quiet = "--quiet" in sys.argv
    verbose = "--verbose" in sys.argv
    refresh = "--refresh" in sys.argv
    debug = "--debug" in sys.argv
    ro = [x for x in sys.argv[1:] if not x.startswith("-")]
    if not ro:
        ro = np.s_[None:None]

    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)

    for _,state,county in Counties(use_index=["RO","ST","COUNTY"]).loc[ro].index.values:

        # process the reference year and every year from 2018 to last year
        for year in [None] + list(range(2018,dt.datetime.now().year)):
            try:
                values = Weather(state,county,refresh=refresh,year=year)
                if verbose:
                    _logger.info(f"{state} {county} {year} ok")
            except KeyboardInterrupt:
                break
            except Exception as err:
                if not quiet:
                    _logger.error(f"{state} {county} {year} {err}")

