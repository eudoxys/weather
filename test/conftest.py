"""Shared fixtures for the weather test suite

All network access is replaced by local fixture data:

  - the RESstock/COMstock reference weather (OEDI CSV) is generated into a
    temporary folder that `Weather.REFERENCE_SOURCE` points to;

  - the NSRDB download (`pvlib.iotools.get_nsrdb_psm4_aggregated`) and the
    NSRDB credentials are mocked;

  - the cache archives are disabled and the cache folder is a temporary
    folder.
"""

import os

import numpy as np
import pandas as pd
import pytest

import cache.cache
from cache import Cache
from fips.counties import County

import weather.weather as ww
from weather import Weather

REFERENCE_YEAR = 2018
"""Year of the COMstock AMY reference weather"""

HOURS = 8760
"""Number of hours in the reference weather year"""

SOURCE_COLUMNS = [
    "date_time",
    "Dry Bulb Temperature [°C]",
    "Relative Humidity [%]",
    "Wind Speed [m/s]",
    "Wind Direction [Deg]",
    "Global Horizontal Radiation [W/m2]",
    "Direct Normal Radiation [W/m2]",
    "Diffuse Horizontal Radiation [W/m2]",
    ]
"""Columns of an OEDI COMstock weather file"""

COLUMNS = [
    "temperature_degF",
    "humidity_pc",
    "global_Wpms",
    "direct_Wpms",
    "diffuse_Wpms",
    ]
"""Columns of a `Weather` data frame"""

def reference_frame():
    """Build a deterministic COMstock-style weather table

    The `Direct Normal Radiation [W/m2]` column holds the source row number,
    so tests can trace each output row back to its source row. The other
    values carry more than one decimal place so rounding can be checked.
    """
    hours = np.arange(HOURS)
    return pd.DataFrame({
        # timestamps are local standard time at the end of each interval
        "date_time": pd.date_range(f"{REFERENCE_YEAR}-01-01 01:00:00",
            periods=HOURS, freq="h").strftime("%Y-%m-%d %H:%M:%S"),
        "Dry Bulb Temperature [°C]": (10 + 15*np.sin(2*np.pi*hours/HOURS)).round(2),
        "Relative Humidity [%]": (50 + 30*np.cos(2*np.pi*hours/24)).round(3),
        "Wind Speed [m/s]": 3.0,
        "Wind Direction [Deg]": 180.0,
        "Global Horizontal Radiation [W/m2]": (hours % 24 * 12.345).round(3),
        "Direct Normal Radiation [W/m2]": hours.astype(float),
        "Diffuse Horizontal Radiation [W/m2]": (hours % 24 * 1.234).round(3),
        })[SOURCE_COLUMNS]

def reference_filename(state, county):
    """Name of the OEDI weather file for a county"""
    fips = County(ST=state, COUNTY=county).FIPS
    return f"G{fips[:2]}0{fips[2:]}0_{REFERENCE_YEAR}.csv"

def weather_cache(state, county, year=None):
    """Cache entry used by `Weather` for a county"""
    return Cache([state, county, "W.csv.gz" if year is None else f"W_{year}.csv.gz"],
        package="weather",
        version=ww._version)

@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    """Isolate every test from the network and from the user's cache

    Yields the folder that stands in for `Weather.REFERENCE_SOURCE`. It is
    empty, so any reference download fails unless a test adds a file with
    the `reference_source` fixture.
    """
    cachedir = tmp_path / "cache"
    cachedir.mkdir()
    source = tmp_path / "oedi"
    source.mkdir()
    monkeypatch.setattr(Cache, "CACHEDIR", str(cachedir))
    monkeypatch.setattr(Weather, "CACHEDIR", str(cachedir))
    monkeypatch.setattr(Weather, "REFERENCE_SOURCE", str(source))
    monkeypatch.setattr(cache.cache, "ARCHIVES", [])

    def no_nsrdb(*args, **kwargs):
        raise AssertionError("NSRDB access is not mocked in this test")
    monkeypatch.setattr(ww.pvlib.iotools, "get_nsrdb_psm4_aggregated", no_nsrdb)
    monkeypatch.setattr(ww, "nsrdb_credentials", lambda *a, **k: ("test@example.com", "TESTKEY"))
    monkeypatch.setenv("MPLBACKEND", "Agg")
    return source

@pytest.fixture
def reference_source(offline):
    """Add the reference weather file of a county to the mocked OEDI source

    Usage: `reference_source(state, county)` returns the source data frame
    written for that county.
    """
    def add(state, county, data=None):
        data = reference_frame() if data is None else data
        data.to_csv(os.path.join(offline, reference_filename(state, county)),
            index=False)
        return data
    return add

@pytest.fixture
def nsrdb(monkeypatch):
    """Mock the NSRDB PSM4 download

    Returns a list that records the keyword arguments of each call. The
    mocked data has hourly values timestamped at the middle of each hour
    (HH:30 UTC), with the source row number in the `dni` column.
    """
    calls = []

    def get_nsrdb_psm4_aggregated(latitude, longitude, api_key, email, **kwargs):
        calls.append(dict(latitude=latitude, longitude=longitude,
            api_key=api_key, email=email, **kwargs))
        year = kwargs["year"]
        index = pd.date_range(f"{year}-01-01 00:30:00", f"{year}-12-31 23:30:00",
            freq="h", tz="UTC")
        hours = np.arange(len(index))
        data = pd.DataFrame({
            "Year": index.year,
            "Month": index.month,
            "temp_air": (5 + 20*np.sin(2*np.pi*hours/len(index))).round(3),
            "relative_humidity": (60 + 25*np.cos(2*np.pi*hours/24)).round(3),
            "ghi": (hours % 24 * 10.55).round(2),
            "dni": hours.astype(float),
            "dhi": (hours % 24 * 2.25).round(2),
            "wind_speed": 2.0,
            }, index=index)
        return data, {"latitude": latitude, "longitude": longitude}

    monkeypatch.setattr(ww.pvlib.iotools, "get_nsrdb_psm4_aggregated",
        get_nsrdb_psm4_aggregated)
    return calls
