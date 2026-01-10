import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _(county_ui, data_ui, mo, month_ui, state_ui, year_ui):
    mo.hstack([state_ui,county_ui,year_ui,month_ui,data_ui],justify='start')
    return


@app.cell
def _(
    county_ui,
    data_ui,
    mo,
    month_ui,
    np,
    pd,
    plt,
    state_ui,
    weather,
    year_ui,
):
    _data = weather[data_ui.value]
    _year = year_ui.value if year_ui.value else 2018
    _month = month_ui.value
    plt.figure(figsize=(20, 10))
    plt.grid()
    if _month:
        dt_index = pd.date_range(
            start=f"{_year}-{_month:02d}-01 00:00:00+00:00",
            end=f"{_year+1 if _month==12 else _year}-{_month+1 if _month<12 else 1:02d}-01 00:00:00+00:00",
            freq="1h",
        )[:-1]
        plt.plot(_data.loc[np.s_[dt_index]])
    else:
        plt.plot(_data)
    plt.title(f"{county_ui.value} {state_ui.value}")
    plt.xlabel("Date/Time")
    plt.ylabel(data_ui.selected_key)
    mo.ui.tabs(
        {
            "Plot": plt.gca(),
            "Data": mo.ui.table(
                weather,
                selection=None,
                page_size=24,
                text_justify_columns={x:"right" for x in weather.columns}
            ),
        },
        lazy=True,
    )
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
        "Temperature (degF)": "temperature_degF",
        "Humidity (%)": "humidity_pc",
        "Global horizontal irradiance (W/m^2)": "global_Wpms",
        "Diffuse horizontal irradiance (W/m^2)": "diffuse_Wpms",
        "Direct normal irradiance (W/m^2)": "direct_Wpms",
    },value="Temperature (degF)")
    return (data_ui,)


@app.cell
def _(Weather, county_ui, mo, state_ui, year_ui):
    mo.stop(state_ui.value is None, mo.md("**<font color=blue>HINT**: select a state</font>"))
    mo.stop(county_ui.value is None, mo.md("**<font color=blue>HINT**: select a county</font>"))
    weather = Weather(state_ui.value,county_ui.value,year_ui.value)
    return (weather,)


@app.cell
def _():
    import marimo as mo
    import h5pyd as h5
    import pandas as pd
    import numpy as np
    import datetime as dt
    import matplotlib.pyplot as plt
    from fips import Counties
    from weather import Weather
    return Counties, Weather, dt, mo, np, pd, plt


if __name__ == "__main__":
    app.run()
