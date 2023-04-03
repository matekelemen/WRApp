""" @author Máté Kelemen"""

__all__ = [
    "RegisterClass",
    "RecursivelyRegisterClass",
    "GetRegistryEntry",
    "GetRegisteredClass",
    "RegisteredClassFactory",
    "IsRegisteredPath"
]

# --- WRApp Imports ---
from .RuntimeRegistry import RuntimeRegistry

# --- STL Imports ---
import typing


def RegisterClass(cls: type, parent_path: str = ""):
    """ @brief Create a new item in the global registry for the provided class.
        @details The newly registered item is the following @a dict:
                 @code
                 {
                    "type" : cls
                 }
                 @endcode
    """
    prefix = parent_path + "." if parent_path else ""
    full_path = f"{prefix}{cls.__name__}"
    entry = {
        "type" : cls
    }
    if IsRegisteredPath(full_path):
        raise RuntimeError(f"Attempt to overwrite entry {GetRegistryEntry(full_path)} in RuntimeRegistry at path {full_path} with {entry}")
    else:
        RuntimeRegistry.AddItem(full_path, entry)


def RecursivelyRegisterClass(cls: type, parent_path: str) -> None:
    """ @brief Add the provided class and its derived classes recursively to the @ref RuntimeRegistry."""
    RegisterClass(cls, parent_path)
    new_parent_path = ("." if parent_path else "").join((parent_path, cls.__name__))
    for subclass in cls.__subclasses__():
        RecursivelyRegisterClass(subclass, new_parent_path)


def GetRegistryEntry(registered_path: str) -> "dict[str,typing.Any]":
    return RuntimeRegistry[registered_path]


def GetRegisteredClass(registered_path: str) -> typing.Any:
    return GetRegistryEntry(registered_path)["type"]


def RegisteredClassFactory(registered_path: str,
                           *args,
                           **kwargs) -> typing.Any:
    """ @brief Instantiate a class registered in @ref RuntimeRegistry."""
    return GetRegisteredClass(registered_path)(*args, **kwargs)


def IsRegisteredPath(path: str) -> bool:
    """ @brief Check whether the provided path exists in @ref RuntimeRegistry."""
    return RuntimeRegistry.HasItem(path)
