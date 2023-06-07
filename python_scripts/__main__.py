# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp


arguments = WRApp.MakeCLI().parse_args()
if arguments.subcommand == "launch":
    WRApp.Launcher(arguments).Launch()
