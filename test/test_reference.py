"""Tests of the RESstock/COMstock reference weather"""

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from weather import Weather

from conftest import COLUMNS, HOURS, REFERENCE_YEAR

COUNTIES = [("CA", "Alameda"), ("AZ", "Maricopa"), ("WA", "King")]

@pytest.mark.parametrize("state,county", COUNTIES)
def test_shape_and_columns(reference_source, state, county):
    reference_source(state, county)
    data = Weather(state, county)
    assert isinstance(data, pd.DataFrame)
    assert data.shape == (HOURS, 5)
    assert list(data.columns) == COLUMNS

@pytest.mark.parametrize("state,county", COUNTIES)
def test_utc_hourly_index(reference_source, state, county):
    reference_source(state, county)
    index = Weather(state, county).index
    assert index.name == "timestamp"
    assert isinstance(index, pd.DatetimeIndex)
    assert index.tz is not None and index.tz.utcoffset(None) == dt.timedelta(0)
    assert index.is_unique and index.is_monotonic_increasing
    assert index[0] == pd.Timestamp(f"{REFERENCE_YEAR}-01-01 00:00:00", tz="UTC")
    assert index[-1] == pd.Timestamp(f"{REFERENCE_YEAR}-12-31 23:00:00", tz="UTC")
    assert (index[1:] - index[:-1] == pd.Timedelta(hours=1)).all()

def test_values_rounded(reference_source):
    reference_source("CA", "Alameda")
    data = Weather("CA", "Alameda")
    assert not data.isna().any().any()
    pd.testing.assert_frame_equal(data, data.round(1))

def test_celsius_to_fahrenheit(reference_source):
    source = reference_source("CA", "Alameda")
    data = Weather("CA", "Alameda").set_index("direct_Wpms").sort_index()
    expected = (source["Dry Bulb Temperature [°C]"] * 9/5 + 32).round(1)
    np.testing.assert_allclose(data["temperature_degF"].values, expected.values)
    np.testing.assert_allclose(data["humidity_pc"].values,
        source["Relative Humidity [%]"].round(1).values)

@pytest.mark.parametrize("state,county,tzoffset", [
    ("CA", "Alameda", -8),
    ("AZ", "Maricopa", -7),
    ("ID", "Ada", -7), # Idaho south (Mountain time)
    pytest.param("ID", "Kootenai", -8, # Idaho panhandle (Pacific time)
        marks=pytest.mark.xfail(strict=True,
            reason="#3: reference weather uses the state time zone")),
    pytest.param("OR", "Malheur", -7, # Oregon east (Mountain time)
        marks=pytest.mark.xfail(strict=True,
            reason="#3: reference weather uses the state time zone")),
    ])
def test_county_time_zone(reference_source, state, county, tzoffset):
    """Source rows are local standard time at the end of the interval; output
    rows are UTC at the start of the interval"""
    reference_source(state, county)
    data = Weather(state, county)
    start = pd.Timestamp(f"{REFERENCE_YEAR}-01-01 00:00:00", tz="UTC")
    for row in [0, 1000, 4000, HOURS - 24]:
        # source row `row` covers local hours [row, row+1) from Jan 1 00:00
        utc = start + pd.Timedelta(hours=row - tzoffset)
        if utc.year > REFERENCE_YEAR:  # year-end hours wrap to the start
            utc = utc.replace(year=REFERENCE_YEAR)
        assert data.loc[utc, "direct_Wpms"] == row, f"{state} {county} {utc}"

def test_year_end_wraps_to_start(reference_source):
    """The last local hours of the year fall in the next UTC year and are
    rotated to the start of the reference year"""
    reference_source("CA", "Alameda")
    data = Weather("CA", "Alameda")
    # local 2018-12-31 16:00 PST is 2019-01-01 00:00 UTC
    assert data.iloc[0]["direct_Wpms"] == HOURS - 8
    assert data.iloc[7]["direct_Wpms"] == HOURS - 1
    assert data.iloc[8]["direct_Wpms"] == 0

def test_download_failure(offline):
    with pytest.raises(RuntimeError, match="reference weather download") as err:
        Weather("CA", "Alameda")
    assert err.value.__cause__ is not None
