"""Weather accessor CLI"""

import os
import sys
import argparse
import warnings
import webbrowser
import importlib.metadata as meta

import pandas as pd
import matplotlib.pyplot as plt

import weather

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

    - `*args`: command line arguments (`None` is `sys.argv`)

    Returns
    -------

    - `int`: return/exit code
    """
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
            help="variable to output")
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
        args = parser.parse_args()

        # setup warning handling
        if not args.warning:
            warnings.showwarning = lambda *x:print(
                f"WARNING [{__package__}]:",
                x[0],
                flush=True,
                file=sys.stderr,
                )

        if args.command in {"print","plot"}:
            assert not args.state is None, f"state is required"
            assert not args.county is None, f"county is required"
            data = weather.Weather(args.state,args.county,args.year)

        match args.command:
            
            case "print":
            
                if args.output is None:

                    pd.options.display.max_rows=None
                    pd.options.display.max_columns=None
                    pd.options.display.width=None

                    print(data)
                    return E_OK

                if args.output.endswith(".csv"):

                    data.to_csv(args.output,index=True,header=True)
                    return E_OK

                if args.output.endswith(".csv.gz"):

                    data.to_csv(args.output,index=True,header=True,compression="gzip")
                    return E_OK

                raise ValueError(f"output={args.output} is not valid")

            case "plot":

                plt.figure(figsize=(20,10))
                data[args.variable.split(",") if args.variable else data.columns].plot(
                    ax=plt.gca(),
                    grid=True,
                    legend=True,
                    xlabel="Date/Time",
                    ylabel="Value",
                    title=f"{args.county} {args.state}"
                    )

                if args.output is None:

                    try:
                        plt.show()
                    except KeyboardInterrupt:
                        return E_OK

                else:

                    plt.savefig(args.output)
                    return E_OK

            case "viewer":

                return os.system(f"marimo run {os.path.dirname(__file__)}/viewer.py")

            case "register":

                webbrowser.open(weather.SIGNUP)
                print("Please fill out the form in the new browser window to register with the NSRDB Developer Network")
                print(f"You should store your credentials in the file {weather.CREDENTIALS}")
                return E_OK

            case "help":
                webbrowser.open(_URLS["Documentation"])
                return E_OK

            case "info":
                print(*[f"{x}: {y}" for x,y in _URLS.items()],sep="\n")
                return E_OK

    # pylint: disable=broad-exception-caught
    except Exception as err:

        if getattr(args,"debug"):
            raise

        print(f"ERROR [[{__package__}]: {err}")
        return E_FAILED

if __name__ == "__main__":
    main("plot","--state","AZ","--county","Maricopa","-V","temperature_degF")
