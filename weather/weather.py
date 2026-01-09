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
import pandas as pd
import h5pyd as h5
import numpy as np
from scipy.spatial import cKDTree
from cache import Cache
from fips.counties import County
from fips.states import State

_nsrdb = None
_nsrdb_meta = None
_version = 0 # cache schema version

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
        cache = Cache([state,county,"W.csv.gz" if year is None else f"W_{year}.csv"],
            package="weather",
            version=_version)

        # download data and save to cache
        if not cache.exists() or refresh:

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

                global _nsrdb
                if _nsrdb is None:
                    _nsrdb = h5.File(self.ACTUAL_SOURCE.format(year=year))
                try:
                    dataset_coords = _nsrdb['coordinates'][...]
                except Exception:
                    global _nsrdb_meta
                    if _nsrdb_meta is None:
                        metacache = Cache("metadata.csv.gz",package="weather",version=_version)
                        if metacache.exists():
                            _nsrdb_meta = pd.read_csv(metacache.pathname)
                        else:
                            _nsrdb_meta = pd.DataFrame(_nsrdb['meta'][...]).set_index("country").loc[b"United States"].set_index(["state","county"]).sort_index()
                            _nsrdb_meta.to_csv(metacache.pathname,index=True,header=True,compression="gzip")
                    dataset_coords = _nsrdb_meta[['latitude', 'longitude']].values

                tree = cKDTree(dataset_coords)
                def nearest(lat_coord, lon_coord):
                    lat_lon = np.array([lat_coord, lon_coord])
                    dist, pos = tree.query(lat_lon)
                    return pos

                latlon = Counties(use_index=["ST","COUNTY"]).loc[state,county][["LAT","LON"]].values.tolist()[0]
                latlon_idx = nearest(*latlon)

                data = pd.DataFrame(
                    data={
                        x:_nsrdb[x][:,latlon_idx] / _nsrdb[x].attrs['psm_scale_factor']
                        for x in ["air_temperature","relative_humidity","ghi","dni","dhi"]
                        },
                    index=pd.to_datetime(_nsrdb["time_index"][...].astype(str)),
                    ).resample("1h").mean().round(1)
                print(pd.DataFrame({
                    "mean":data.mean(),
                    "min":data.min(),
                    "max":data.max(),
                    "std":data.std(),
                    }).round(1))
                data.air_temperature = data.air_temperature * 1.8 + 32
                data.columns = [
                    "temperature_degF",
                    "humidity_pc",
                    "global_Wpms",
                    "direct_Wpms",
                    "diffuse_Wpms",
                    ]
                data.index.name = "timestamp"

            data.to_csv(cache.pathname,
                index=True,
                header=True,
                compression="gzip" if cache.name.endswith(".gz") else None,
                )

        else:

            # load from cache
            data = pd.read_csv(cache.pathname,
                index_col=["timestamp"],
                parse_dates=["timestamp"],
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
            values = Weather(state,county,refresh=True,year=2020)
            # print(pd.DataFrame({
            #     "Mean":values.mean().T,
            #     "Min":values.min().T,
            #     "Max":values.max().T,
            #     "Stdev":values.std().T,
            #     }))
        except Exception as err:
            raise

