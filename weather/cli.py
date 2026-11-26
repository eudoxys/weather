"""Weather accessor CLI"""

import os
import sys
import argparse
import subprocess
import warnings
import webbrowser
import importlib.metadata as meta

import pandas as pd
import matplotlib.pyplot as plt

import weather
from weather.weather import SIGNUP, credentials_path

E_OK = 0
"""Exit code on success"""

E_FAILED = 1
"""Exit code on failure"""

E_SYNTAX = 2
"""Exit code on syntax error"""

_URLS = dict(x.split(", ") for x in meta.metadata(__package__).get_all("Project-URL"))

def main(*args:list[str],**kwargs:dict[str,str]) -> int:
    """Weather data command line processor

    Argument
    --------

    - `*args`: command line arguments (none means use `sys.argv`)

    - `**kwargs`: command line options given as `name=value`

    Returns
    -------

    - `int`: return/exit code
    """
    options = None
    try:

        # support direct call to main
        if args:
            sys.argv = [__file__] + list(args)
        if kwargs:
            sys.argv += [f"--{x}={y}" for x,y in kwargs.items()]

        # setup command line parser
        parser = argparse.ArgumentParser(
            prog="weather",
            description="Weather data CLI",
            epilog="See https://www.eudoxys.com/weather for documentation. ",
            )

        parser.add_argument("command",
            choices={"print","plot","viewer","register","help","info"},
            help="Weather command")

        parser.add_argument("-S","--state",
            type=str,
            help="state abbreviation of county")
        parser.add_argument("-C","--county",
            type=str,
            help="county name of weather data to collect")
        parser.add_argument("-V","--variable",
            type=str,
            help="comma-separated variable(s) to print or plot (default all)")
        parser.add_argument("-Y","--year",
            type=int,
            default=None,
            help="year of weather data to collect")
        parser.add_argument("-o","--output",
            help="output file name")
        parser.add_argument("-w","--warning",
            action="store_true",
            help="enable warning messages from python")
        parser.add_argument("-d","--debug",
            action="store_true",
            help="enable debug traceback on exceptions")

        # parse arguments
        options = parser.parse_args()

        # setup warning handling
        if not options.warning:
            warnings.showwarning = lambda *x:print(
                f"WARNING [{__package__}]:",
                x[0],
                flush=True,
                file=sys.stderr,
                )

        if options.command in {"print","plot"}:
            if options.state is None:
                raise ValueError("state is required")
            if options.county is None:
                raise ValueError("county is required")
            data = weather.Weather(options.state,options.county,options.year)
            if options.variable:
                variables = options.variable.split(",")
                unknown = [x for x in variables if x not in data.columns]
                if unknown:
                    raise ValueError(f"variable(s) {unknown} not found "
                        f"(valid variables are {list(data.columns)})")
                data = data[variables]

        match options.command:
            
            case "print":
            
                if options.output is None:

                    pd.options.display.max_rows=None
                    pd.options.display.max_columns=None
                    pd.options.display.width=None

                    print(data)
                    return E_OK

                if options.output.endswith(".csv"):

                    data.to_csv(options.output,index=True,header=True)
                    return E_OK

                if options.output.endswith(".csv.gz"):

                    data.to_csv(options.output,index=True,header=True,compression="gzip")
                    return E_OK

                raise ValueError(f"output={options.output} is not valid")

            case "plot":

                plt.figure(figsize=(20,10))
                data.plot(
                    ax=plt.gca(),
                    grid=True,
                    legend=True,
                    xlabel="Date/Time",
                    ylabel="Value",
                    title=f"{options.county} {options.state}"
                    )

                if options.output is None:

                    try:
                        plt.show()
                    except KeyboardInterrupt:
                        pass

                else:

                    plt.savefig(options.output)

                return E_OK

            case "viewer":

                return subprocess.run([sys.executable,"-m","marimo","run",
                    os.path.join(os.path.dirname(__file__),"viewer.py")],
                    check=False).returncode

            case "register":

                if webbrowser.open(SIGNUP):
                    print("Please fill out the form in the new browser window to register with the NSRDB Developer Network")
                else:
                    print(f"Please fill out the form at {SIGNUP} to register with the NSRDB Developer Network")
                print(f"You should store your credentials in the file {credentials_path()}")
                print('as {"YOUR.EMAIL@EXAMPLE.COM": "YOUR_TOKEN"}')
                return E_OK

            case "help":
                webbrowser.open(_URLS["Documentation"])
                return E_OK

            case "info":
                print(*[f"{x}: {y}" for x,y in _URLS.items()],sep="\n")
                return E_OK

    # pylint: disable=broad-exception-caught
    except Exception as err:

        if getattr(options,"debug",False):
            raise

        print(f"ERROR [{__package__}]: {err}",file=sys.stderr)
        return E_FAILED

if __name__ == "__main__":
    sys.exit(main())
