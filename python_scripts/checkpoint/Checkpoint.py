"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from KratosMultiphysics.WRApp.checkpoint.Snapshot import Snapshot


class Checkpoint:
    """@brief Class representing a checkpoint, consisting of one or more consecutive @ref Snapshot s."""

    def __init__(self, snapshots: list):
        """@brief Construct a Checkpoint from a list of @ref Snapshot.
           @param snapshots: list of @ref Snapshot s that make up the checkpoint. The number of snapshots must
                             match the buffer size of the model part the checkpoint will be loaded into."""
        self.__snapshots = sorted(snapshots)
        if not self.IsValid():
            raise ValueError(f"Invalid Snapshots:\n{'\n'.join(str(snapshot) for snapshot in self.__snapshots)}")

    def IsValid(self) -> bool:
        """@brief Check whether the snapshots are consecutive."""
        for left, right in zip(self.__snapshots[:-1], self.__snapshots[1:]):
            if left.step + 1 != right.step:
                return False
        return bool(self.__snapshots)

    def GetBufferSize(self) -> int:
        return len(self.__snapshots)

    def Load(self, model_part: KratosMultiphysics.ModelPart) -> None:
        """@brief Load data from the Snapshots to the provided @ref ModelPart.
           @details The model part's buffer size must match the number of stored snapshots.
        """
        if self.GetBufferSize() != model_part.GetBufferSize():
            raise RuntimeError(f"Buffer size mismatch! (model part: {model_part.GetBufferSize()}, checkpoint: {self.GetBufferSize()})")

        # No need to cycle the buffer on the first snapshot.
        self.__snapshots[0].Load(model_part)

        # Load the rest of the snapshots.
        for snapshot in self.__snapshots[1:]:
            model_part.CloneSolutionStep() # TODO: ModelPart::CreateSolutionStep would suffice but throws an exception for now
            snapshot.Load(model_part)
