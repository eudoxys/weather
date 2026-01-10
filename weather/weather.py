"""Weather data accessor

Access the RESstock/COMstock or NSRB weather data for US.

Credentials
-----------

To access the NSRDB data you must obtain a token from NLR (formerly NREL).
You can install your access token by running the following command

    weather register

and filling out the form in the browser window. Alternative, when you first
attempt to access, the same sign-up form will be opened automatically if you
are running on a system with a terminal. Otherwise, an exception is raised
with guidance on how to sign up.

Example
-------

To get the RESstock/COMstock reference weather data for Alameda County CA use
the command

    from weather import Weather
    Weather("CA","Alameda")

which outputs the following

                                temperature_degF  ...    diffuse_Wpms
    2018-01-01 00:00:00+00:00              53.96  ...            32.0
    2018-01-01 01:00:00+00:00              51.98  ...             2.0
    2018-01-01 02:00:00+00:00              51.08  ...             0.0
    2018-01-01 03:00:00+00:00              51.08  ...             0.0
    2018-01-01 04:00:00+00:00              51.08  ...             0.0
    ...                                      ...  ...             ...
    2018-12-31 19:00:00+00:00              57.02  ...            58.0
    2018-12-31 20:00:00+00:00              57.92  ...            61.5
    2018-12-31 21:00:00+00:00              57.92  ...            63.5
    2018-12-31 22:00:00+00:00              57.92  ...            58.5
    2018-12-31 23:00:00+00:00              57.02  ...            52.0

    [8760 rows x 5 columns]

To get the actual weather data for Alameda County CA in 2020 use the command

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
"""

import os
import sys
import datetime as dt
import pytz
import json
import webbrowser

import pandas as pd
# import h5pyd as h5
import numpy as np
from scipy.spatial import cKDTree
import pvlib

from cache import Cache
from fips.counties import Counties, County
from fips.states import State

_nsrdb = None
_nsrdb_meta = None
_version = 0 # cache schema version

CREDENTIALS = "{HOME}/.nsrdb/credentials.json"
"""Location of credentials file"""

SIGNUP = "https://developer.nrel.gov/signup/"
"""URL of NSRDB Developer Network sign-up form"""

def nsrdb_credentials(path=CREDENTIALS.format(HOME=os.environ["HOME"])):
    """@private 
    Read NSRDB credentials

    Arguments
    ---------

    - `path`: path to credentials file (defaults to `weather.weather.CREDENTIALS`)

    Returns
    -------

    - `str`: email address

    - `str`: access token
    """
    try:
        with open(path,"r") as fh:
            return list(json.load(fh).items())[0]
    except FileNotFoundError:
        print("ERROR: You are not registered with the NSRDB Developer Network. ",
            file=sys.stderr)

    try:
        webbrowser.open(SIGNUP)
        print("Please fill out the NSRDB Developer Network registration form in the browser window.",
            file=sys.stderr)
        raise FileNotFoundError(path)
    except FileNotFoundError:
        pass
    except:
        print(f"See {SIGNUP} to register with the NSRDB Developer Network",
            file=sys.stderr)
        raise
        
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
    leap = (year%4 == 0)
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
    psm4.drop(columns=set(psm4.columns)-set(columns),inplace=True)
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

    ACTUAL_SOURCE = "/nrel/nsrdb/GOES/aggregated/v4.0.0/nsrdb_{year}.h5"
    """Source for actual weather when a year is provided"""

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

        - `refresh`: force download of data from source repository
        """

        if self.CACHEDIR:
            Cache.CACHEDIR = self.CACHEDIR
        cache = Cache([state,county,"W.csv.gz" if year is None else f"W_{year}.csv.gz"],
            package="weather",
            version=_version)

        # read from cache
        if cache.exists() and not refresh:

            # load from cache
            try:
                data = pd.read_csv(cache.pathname,
                    index_col=["timestamp"],
                    parse_dates=["timestamp"],
                    )
            except:

                data = None

        else:

            data = None

        # download data and save to cache
        if data is None:
            fips = County(ST=state,COUNTY=county).FIPS
            tzoffset = float(State(ST=state).TZOFFSET)
            if year is None:

                # locate the COMstock weather file
                url = f"{self.REFERENCE_SOURCE}/G{fips[:2]}0{fips[2:]}0_2018.csv"

                # download the weather file
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

                # round the humidity values
                data["humidity_pc"] = data["humidity_pc"].round(1)

                # rotate the records so they're all in the same year
                data.index = pd.DatetimeIndex([str(x).replace("2019","2018") for x in data.index])

            else:

                # get the lat/lon of the county
                latlon = Counties(use_index=["ST","COUNTY"]).loc[state,county][["LAT","LON"]].values.tolist()[0]

                # download the weather data
                data = nsrdb_weather(*latlon, year)

                # correct correct names and drop unwanted columns
                columns = {
                    "temp_air":"temperature_degF",
                    "relative_humidity":"humidity_pc",
                    "ghi":"global_Wpms",
                    "dni":"direct_Wpms",
                    "dhi":"diffuse_Wpms",
                }
                data.drop(set(data.columns)-set(columns),inplace=True,axis=1)
                data.rename(columns,inplace=True,axis=1)

                # convert temperature to Fahrenheit
                data.temperature_degF = data.temperature_degF * 1.8 + 32

                # reorder and round columns 
                data = data[columns.values()].round(1)

                # change date/time index from end-of-interval to start-of-interval
                data.index = data.index - dt.timedelta(minutes=30) 

            data.sort_index(inplace=True)
            data.index.name = "timestamp"
            data.to_csv(cache.pathname,
                index=True,
                header=True,
                compression="gzip" if cache.name.endswith(".gz") else None,
                )

        # move year-end data to beginning
        super().__init__(data)

    @classmethod
    def makeargs(cls,**kwargs):
        """@private Return dict of accepted kwargs by this class constructor"""
        return {x:y for x,y in kwargs.items()
            if x in cls.__init__.__annotations__}

if __name__ == '__main__':
    
    from fips.counties import Counties

    pd.options.display.width = None
    pd.options.display.max_columns = None

    for state,county in Counties(use_index=["RO","ST","COUNTY"]).loc["WECC"].index.values:
        print("Processing",state,county,end="...",flush=True)
        try:
            print("ok")
            for year in [None,2018,2019,2020,2021,2022]:
                values = Weather(state,county,refresh=False,year=year)
                # print(f"{state} {county} {year=}")
                # print(values)
                # print(pd.DataFrame({
                #     "Mean":values.mean().T,
                #     "Min":values.min().T,
                #     "Max":values.max().T,
                #     "Stdev":values.std().T,
                #     }).round(1))
        except Exception as err:
            raise

