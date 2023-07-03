""" @author Máté Kelemen"""

__all__ = [
    "SolutionStageScope",
    "AggregateSolutionStageScope"
]

# --- STL Imports ---
import abc
import typing
import types


## @addtogroup WRApplication
## @{
## @addtogroup AsyncAnalysis
## @{


class SolutionStageScope(abc.ABC):
    """ @brief RAII context manager for tasks during solver execution.
        @classname SolutionStageScope
        @details Example usage would be sandwiching @a AnalysisStage.SolveSolutionStep
                 between @a AnalysisStage.InitializeSolutionStep
                 and @a AnalysisStage.FinalizeSolutionStep.
    """


    @abc.abstractmethod
    def _Preprocess(self) -> None:
        """ @brief Invoke this function when the scope is created.
            @details Executes on @a __enter__.
        """
        pass


    @abc.abstractmethod
    def __call__(self) -> None:
        """ @brief Perform operations that are supposed to be RAII'd."""
        pass


    @abc.abstractmethod
    def _Postprocess(self) -> None:
        """ @brief Invoke this function when the scope is destroyed.
            @details Executes on @a __exit__.
        """
        pass


    def __enter__(self) -> "SolutionStageScope":
        self._Preprocess()
        return self


    def __exit__(self,
                 exception_type: typing.Optional[typing.Type[Exception]],
                 exception_instance: typing.Optional[Exception],
                 traceback: typing.Optional[types.TracebackType]) -> None:
        if any(argument is not None for argument in (exception_type, exception_instance, traceback)):
            raise exception_instance
        else:
            self._Postprocess()



class AggregateSolutionStageScope(SolutionStageScope):
    """ @brief Enter multiple @ref SolutionStageScope contexts at once.
        @classname AggregateSolutionStageScope
    """

    def __init__(self, scopes: "list[SolutionStageScope]"):
        self.__scopes = scopes


    def _Preprocess(self) -> None:
        for scope in self.__scopes:
            scope._Preprocess()


    def __call__(self) -> None:
        for scope in self.__scopes:
            scope()


    def _Postprocess(self) -> None:
        for scope in self.__scopes:
            scope._Postprocess()


## @}
## @}
