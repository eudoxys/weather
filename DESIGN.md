# eudoxys/weather — package design (draft 1)

Status: draft, 2026-10-28; reconstructed from the implementation (after #18),
not yet agreed with the maintainer. Where the code does not say why, the
rationale is a best guess and is marked *(inferred)*.

## Purpose

`weather` provides hourly weather for a US county as a `pandas.DataFrame`,
for use as input to load and bulk power system models (e.g. the Eudoxys
WECC model, https://github.com/eudoxys/wecc).

- **Reference weather:** the RESstock/COMstock AMY2018 county weather files
  (OEDI), used when no year is given.
- **Actual weather:** NSRDB PSM4 aggregated data for a given year, at the
  county latitude/longitude, downloaded through `pvlib`.

Variables: dry-bulb temperature, relative humidity, and global horizontal,
direct normal, and diffuse horizontal irradiance.

Excluded: wind, pressure, precipitation, and other source variables;
sub-hourly data; forecasts; spatial averaging within a county; weather for
locations other than counties. County identities, coordinates, and time
zones live in `eudoxys/fips`; caching and the data archive live in
`eudoxys/cache` and `eudoxys/wecc`.

Coverage: every county known to `fips` (3142). Reference weather is 2018
only. Actual weather is whatever years the NSRDB PSM4 aggregated product
serves; the cache maintenance script builds 2018 through last year.

## Decisions settled

Numbers are permanent: add `Nb` rows for related later decisions; edit a
reversed decision in place and note the date.

| # | Decision |
|---|---|
| 1 | `Weather` is a `pandas.DataFrame` subclass; constructing it returns the data. |
| 2 | One weather point per county: the county's COMstock file, or the NSRDB cell at the county `LAT`/`LON` from `fips`. |
| 3 | `year=None` selects reference weather (COMstock AMY2018); an integer `year` selects NSRDB actual weather for that year. |
| 4 | Five output columns with units in their names: `temperature_degF`, `humidity_pc`, `global_Wpms`, `direct_Wpms`, `diffuse_Wpms`. |
| 5 | Temperatures are converted to °F; all values are rounded to 0.1. |
| 6 | Index is tz-aware UTC, named `timestamp`, hourly, hour-beginning. A year is January 1 00:00 UTC to December 31 23:00 UTC regardless of local time zone (8760 or 8784 rows). |
| 7 | Reference timestamps (local standard time, hour-ending) are shifted to UTC hour-beginning using the **county** `TZOFFSET` from `fips` (revised 2026-10-27, #3; was the state time zone). |
| 7b | Reference hours that fall in 2019 after the shift are rotated to the start of 2018, so the reference year is exactly calendar 2018 UTC. |
| 8 | NSRDB timestamps (HH:30 UTC) are moved back 30 minutes to HH:00. *(Alignment with the reference convention is unverified: open question 1, #12.)* |
| 9 | Results are cached as gzipped CSV through `cache.Cache`, keyed by state, county, and year, under package `weather` and a cache `version`; bump `_version` when cached contents change. |
| 10 | Lookup order: local cache → cache archive (eudoxys/wecc) → source. `refresh=True` skips both cache and archive and rebuilds from the source. |
| 11 | An unreadable cache file is deleted and rebuilt rather than raising. |
| 12 | A failed source download raises `RuntimeError` with the original error chained (#15). |
| 13 | NSRDB credentials are read from `~/.nsrdb/credentials.json` as `{email: token}`; if missing, the sign-up form is opened. *(Environment variables proposed in #13.)* |
| 14 | The CLI (`weather`) offers `print`, `plot`, `viewer`, `register`, `help`, and `info`; option names equal constructor argument names. |
| 15 | An interactive marimo viewer (`weather viewer`) ships with the package. |

## Conventions inherited

From the `eudoxys-package` skill and sibling packages:

- `CACHEDIR = None` class attribute and `refresh:bool=False` argument (`eudoxys/cache`).
- County identified by `(ST, COUNTY)` names as in `eudoxys/fips`; FIPS, `LAT`, `LON`, `TZOFFSET` come from `fips.counties`.
- Units in column names; tz-aware UTC time series with a named index.
- `makeargs()` filters keyword arguments by constructor annotations so the CLI can forward its options.
- `__main__` block for cache maintenance, honoring `--refresh` and `--debug`.

## Module layout

```
weather/
  __init__.py       package docs; re-exports Weather, main, __version__
  weather.py        Weather(state, county, year=None, refresh=False);
                    nsrdb_credentials(), nsrdb_weather() (private helpers);
                    __main__: rebuild the cache for all or selected regions
  cli.py            main(*args, **kwargs) -> int: the `weather` command
  viewer.py         marimo app: state/county/year/month/variable plot and table
  _test/            pytest suite (offline; see _test/README.md)
  # planned
  (none)
```

### Constructor and columns

```python
Weather(state:str, county:str, year:int|None=None, refresh:bool=False)
```

returns a `Weather` frame (a `pandas.DataFrame`) with

| class | columns |
|---|---|
| `Weather` | `temperature_degF`, `humidity_pc`, `global_Wpms`, `direct_Wpms`, `diffuse_Wpms` |

Nothing is composed from parts: each object is one county and one year.

## Sources

| output | primary source | fallback | anchor/reconciliation |
|---|---|---|---|
| reference weather (`year=None`) | eudoxys/wecc cache archive (`W.csv.gz`) | OEDI COMstock AMY2018 file `G{SS}0{CCC}0_2018.csv` (`Weather.REFERENCE_SOURCE`) | none |
| actual weather (`year=Y`) | eudoxys/wecc cache archive (`W_{Y}.csv.gz`) | NSRDB PSM4 aggregated via `pvlib.iotools.get_nsrdb_psm4_aggregated` (`time_step=60`, `utc=True`) | none |

The archive is itself built by this package (`refresh=True` from
`eudoxys/wecc`), so it holds the same processed output as the source path.

## Method

1. **Cache.** Build the cache key `[ST, COUNTY, "W.csv.gz" | "W_{year}.csv.gz"]`. Unless `refresh`, fetch it from the archive if not local and read it; on a read error delete it and continue.
2. **Locate the county.** Look up FIPS, `LAT`/`LON`, and `TZOFFSET` in `fips`.
3. **Reference path.** Read the COMstock CSV (date/time, dry bulb °C, RH %, GHI, DNI, DHI); shift the index by `-(TZOFFSET + 1)` hours to UTC hour-beginning; rename columns; convert °C → °F; round to 0.1; rotate 2019 hours to 2018.
4. **NSRDB path.** Request the five variables for the county point and year; keep and rename them; convert °C → °F; round to 0.1; shift the index by −30 minutes.
5. **Save.** Sort the index, name it `timestamp`, and write the gzipped CSV to the cache.

No reconciliation: differences between reference and NSRDB weather, or
between NSRDB years, are neither forced nor reported.

## Outputs

### `Weather`

Key: `timestamp` (one row per hour of the calendar year, UTC).

| column | dtype | notes |
|---|---|---|
| `timestamp` (index) | datetime, tz UTC | hour-beginning |
| `temperature_degF` | float64 | outdoor dry-bulb temperature, °F |
| `humidity_pc` | float64 | relative humidity, % |
| `global_Wpms` | float64 | global horizontal irradiance, W/m² |
| `direct_Wpms` | float64 | direct normal irradiance, W/m² |
| `diffuse_Wpms` | float64 | diffuse horizontal irradiance, W/m² |

Example rows (real output, `Weather("CA","Alameda")`):

```
                           temperature_degF  humidity_pc  global_Wpms  direct_Wpms  diffuse_Wpms
timestamp
2018-01-01 00:00:00+00:00              54.0         23.4         40.5         63.0          32.0
2018-01-01 01:00:00+00:00              52.0         26.3          2.0         12.0           2.0
2018-01-01 02:00:00+00:00              51.1         28.6          0.0          0.0           0.0
```

## Files and formats

- Cache path: `<CACHEDIR>/weather/<_version>/<ST>/<COUNTY>/W.csv.gz` (reference) or `W_<year>.csv.gz` (actual); CSV with header, `timestamp` first, gzip.
- Size: about 80 KB per county-year (77 KB and 85 KB measured for Alameda reference and 2020). A full cache of 3142 counties × (reference + 2018–2025) is roughly 2–2.5 GB *(estimate, to confirm)*.
- No data is checked into this repository.

## Dependencies and gaps in sibling packages

| need | status |
|---|---|
| county FIPS, `LAT`/`LON`, `TZOFFSET`, `RO` | `fips.counties.Counties`, `County` ✔ |
| namespaced, versioned cache with archive download | `cache.Cache` ✔ |
| prebuilt weather archive | eudoxys/wecc `wecc/weather/` ✔ (coverage beyond WECC to confirm) |
| NSRDB PSM4 download | `pvlib.iotools.get_nsrdb_psm4_aggregated` ✔ (pvlib from git `main`; pin in #9) |

## Known issues to handle

- COMstock files are local standard time, hour-ending; the shift uses standard time all year (no DST).
- COMstock AMY2018 file names use a FIPS-derived G-code (`G{state}0{county}0`); counties whose FIPS changed after the COMstock release may have no file *(assumption)*.
- NSRDB PSM4 rows are stamped at HH:30; the meaning (interval midpoint vs. instantaneous) is unverified (#12).
- Missing credentials currently fail with `TypeError` (#4); `HOME` must be set at import (#6).
- Data validation uses `assert`, stripped by `python -O` (#5).
- Leap years: NSRDB returns 8784 hours; reference weather is always 2018 (8760).

## Open questions

1. **NSRDB alignment (#12).** Is −30 minutes correct, or should NSRDB be shifted −60 (hour-ending) or 0? Check peak-GHI hour against the reference on clear days for 2018. A change bumps `_version`.
2. **Credentials (#13).** Add `NSRDB_API_KEY`/`NSRDB_EMAIL` environment variables, and in what precedence with the file?
3. **Packaging (#9).** Distribution name, extras for `marimo`/`matplotlib`, and pinned `pvlib`, `fips`, `cache`.
4. **Viewer scope (#14).** All states and all available years, or keep WECC 2018–2022?
5. **Reference year.** Stay with AMY2018 only, or add TMY or other ResStock/ComStock weather years?
