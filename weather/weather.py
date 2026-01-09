"""Weather data accessor

Access the RESstock/COMstock or NSRB weather data for US.

# Example

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
import datetime as dt
import pytz
import json

import pandas as pd
# import h5pyd as h5
import numpy as np
from scipy.spatial import cKDTree
import pvlib

from cache import Cache
from fips.counties import County
from fips.states import State

_nsrdb = None
_nsrdb_meta = None
_version = 0 # cache schema version

def nsrdb_credentials(path=os.path.join(os.environ["HOME"],".nsrdb","credentials.json")):
    """Read NSRDB credentials"""
    with open(path,"r") as fh:
        return list(json.load(fh).items())[0]
        
def nsrdb_weather(lat,lon,year,
                  interval=30,
                  attributes={"ghi" : "ghi",
                              "temp_air" : "air_temperature",
                              "wind_speed" : "wind_speed",
                              'dhi': 'dhi',
                              'dni': 'dni',
                              'wind_direction': 'wind_direction',
                              'dew_point': 'dew_point',
                              'relative_humidity': 'relative_humidity',
                              'total_precipitable_water': 'total_precipitable_water'
                              }):
    """
    Pull NSRDB data for a particular year and location. 
    
    Parameters
    ----------
    location: Str.
        Geohash of a particular location that will be decoded to get lat-long
        coordinates.
    year: Int.
        Year of data we want to pull data for.
    interval: Int.
        Frequency of data in minutes. Default 5
    attributes: Dictionary of string keys/values.
        Desired data fields to return as values, and final column names as keys.
        See pvlib documentaton for the full list of fields in NSRDB:
        https://pvlib-python.readthedocs.io/en/v0.9.0/generated/pvlib.iotools.get_psm3.html
    
    Returns
    -------
    Pandas dataframe containing 'attribute' fields, with UTC ISO format
    datetime index.
    """
    leap = (year%4 == 0)
    email, api_key = nsrdb_credentials()
    # Pull from API and save locally
    psm4, _= pvlib.iotools.get_nsrdb_psm4_aggregated(
        lat,
        lon,
        api_key,
        email,
        year=year,
        time_step=interval, 
        parameters=["ghi", "dni", "dhi", "temp_air", 
                    "wind_speed", 'wind_direction',
                    'dew_point', 'relative_humidity', 
                    'total_precipitable_water'], # Example parameters
        utc=True, # Set to True for UTC timestamps
        map_variables=True # Renames columns to pvlib standard names
    )
    cols_to_remove = ['Year', 'Month', 'Day', 'Hour', 'Minute']
    psm4 = psm4.drop(columns=cols_to_remove)
    psm4.index = pd.to_datetime(psm4.index)
    psm4.rename(columns={"key_0": "datetime",
                         **{v: k for k, v in attributes.items()}},
                inplace=True)
    psm4 = psm4.round(3)  
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

        # Arguments

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
                url = f"{self.REFERENCE_SOURCE}/G{fips[:2]}0{fips[2:]}0_2018.csv"
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
                data.index = pd.DatetimeIndex(data.index,tz=pytz.UTC) - dt.timedelta(hours=tzoffset+1)
                data.columns = [
                    "temperature_degF",
                    "humidity_pc",
                    "global_Wpms",
                    "direct_Wpms",
                    "diffuse_Wpms",
                    ]
                data["temperature_degF"] = (data["temperature_degF"]*9/5+32).round(1)
                data["humidity_pc"] = data["humidity_pc"].round(1)
                data.index = pd.DatetimeIndex([str(x).replace("2019","2018") for x in data.index])
                data.index.name = "timestamp"
                data.sort_index(inplace=True)

            else:

                latlon = Counties(use_index=["ST","COUNTY"]).loc[state,county][["LAT","LON"]].values.tolist()[0]
                data = nsrdb_weather(*latlon, year, interval=60)
                columns = {
                    "temp_air":"temperature_degF",
                    "relative_humidity":"humidity_pc",
                    "ghi":"global_Wpsm",
                    "dni":"direct_Wpsm",
                    "dhi":"diffuse_Wpsm",
                }
                data.drop(set(data.columns)-set(columns),inplace=True,axis=1)
                data.rename(columns,inplace=True,axis=1)
                data.temperature_degF = data.temperature_degF * 1.8 + 32
                data = data[columns.values()].round(1)
                data.index.name = "timestamp"
                data.index = data.index - dt.timedelta(minutes=30)
                # print(data)

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
                print(f"{state} {county} {year=}")
                # print(values)
                print(pd.DataFrame({
                    "Mean":values.mean().T,
                    "Min":values.min().T,
                    "Max":values.max().T,
                    "Stdev":values.std().T,
                    }).round(1))
        except Exception as err:
            raise

