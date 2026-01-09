import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _(county_ui, data_ui, mo, month_ui, state_ui, year_ui):
    mo.hstack([state_ui,county_ui,year_ui,month_ui,data_ui],justify='start')
    return


@app.cell
def _(county_ui, data_ui, month_ui, np, pd, plt, state_ui, weather, year_ui):
    plt.figure(figsize=(20,10))
    plt.grid()
    if month_ui.value:
        dt_index = pd.date_range(
            start=f"{year_ui.value}-{month_ui.value:02d}-01 00:00:00+00:00",
            end=f"{year_ui.value+1 if month_ui.value==12 else year_ui.value}-{month_ui.value+1 if month_ui.value<12 else 1:02d}-01 00:00:00+00:00",
            freq="30min",
        )[:-1]
        plt.plot(weather.loc[np.s_[dt_index]])
    else:
        plt.plot(weather)
    plt.title(f"{county_ui.value} {state_ui.value}")
    plt.xlabel("Date/Time")
    plt.ylabel(data_ui.selected_key)
    plt.gca()
    return


@app.cell
def _(Counties, mo):
    state_ui = mo.ui.dropdown(label="State:",options=Counties(use_index="RO").loc["WECC"].ST.sort_values())
    return (state_ui,)


@app.cell
def _(Counties, mo, state_ui):
    county_ui = mo.ui.dropdown(
        label="County:",
        options=Counties(use_index="ST").loc[state_ui.value].COUNTY.sort_values() if state_ui.value else [],
    )
    return (county_ui,)


@app.cell
def _(mo):
    year_ui = mo.ui.dropdown(label="Year:",options=[x for x in range(2018,2023)])
    return (year_ui,)


@app.cell
def _(dt, mo):
    month_ui = mo.ui.dropdown(label="Month:",options={dt.date(2018,x+1,1).strftime("%B"):(x+1) for x in range(12)})
    return (month_ui,)


@app.cell
def _(mo):
    data_ui = mo.ui.dropdown(label="Data:",options={
        "Temperature (degF)": "/air_temperature",
        "Global horizontal irradiance (W/m^2)": "/ghi",
        "Diffuse horizontal irradiance (W/m^2)": "/dhi",
        "Direct normal irradiance (W/m^2)": "/dni",
    },value="Temperature (degF)")
    return (data_ui,)


@app.cell
def _(county_ui, mo, state_ui, year_ui):
    mo.stop(state_ui.value is None, mo.md("**<font color=blue>HINT**: select a state</font>"))
    mo.stop(county_ui.value is None, mo.md("**<font color=blue>HINT**: select a county</font>"))
    mo.stop(year_ui.value is None, mo.md("**<font color=blue>HINT**: select a year</font>"))
    return


@app.cell
def _(h5, year_ui):
    data = h5.File(f"/nrel/nsrdb/GOES/aggregated/v4.0.0/nsrdb_{year_ui.value}.h5")
    return (data,)


@app.cell
def _(data, mo, pd):
    try:
        dataset_coords = data["coordinates"][...]
    except Exception:
        # fall back to meta which includes 'latitude' and 'longitude' columns
        with mo.status.spinner(title="Loading NSRDB metadata...") as _spinner:
            meta = (
                pd.DataFrame(data["meta"][...])
                .set_index("country")
                .loc[b"United States"]
                .set_index(["state", "county"])
                .sort_index()
            )
            dataset_coords = meta[["latitude", "longitude"]].values
    return (dataset_coords,)


@app.cell
def _(cKDTree, dataset_coords, np):
    tree = cKDTree(dataset_coords)
    def nearest(lat_coord, lon_coord):
        lat_lon = np.array([lat_coord, lon_coord])
        dist, pos = tree.query(lat_lon)
        return pos
    return (nearest,)


@app.cell
def _(Counties, county_ui, nearest, state_ui):
    latlon = Counties(use_index=["ST","COUNTY"]).loc[state_ui.value,county_ui.value][["LAT","LON"]].values.tolist()[0]
    latlon_idx = nearest(*latlon)
    return (latlon_idx,)


@app.cell
def _(data, data_ui, latlon_idx, pd):
    values = data[data_ui.value]
    value_scale = values.attrs["psm_scale_factor"]
    print(f"{data_ui.value} scale is {value_scale}")
    time_index = pd.to_datetime(data["time_index"][...].astype(str))
    weather = pd.DataFrame(
        data=(values[:,latlon_idx] / value_scale * 1.8) + 32,
        index=time_index,
    )
    # weather
    return (weather,)


@app.cell
def _():
    import marimo as mo
    import h5pyd as h5
    import pandas as pd
    import numpy as np
    import datetime as dt
    import matplotlib.pyplot as plt
    from scipy.spatial import cKDTree
    from fips.counties import Counties
    return Counties, cKDTree, dt, h5, mo, np, pd, plt


if __name__ == "__main__":
    app.run()
