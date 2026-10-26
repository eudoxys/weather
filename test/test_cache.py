"""Tests of the weather cache"""

import os
import pathlib

import pandas as pd
import pytest

import cache.cache
from weather import Weather

from conftest import reference_filename, weather_cache

def remove_source(offline, state, county):
    os.remove(os.path.join(offline, reference_filename(state, county)))

def test_cache_written(reference_source):
    reference_source("CA", "Alameda")
    data = Weather("CA", "Alameda")
    pathname = weather_cache("CA", "Alameda").pathname
    assert os.path.exists(pathname)
    cached = pd.read_csv(pathname, index_col=["timestamp"], parse_dates=["timestamp"])
    pd.testing.assert_frame_equal(pd.DataFrame(data), cached, check_freq=False)

def test_cache_read(reference_source, offline):
    """A second request is served from the cache without the source"""
    reference_source("CA", "Alameda")
    first = Weather("CA", "Alameda")
    remove_source(offline, "CA", "Alameda")
    second = Weather("CA", "Alameda")
    pd.testing.assert_frame_equal(first, second, check_freq=False)

def test_cache_year_separate(reference_source, nsrdb):
    reference_source("CA", "Alameda")
    Weather("CA", "Alameda")
    Weather("CA", "Alameda", year=2019)
    assert os.path.exists(weather_cache("CA", "Alameda").pathname)
    assert os.path.exists(weather_cache("CA", "Alameda", 2019).pathname)
    Weather("CA", "Alameda", year=2019)
    assert len(nsrdb) == 1, "second NSRDB request not served from cache"

@pytest.mark.parametrize("content", [b"not a gzip file", b""])
def test_corrupt_cache_recovery(reference_source, content):
    """A cache file that cannot be read is deleted and rebuilt"""
    reference_source("CA", "Alameda")
    expected = Weather("CA", "Alameda")
    pathname = weather_cache("CA", "Alameda").pathname
    with open(pathname, "wb") as fh:
        fh.write(content)
    data = Weather("CA", "Alameda")
    pd.testing.assert_frame_equal(expected, data, check_freq=False)
    rebuilt = pd.read_csv(pathname, index_col=["timestamp"], parse_dates=["timestamp"])
    assert rebuilt.shape == expected.shape

def test_refresh(reference_source):
    """`refresh=True` bypasses the cache and rebuilds it from the source"""
    reference_source("CA", "Alameda")
    expected = Weather("CA", "Alameda")
    pathname = weather_cache("CA", "Alameda").pathname
    stale = pd.DataFrame(expected).copy()
    stale["temperature_degF"] = -999.0
    stale.to_csv(pathname, compression="gzip")
    assert (Weather("CA", "Alameda")["temperature_degF"] == -999.0).all()
    data = Weather("CA", "Alameda", refresh=True)
    pd.testing.assert_frame_equal(expected, data, check_freq=False)
    assert (Weather("CA", "Alameda")["temperature_degF"] != -999.0).any()

def test_archive_download(reference_source, offline, tmp_path, monkeypatch):
    """A file missing from the local cache is downloaded from the archive
    before the source is used"""
    reference_source("CA", "Alameda")
    expected = Weather("CA", "Alameda")
    entry = weather_cache("CA", "Alameda")

    # move the cached file into a local archive and remove the source
    archive = tmp_path / "archive" / "weather" / "CA" / "Alameda"
    archive.mkdir(parents=True)
    os.replace(entry.pathname, archive / entry.name)
    remove_source(offline, "CA", "Alameda")
    monkeypatch.setattr(cache.cache, "ARCHIVES",
        [pathlib.Path(tmp_path / "archive").as_uri() + "/{package}/{path}"])

    data = Weather("CA", "Alameda")
    pd.testing.assert_frame_equal(expected, data, check_freq=False)
    assert os.path.exists(entry.pathname)

def test_refresh_skips_archive(reference_source, offline, tmp_path, monkeypatch):
    """`refresh=True` bypasses the archive too"""
    reference_source("CA", "Alameda")
    entry = weather_cache("CA", "Alameda")
    archive = tmp_path / "archive" / "weather" / "CA" / "Alameda"
    archive.mkdir(parents=True)
    (archive / entry.name).write_bytes(b"archived copy that must not be read")
    monkeypatch.setattr(cache.cache, "ARCHIVES",
        [pathlib.Path(tmp_path / "archive").as_uri() + "/{package}/{path}"])
    data = Weather("CA", "Alameda", refresh=True)
    assert data.shape == (8760, 5)
