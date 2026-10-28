# Data

- [x] Reference weather from RESstock/COMstock 2018 (see `weather.weather.Weather`)

- [x] Actual weather from the NSRDB for a given year (see `weather.weather.Weather`)

- [x] Use the county time zone for reference weather (#3)

- [x] Download from the Eudoxys WECC archive before rebuilding from the source

- [ ] Verify NSRDB timestamp alignment against the reference weather (#12)

- [ ] Allow NSRDB credentials from environment variables (#13)

# Fixes

- [ ] Clear error when NSRDB credentials are missing (#4)

- [ ] Replace data-validation `assert`s with exceptions (#5; download errors fixed by #15)

- [ ] Import without `HOME` set (#6)

- [ ] CLI error output, exit codes, and argument handling (#7)

- [ ] Remove dead code in `weather/weather.py` (#10)

- [ ] Documentation errors in README and docstrings (#11)

# Tools

- [x] Test suite and CI (see `weather/_test/`)

- [ ] Viewer beyond WECC states and 2018–2022 (#14)

# Release

- [ ] Packaging for release: version, dependencies, extras (#9)
