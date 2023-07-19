""" @author Máté Kelemen"""

__all__ = [
    "CLI"
]

# --- Core Imports ---
import KratosMultiphysics

# --- STD Imports ---
import argparse
import typing


def _GetParameterType(parameters: KratosMultiphysics.Parameters) -> typing.Union[
        typing.Type[bool],
        typing.Type[int],
        typing.Type[float],
        typing.Type[str]]:
    if parameters.IsBool():
        return bool
    elif parameters.IsInt():
        return int
    elif parameters.IsDouble():
        return float
    elif parameters.IsString():
        return str
    elif parameters.IsArray() or parameters.IsStringArray():
        raise TypeError(f"CLI operations cannot have array parameters")
    elif parameters.IsMatrix():
        raise TypeError(f"CLI operations cannot have matrix parameters")
    elif parameters.IsSubParameter():
        raise TypeError(f"CLI operations cannot have nested parameters")
    else:
        raise RuntimeError(f"Unexpected parameter type: {parameters}")



def _GetParameter(parameters: KratosMultiphysics.Parameters) -> typing.Union[bool,int,float,str]:
    if parameters.IsBool():
        return parameters.GetBool()
    elif parameters.IsInt():
        return parameters.GetInt()
    elif parameters.IsDouble():
        return parameters.GetDouble()
    elif parameters.IsString():
        return parameters.GetString()
    else:
        raise RuntimeError(f"Invalid parameter: {parameters}")



def _AddParameter(parameters: KratosMultiphysics.Parameters,
                  name: str,
                  value: typing.Union[bool,int,float,str]) -> None:
    if isinstance(value, bool):
        parameters.AddBool(name, value)
    elif isinstance(value, int):
        parameters.AddInt(name, value)
    elif isinstance(value, float):
        parameters.AddDouble(name, value)
    elif isinstance(value, str):
        parameters.AddString(name, value)
    else:
        raise TypeError(f"Unexpected value: {value}")



class CLI:
    """"""

    parser_root, subparser = (lambda p: (p, p.add_subparsers(dest = "subcommand")))(argparse.ArgumentParser())


    operations: "dict[str,tuple[argparse.ArgumentParser,typing.Type[KratosMultiphysics.Operation]]]" = {}


    @classmethod
    def AddOperation(cls, operation_type: typing.Type[KratosMultiphysics.Operation]) -> None:
        """ @brief Add a @ref Kratos::Operation as a subcommand."""
        if not issubclass(operation_type, KratosMultiphysics.Operation):
            raise TypeError(f"Expecting a Kratos::Operation, but got {operation_type} instead")

        parser = cls.subparser.add_parser(operation_type.__name__,
                                          description = operation_type.__doc__)

        parameters: KratosMultiphysics.Parameters = operation_type.GetDefaultParameters()
        for key, value in parameters.items():
            parser.add_argument(f"--{key.replace('_','-')}",
                                dest = key,
                                type = _GetParameterType(value),
                                default = _GetParameter(value))

        cls.operations[operation_type.__name__] = (parser, operation_type)


    @classmethod
    def RunOperation(cls,
                     operation_name: str,
                     arguments: argparse.Namespace) -> None:
        parser, operation_type = cls.operations[operation_name]
        model = KratosMultiphysics.Model()
        parameters = KratosMultiphysics.Parameters()
        for name, value in arguments.__dict__.items():
            if name != "subcommand":
                _AddParameter(parameters, name, value)
        operation_type(model, parameters).Execute()


    @classmethod
    def Run(cls, argv: "typing.Optional[list[str]]" = None) -> None:
        arguments = cls.parser_root.parse_args(argv)
        cls.RunOperation(arguments.subcommand, arguments)
