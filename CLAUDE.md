# CLAUDE.md

Guidance for Claude when working in the `eudoxys/weather` repository.
General Eudoxys package conventions are in the `eudoxys-package` skill
(https://github.com/eudoxys/claude); this file records only what is specific
to this package.

## What this is

`weather` returns hourly county weather for the US as a `pandas.DataFrame`
subclass, `weather.Weather(state, county, year=None, refresh=False)`. With no
`year` it reads the RESstock/COMstock 2018 reference weather (OEDI); with a
`year` it downloads NSRDB PSM4 data through `pvlib` (needs NSRDB credentials).
Python >= 3.11, alpha (`version = "0.0.0"`, unreleased).

- Docs site: https://www.eudoxys.com/weather (pdoc from docstrings)
- Maintainer: David P. Chassin (`dchassin`)
- CLI entry point: `weather` -> `weather.cli:main`

## Where things are

- `MANIFEST.md`: map of every file, a task index, and what not to read.
  Read it first instead of listing folders.
- `DESIGN.md`: design reconstructed from the implementation (draft, not yet
  agreed), numbered decisions, and open questions. Follow its decisions; ask
  before departing from one, and update it in the same PR when one changes.

Sibling Eudoxys dependencies:

- `fips` (`fips.counties.Counties`, `County`): county FIPS codes, LAT/LON,
  and `TZOFFSET` (county standard time offset).
- `cache` (`cache.Cache`): cache paths namespaced by package and version,
  and download from the Eudoxys WECC data archive (https://github.com/eudoxys/wecc).

## Core conventions

- Output columns, in order: `temperature_degF`, `humidity_pc`,
  `global_Wpms`, `direct_Wpms`, `diffuse_Wpms` (units in the names), values
  rounded to 0.1.
- Index: tz-aware UTC, named `timestamp`, hourly, **hour-beginning**. The
  reference source is local standard time hour-ending and is shifted by the
  county `TZOFFSET` + 1 h; hours that land in 2019 are rotated back to the
  start of 2018. NSRDB rows (HH:30) are moved back 30 minutes.
- Cache: `Cache([ST, COUNTY, "W.csv.gz" | "W_{year}.csv.gz"], package="weather",
  version=_version)`. Bump `_version` in `weather/weather.py` when the cached
  format or its contents change (it is 1 since the county time zone fix, #3).
  Unreadable cache files are deleted and rebuilt.
- Download failures and invalid downloaded data raise `RuntimeError` with
  the cause chained; don't use `assert` for data validation (`python -O`
  strips it).
- `Weather.makeargs()` filters keyword arguments by the constructor's
  annotations; keep CLI option names equal to argument names.

## Style

House style: no spaces after commas in calls, 4-space indent, dashed
docstring section headings. Match it; don't reformat code you aren't changing.

## Build, test, docs

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install --upgrade pip && pip install -e . pytest
pytest            # offline, ~15 s
make docs         # pdoc into docs/ (gitignored; CI deploys it)
```

Tests are fully offline (network and cache are mocked in
`weather/_test/conftest.py`); `test_live.py` hits the NSRDB only when
`~/.nsrdb/credentials.json` exists. CI (`validate.yaml`) runs pylint
(informational) and pytest on Python 3.11–3.13; `deploy-pages.yaml` builds
and publishes the docs.

## Known rough edges (don't "fix" silently; mention or ask)

Each has an approved issue; fix them in a PR that references it.

- Packaging: `marimo` and `matplotlib` are required even though only the
  `viewer` and `plot` commands use them; version is still `0.0.0` (#9).
- NSRDB timestamp alignment not verified against the reference weather (#12).
- The viewer is limited to WECC states and 2018–2022 (#14).

## Working rules

- Never commit caches, downloaded weather, `docs/`, or marimo session files.
- When a public signature, column, or output changes, update the module
  docstring example, the package docstring, and `README.md` in the same PR.
- Update `MANIFEST.md` when adding, moving, or deleting files, and run
  `python .github/check_manifest.py`.
- Conventional small case: Alameda County CA (`Weather("CA","Alameda")`, and
  `year=2020` for NSRDB). Don't run `python3 -m weather.weather` (every
  county, every year since 2018) unprompted.
