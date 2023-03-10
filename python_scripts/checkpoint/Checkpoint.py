"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApplication Imports ---
import KratosMultiphysics.WRApplication as WRApp
from .Snapshot import Snapshot


## @addtogroup WRApplication
## @{
## @addtogroup checkpointing
## @{


class Checkpoint(WRApp.WRAppClass):
    """ @brief Class representing a checkpoint, consisting of one or more consecutive @ref Snapshot s.
        @classname Checkpoint
    """

    def __init__(self, snapshots: "list[Snapshot]"):
        """ @brief Construct a Checkpoint from a list of @ref Snapshot s.
            @param snapshots: list of @ref Snapshot s that make up the checkpoint. The number of snapshots must
                              match the buffer size of the model part the checkpoint will be loaded into.
        """
        super().__init__()
        self.__snapshots = sorted(snapshots)
        if not self.IsValid():
            new_line = "\n"
            raise ValueError(f"Invalid Snapshots:\n{new_line.join(str(snapshot) for snapshot in self.__snapshots)}")


    def IsValid(self) -> bool:
        """@brief Check whether the snapshots are consecutive."""
        for left, right in zip(self.__snapshots[:-1], self.__snapshots[1:]):
            if left.step + 1 != right.step:
                return False
        return bool(self.__snapshots)


    def GetBufferSize(self) -> int:
        """@brief Get the minimum buffer size required to load this @ref Checkpoint."""
        return len(self.__snapshots)


    def Load(self, model_part: KratosMultiphysics.ModelPart) -> None:
        """ @brief Load data from the Snapshots to the provided @ref ModelPart.
            @note The model part's buffer size must match the number of stored snapshots.
        """
        if self.GetBufferSize() != model_part.GetBufferSize():
            raise RuntimeError(f"Buffer size mismatch! (model part: {model_part.GetBufferSize()}, checkpoint: {self.GetBufferSize()})")

        current_analysis_path = model_part.ProcessInfo[WRApp.ANALYSIS_PATH]

        if self.__snapshots:
            # No need to cycle the buffer on the first snapshot.
            self.__snapshots[0].Load(model_part)

            # Load the rest of the snapshots.
            for snapshot in self.__snapshots[1:]:
                model_part.CloneSolutionStep() # TODO: ModelPart::CreateSolutionStep would suffice but throws an exception for now
                snapshot.Load(model_part)

        # Increment ANALYSIS_PATH
        model_part.ProcessInfo[WRApp.ANALYSIS_PATH] = current_analysis_path + 1


## @}
## @}
