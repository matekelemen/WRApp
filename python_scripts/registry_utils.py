""" @author Máté Kelemen"""

__all__ = [
    "RegisterClass",
    "RecursivelyRegisterClass",
    "GetRegistryEntry",
    "GetRegisteredClass",
    "RegisteredClassFactory",
    "IsRegisteredPath",
    "ImportAndRegister"
]

# --- WRApp Imports ---
from .RuntimeRegistry import RuntimeRegistry

# --- STL Imports ---
import typing
import importlib


def RegisterClass(cls: type,
                  parent_path: str = "",
                  class_name: typing.Optional[str] = None):
    """ @brief Create a new item in the global registry for the provided class.
        @details The newly registered item is the following @a dict:
                 @code
                 {
                    "type" : cls
                 }
                 @endcode
    """
    prefix = parent_path + "." if parent_path else ""
    full_path = f"{prefix}{cls.__name__ if class_name is None else class_name}"
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


def ImportAndRegister(import_path: str,
                      registry_path: str) -> None:
    """ @brief Import a class from a module and add it to @ref RuntimeRegistry.
        @param import_path: full module path of the class to be imported.
        @param registry_path: path in the registry to add the imported class.
        @details At least one level of module resolution is expected, meaning
                 that @a import_path must contain at least one '.'.
    """
    import_parts = import_path.split(".")
    if len(import_parts) < 2:
        raise ValueError(f"At least one level of module resolution is expected in '{import_path}'")
    module = importlib.import_module(".".join(import_parts[:-1]))

    if not hasattr(module, import_parts[-1]):
        raise ImportError(f"Module {'.'.join(import_parts[:-1])} has no attribute '{import_parts[-1]}'")

    cls = getattr(module, import_parts[-1])
    registry_parts = registry_path.split(".")
    RegisterClass(cls,
                  ".".join(registry_parts[:-1]) if 1 < len(registry_parts) else "",
                  registry_parts[-1])
