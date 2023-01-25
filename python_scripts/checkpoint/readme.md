# Description

## Purpose
Checkpointing is meant to help with loading an earlier state of the analysis in order to retry/resume the computation with additional information "from the future".

# Definitions

## Analysis Path
An analysis path is an ordered set of continuous solution steps from which no checkpoints were loaded. Analysis paths begin at the start of the analysis' and end at dead-ends or at the analysis end. A new path is created after each time a ```Checkpoint``` is loaded, inheriting the solution steps preceding the loaded ```Checkpoint```, while the previous path's last step becomes a **dead-end**. Paths may share sections but always have a unique end step, and can only diverge at steps where a valid ```Checkpoint``` is available. The **solution path** is an analysis path ending at the analysis' end.
- An analysis has exactly one solution path but may have zero or more paths with dead-ends.
- The solution path is the only path that does not end in a dead-end.

## Snapshot
A ```Snapshot``` stores all data from a model part's nodes, elements, conditions and ```ProcessInfo``` at the state when it was created. The data can either be stored on disk in an HDF5 file (```SnapshotOnDisk```) or in memory (```SnapshotInMemory``` - not implemented yet). A ```Snapshot``` stores no data related to previous steps.

## Checkpoint
A ```Checkpoint``` consists of one or more consecutive ```Snapshot```s from the same solution path; the exact number depends on the buffer size of the ```ModelPart```. When a ```Checkpoint``` is loaded, its related ```Snapshot```s are read in order to fill the buffer of the target ```ModelPart```. **A ```Checkpoint``` is valid iff all required ```Snapshot```s exist**.

# Behaviour

## Loading Checkpoints
- A ```Checkpoint``` can only be loaded if all related ```Snapshot```s are available, the target ```ModelPart``` has all variables stored in the ```Snapshot```s, and its buffer size equals the number of ```Snapshot```s in the ```Checkpoint```.
- **Obsolete ```Checkpoint```s** and their related ```Snapshot```s on the dead-end of paths **are not deleted by default**.

## Writing Checkpoints
- Creating a ```Checkpoint``` at a specific step involves constructing ```Snapshot```s before that step in order to capture buffer data.
- ```Checkpoint```s at the first steps of the analysis may not have sufficient data for earlier ```Snapshot```s; these cases must be handled manually by providing ```Snapshot```s with data on initial conditions.

## Example
Example analysis steps with buffer size 3:
```
                                                                 step#   checkpoint  snapshot
  begin (path 0,1,2,3, step 0)                                     0
    |                                                              1
    V                                                              2                    x
    |                                                              3                    x
    A----->-----+----------->-----------+                          4          A         x
    |           |                       |                          5
  path 0      path 1,2                path 3                       6                    x
    |           |                       |                          7                    x
    V           B----->-----+           V                          8          B         x
    |           |           |           |                          9
  load A      path 1     path 2         |                          10
                |           |           |                          11
                V           V          end (path 3, step 12)       12
              load B        |                                      13
                            |                                      14
                          load A                                   15
```

In the example above, the following ```Checkpoint```-related operations are performed in order:
1) Begin analysis (path 0, step 0).
2) Write checkpoint A (path 0, step 2-4).
3) Dead-end => load checkpoint A (path 0, step 10 => path 1, step 4).
4) Write checkpoint B (path 1, step 6-8).
5) Dead-end => load checkpoint B (path 1, step 13 => path 2, step 8).
6) Dead-end => load checkpoint A (path 2, step 15 => path 3, step 4).
7) End analysis (path 3, step 12).

Even though the analysis terminates at step 12, the total number of computed steps is actually 34 (10 in path 0, 9 in path 1, 7 in path 2, and 8 in path 3) and the highest step index during the analysis was 15. Keep this in mind while reading the next section.

It is possible to load a ```Checkpoint``` from the dead-end of an abandoned path (the abandoned path is not changed, but a new one is created that shares its section preceding the loaded checkpoint), though no example is given of that here.

# Issues

## Internal State
A lot of ```Process```es, solvers, and even the ```AnalysisStage``` keeps track of step indices and time internally, independently of their associated ```ModelPart```s. This can lead to all kinds of bugs that need to be tracked down individually for each object. The best solution is to modify these objects such that they query their ```Model``` or ```ModelPart```s when they need information about the current time and step, instead of relying on internally managed state.

## Output
Output generators (ideally ```OutputProcess```es) need to be configured such that they are allowed to overwrite existing output files. This is essential because an analysis involving checkpoints may pass through completely identical steps multiple times, triggering the same output generator.

Furthermore, the checkpoint system has no information about generated outputs, so if output is generated at steps/times that exceed the final step/time at which the analysis terminates, those output files will not be overwritten nor deleted, even though they are not part of the solution path. For this reason, a cleanup process should be executed at the end of the analysis.