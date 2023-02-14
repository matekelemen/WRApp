<a name="table-of-contents"></a>

# Table of Contents
- [Setup](#setup)
- [Checkpointing](#checkpointing)
  - [Purpose](#checkpointing.purpose)
  - [Definitions](#checkpointing.definitions)
    - [Analysis Path](#checkpointing.definitions.analysis-path)
    - [Snapshot](#checkpointing.definitions.snapshot)
    - [Checkpoint](#checkpointing.definitions.checkpoint)
  - [Behaviour](#checkpointing.behaviour)
    - [Loading Checkpoints](#checkpointing.behaviour.loading-checkpoints)
    - [Writing Checkpoints](#checkpointing.behaviour.writing-checkpoints)
    - [Example](#checkpointing.behaviour.example)
  - [Issues](#checkpointing.issues)
    - [Internal State](#checkpointing.issues.internal-state)
    - [Output](#checkpointing.issues.output)
- [Registry](#registry)
  - [C++](#registry.cpp)
  - [Python](#registry.python)
- [Testing](#testing)
  - [C++](#testing.cpp)
  - [Python](#testing.python)

<a name="setup"></a>

# Setup

Being an *"application"* of [KratosMultiphysics](https://github.com/KratosMultiphysics/Kratos), this project is meant to be compiled along kratos as an external app. Clone this repo and invoke `add_app` with its path in the kratos configure script. Note this application requires a few extra PRs that have been in limbo in the KratosMultiphysics repository. Use the ['wrapp' branch](https://github.com/kratosmultiphysics/kratos/tree/wrapp) instead.
```
# configure.sh
...
add_app("path_to_the_cloned_repo")
...
```

See the full documentation [here](https://matekelemen.github.io/WRApp/docs/html/index.html).

<a name="checkpointing"></a>

#  Checkpointing

<a name="checkpointing.purpose"></a>

##  Purpose
Checkpointing is meant to help with loading earlier states of the analysis in order to retry/resume the computation with additional information "from the future".

<a name="checkpointing.definitions"></a>

##  Definitions

<a name="checkpointing.definitions.analysis-path"></a>

###  Analysis Path
An analysis path is an ordered set of continuous solution steps from which no checkpoints were loaded. Analysis paths begin at the start of the analysis' and end at dead-ends or at the analysis end. A new path is created after each time a ```Checkpoint``` is loaded, inheriting the solution steps preceding the loaded ```Checkpoint```, while the previous path's last step becomes a **dead-end**. Paths may share sections but always have a unique end step, and can only diverge at steps where a valid ```Checkpoint``` is available. The **solution path** is an analysis path ending at the analysis' end.
- An analysis has exactly one solution path but may have zero or more paths with dead-ends.
- The solution path is the only path that does not end in a dead-end.

<a name="checkpointing.definitions.snapshot"></a>

###  Snapshot
A ```Snapshot``` stores all data of a model part's nodes, elements, conditions and ```ProcessInfo``` at the state when it was created. The data can either be stored on disk in an HDF5 file (```SnapshotOnDisk```) or in memory (```SnapshotInMemory``` - not implemented yet). A ```Snapshot``` stores no data related to previous steps. This allows changing time integration schemes on the fly, provided that enough snapshots are available to fill the buffer.

<a name="checkpointing.definitions.checkpoint"></a>

###   Checkpoint
A ```Checkpoint``` consists of one or more consecutive ```Snapshot```s from the same solution path; the exact number depends on the buffer size of the ```ModelPart```. When a ```Checkpoint``` is loaded, its related ```Snapshot```s are read in order to fill the buffer of the target ```ModelPart```. **A ```Checkpoint``` is valid iff all required ```Snapshot```s exist**.

<a name="checkpointing.behaviour"></a>

##   Behaviour

<a name="checkpointing.behaviour.loading-checkpoints"></a>

###   Loading Checkpoints
- A ```Checkpoint``` can only be loaded if all related ```Snapshot```s are available, the target ```ModelPart``` has all variables stored in the ```Snapshot```s, and its buffer size equals the number of ```Snapshot```s in the ```Checkpoint```.
- **Obsolete ```Checkpoint```s** and their related ```Snapshot```s on the dead-end of paths **are not deleted by default**.

<a name="checkpointing.behaviour.writing-checkpoints"></a>

###   Writing Checkpoints
- Creating a ```Checkpoint``` at a specific step involves constructing ```Snapshot```s before that step in order to capture buffer data.
- ```Checkpoint```s at the first steps of the analysis may not have sufficient data for earlier ```Snapshot```s; these cases must be handled manually by providing ```Snapshot```s with data on initial conditions.

<a name="checkpointing.behaviour.example"></a>

###   Example
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

<a name="checkpointing.issues"></a>

##   Issues

<a name="checkpointing.issues.internal-state"></a>

###   Internal State
A lot of ```Process```es, solvers, and even the ```AnalysisStage``` keeps track of step indices and time internally, independently of their associated ```ModelPart```s. This can lead to all kinds of bugs that need to be tracked down individually for each object. The best solution is to modify these objects such that they query their ```Model``` or ```ModelPart```s when they need information about the current time and step, instead of relying on internally managed state.

<a name="checkpointing.issues.output"></a>

###   Output
Output generators (ideally ```OutputProcess```es) need to be configured such that they are allowed to overwrite existing output files. This is essential because an analysis involving checkpoints may pass through completely identical steps multiple times, triggering the same output generator.

Furthermore, the checkpoint system has no information about generated outputs, so if output is generated at steps/times that exceed the final step/time at which the analysis terminates, those output files will not be overwritten nor deleted, even though they are not part of the solution path. For this reason, a cleanup process should be executed at the end of the analysis.


<a name="registry"></a>

#  Registry

<a name="registry.cpp"></a>

##  C++
@todo

<a name="registry.python"></a>

##  Python

The python registry in `WRApplication` is automatically populated at module initialization time. To register new **python classes**, they must inherit from `WRAppClass` (directly or indirectly), and their containing script/module must eventually be imported in the root initializer.

Inheriting from `WRAppClass` also comes with some obligations in order to help with automation later:
- Derived classes must invoke the base constructor `super().__init__()`.
- Derived classes must implement the `GetDefaultParameters` classmethod.

Here's how registering would work for a new class `Registered` defined in `python_scripts/Registered.py`:

```py
# python_scripts/Registered.py

import KratosMultiphysics.WRApplication as WRApp

class Registered(WRApp.WRAppClass):
    def __init__(self):
        super().__init__()

    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters()


class RegisteredSub(Registered):
    def __init__(self):
        super().__init__()


__all__ = ["Registered, RegisteredSub"]
```

```py
# python_scripts/__init__.py
...
from .RegisteredClass import *
...
```

Registered classes are accessible in a dictionary under `WRApplication`, followed by their inheritance sequence after `WRAppClass`:
```py
registered_dict = KratosMultiphysics.Registry["WRApplication.Registered.RegisteredSub"] # <== {"type" : RegisteredSub}
registered_sub_type = registered_dict["type"] # <== RegisteredSub
```

**C++ classes** are also automatically registered in the python `Registry` if they are exposed via `pybind` and inherit from the C++ `WRAppClass`. Note that intermediate base classes will only appear on their access path if those intermediates are also exposed to python.


<a name="testing"></a>

#  Testing

<a name="testing.cpp"></a>

##  C++
No tests are written yet in C++; exposed classes' tests are implemented in python.

<a name="testing.python"></a>

##  Python
Python tests in `WRApplication` should inherit from the custom `TestCase` class that adds automatic detection and a flag system. By default, every test case is executed in all test suites, including MPI runs. Alternatively, the list of suites the test case is added to can be restricted by defining the `suite_flags` static member bitfield of the case:

```py
import KratosMultiphysics.WRApplication as WRApp

class MyTestCase(WRApp.TestCase):
    suite_flags = WRApp.SuiteFlags.NIGHTLY | WRApp.SuiteFlags.NO_MPI

    ...
```
