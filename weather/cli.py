"""Weather accessor CLI

"""

import os
import sys
import argparse
import warnings

import pandas as pd

from weather import Weather

E_OK = 0
"""Exit code on success"""

E_FAILED = 1
"""Exit code on failure"""

E_SYNTAX = 2
"""Exit code on syntax error"""

def main(*args:list[str],**kwargs:dict[str,str]) -> int:
    """Weather data command line processor

    # Argument

    - `*args`: command line arguments (`None` is `sys.argv`)

    # Returns

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

        parser.add_argument("-S","--state",
            required=True,
            type=str,
            help="state abbreviation of county")
        parser.add_argument("-C","--county",
            required=True,
            type=str,
            help="county name of weather data to collect")
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

        data = Weather(args.state,args.county,args.year)

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

    # pylint: disable=broad-exception-caught
    except Exception as err:

        if getattr(args,"debug"):
            raise

        print(f"ERROR [[{__package__}]: {err}")
        return E_FAILED

if __name__ == "__main__":
    main("--state","CA","--county","Alameda")
