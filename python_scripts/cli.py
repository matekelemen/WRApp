""" @author Máté Kelemen"""

__all__ = [
    "MakeCLI"
]

# --- STD Imports ---
import argparse
import typing
import pathlib
import os


def MakeCLI() -> argparse.ArgumentParser:
    root_parser = argparse.ArgumentParser(prog = "wrapp",
                                          description = "WRApplication aggregate command line interface.")
    subparser = root_parser.add_subparsers(dest = "subcommand")
    MakeLauncherCLI(subparser)
    return root_parser


def MakeLauncherCLI(subparser: typing.Optional[argparse.Action] = None) -> typing.Optional[argparse.ArgumentParser]:
    """ @brief Create a command line interface for launching analyses with WRApplication.
        @param subparser: If @a subparser is passed the newly created parser will be added
                          to it as a subcommand instead of creating a standalone one.
    """
    parser: argparse.ArgumentParser

    # Choose between a standalone parser or a subcommand
    if subparser is None:
        parser = argparse.ArgumentParser("launch", description = "Launch an analysis with WRApplication")
    else:
        parser = subparser.add_parser("launch",description = "Launch an analysis with WRApplication")

    # Define arguments
    parser.add_argument("-i",
                        "--input",
                        dest = "input_path",
                        type = pathlib.Path,
                        required = True,
                        help = "Path to the input JSON configuration.")
    parser.add_argument("--cd",
                        dest = "working_directory",
                        type = pathlib.Path,
                        default = pathlib.Path(os.getcwd()),
                        help = "Change the working directory to the provided path.")

    return parser

