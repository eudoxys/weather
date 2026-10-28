Testing
-------

From the repository root:

	python3 -m venv .venv
	. .venv/bin/activate
	python3 -m pip install --upgrade pip
	pip install -e . pytest
	pytest

or `make test`, which installs non-editable into `.venv` and runs the same
tests with `MPLBACKEND=Agg`.

All tests except `test_live.py` run offline in about 15 seconds. The
`offline` fixture in `conftest.py` is applied to every test and:

  - points `Weather.REFERENCE_SOURCE` at a temporary folder that tests fill
    with generated COMstock-style files (`reference_source` fixture);

  - replaces the NSRDB download and credentials with mocks (`nsrdb` fixture
    records the calls);

  - disables the cache archives and points the cache at a temporary folder,
    so tests never read or write the user's cache.

Because of this nothing is downloaded and no cache folder needs to be kept
between runs (CI restores none).

Credentials: `test_live.py` reads NSRDB credentials from
`~/.nsrdb/credentials.json` (see `weather register`) and is skipped when they
are not found. It is marked `network` and `live`; exclude it with
`pytest -m "not live"`.

Environment variables:

  - `MPLBACKEND=Agg`: avoid opening plot windows (set by `make test` and CI)

conftest.py
-----------

Fixtures and helpers shared by all tests: `offline` (autouse),
`reference_source`, `nsrdb`, the synthetic `reference_frame()`, and
`weather_cache()`.

test_reference.py
-----------------

RESstock/COMstock reference weather from generated source files: shape and
columns, UTC hourly index, rounding, Celsius to Fahrenheit, the county time
zone shift to UTC start-of-interval, wrapping of year-end hours to the start
of the year, and the error raised when the download fails. Fast, offline.

	pytest weather/_test/test_reference.py

test_nsrdb.py
-------------

NSRDB actual weather with the download mocked: the county latitude and
longitude passed to the request, shape and columns for leap and non-leap
years, the shift from mid-interval (HH:30) to start-of-interval timestamps,
Celsius to Fahrenheit, and the error raised when the download fails. Fast,
offline.

	pytest weather/_test/test_nsrdb.py

test_cache.py
-------------

The cache: files are written and re-read without the source, actual and
reference years are cached separately, unreadable files are rebuilt, missing
files are fetched from the archive before the source, and `refresh=True`
bypasses both the cache and the archive. Fast, offline.

	pytest weather/_test/test_cache.py

test_cli.py
-----------

The `weather` command: `info`, `print` to stdout and to `.csv`/`.csv.gz`,
`plot` to a file, error handling, `--debug`, syntax errors, and the exit
codes of the installed command. Fast, offline.

	pytest weather/_test/test_cli.py

test_live.py
------------

One real NSRDB download (Alameda County CA, 2020) with range checks on the
values. Networked, needs credentials, skipped otherwise.

	pytest weather/_test/test_live.py
