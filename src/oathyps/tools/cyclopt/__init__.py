"""Optimize the scheduling of cyclic industrial processes

Read load timeseries, load profiles and [optional] prices
and ...

        or import library and use cyclopt object
Unit convention: kW

Usage: cyclopt <path>


Options:
  -h --help  Print this help message and exit.
  --lp=bool  Save the model's LP file.
"""

import os
import pandas as pd
from loguru import logger
from docopt import docopt
from dataclasses import dataclass, field
from importlib import import_module
from pyomo.core.kernel.parameter import parameter

# import rich.traceback
from . import io
from .models import simplecyclicprocess
from oathyps.misc import helpers as hlp


@dataclass
class Parameters:

    filename_load_timeseries: str  # load
    filename_price_timeseries: str  # price
    filename_loadprofile: str
    path_output: str
    manually_adjust_loadprofile: bool
    model: str
    number_of_processes: int = 2
    total_number_of_cycles: int = 4
    timerange: range = None  # timerange
    length_of_loadprofile: int = 4
    # loadprofile: pd.Series or list = field(default_factory=[0] + [1] * (length_of_loadprofile - 2) + [0])
    target_power_level: float = None

    objective: str = ""
    factor_load: float = 1.0
    offset_load: float = 0.0
    factor_price: float = 1.0
    offset_price: float = 0.0

    slice_load_start: int = 0
    slice_load_end: int = 10
    slice_price_start: int = 0
    slice_price_end: int = 10
    slice_loadprofile_start: int = 0
    slice_loadprofile_end: int = 10
    solver: str = "cbc"
    extract_data: list = field(default_factory=[])


class CyclicProcessOptimization:
    """
    Optimize schedule for cyclic (industrial) processe

    Note: When an objective including grid surcharges is chosen,
    the (sliced) time increment has to be an integer multiple of 15

    """

    def __init__(self, pth_to_dir):

        logger.info("Ini CPO")
        self.directory = pth_to_dir
        self.parameters = Parameters(**io.read_parameters(pth_to_dir))
        logger.info("Read timeseries")
        self.timeseries = {
            name: pd.read_csv(os.path.join(pth_to_dir, file), index_col=0)
            .iloc[slc0:slc1, [0]]
            .iloc[:, 0]
            .values
            for name, file, (slc0, slc1) in zip(
                ["load", "price", "loadprofile"],
                [
                    self.parameters.filename_load_timeseries,
                    self.parameters.filename_price_timeseries,
                    self.parameters.filename_loadprofile,
                ],
                [
                    (self.parameters.slice_load_start, self.parameters.slice_load_end),
                    (
                        self.parameters.slice_price_start,
                        self.parameters.slice_price_end,
                    ),
                    (
                        self.parameters.slice_loadprofile_start,
                        self.parameters.slice_loadprofile_end,
                    ),
                ],
            )
            if os.path.exists(os.path.join(pth_to_dir, file))
        }
        for k, v in self.timeseries.items():
            print(f"{k}: len: {len(v)} \n {v[:5]} shape: {v.shape}")  # v.head()}")

    def adjust_loadprofile(self):
        # TODO: reading loadprofile redundant
        self.pth_adjusted_loadprofile = os.path.join(
            self.pth_output, self.timestamp + "_adjusted_loadprofile.csv"
        )
        io.adjust_data(
            None,
            pth_in=os.path.join(self.directory, self.parameters.filename_loadprofile),
            pth_out=self.pth_adjusted_loadprofile,
            col="cyclic_process",
        )
        self.timeseries["loadprofile"] = (
            pd.read_csv(self.pth_adjusted_loadprofile, index_col=0)
            .iloc[slc0:slc1, [0]]
            .iloc[:, 0]
            .values
        )

    def setup_model_parameters(self):
        pass

        # if sum([self.parameters.solve_for_powerdeviation, self.parameters.solve_for_electricitycosts]) > 1:
        #    raise ValueError("More than one objective specified - select one option, please.")

    def initialize_output(self, basepath_out=""):
        logger.info("Initialize Output")
        self.timestamp = hlp.timestamp("ISO+md")
        if not basepath_out:
            if self.parameters.path_output:
                basepath_out = self.parameters.path_output
            else:
                basepath_out = self.directory

        self.pth_output = io.make_output_dir(
            os.path.join(
                basepath_out,
                "out",
                "_".join([self.timestamp, self.parameters.objective]),
            )
        )

    def write_values(self, variable_values):

        for nm, val in variable_values.items():

            if hasattr(val, "items"):
                for snm, sval in val.items():
                    if sval is not None:
                        logger.info(f"Write variable value: {snm}")
                        sval.to_csv(os.path.join(self.pth_output, f"var_{snm}.csv"))
            else:
                if val is not None:
                    logger.info(f"Write variable value: {nm}")
                    val.to_csv(os.path.join(self.pth_output, f"var_{nm}.csv"))
        return

    def initialize_process(self):
        logger.info("Initialize Process")
        match self.parameters.model:
            case "simple_cpo":
                self.process = models.simplecyclicprocess.ProcessModel(
                    self.parameters, self.timeseries
                )
                if self.parameters.objective in self.process.objectives:
                    self.process.objective = self.parameters.objective
                else:
                    raise ValueError("No matching objective specified")
            case other:
                logger.warning(f"Model '{self.parameters.model}' not found")
                self.model = None

        return


def main(options):

    logger.info("Create CPO-Instance")
    cpo = CyclicProcessOptimization(options["<path>"])

    print(__doc__)
    # if options.get("--lp") and not options.get("--buildonly"):
    if not options.get("--no-output", False):
        cpo.initialize_output(basepath_out=options.get("--path_out", ""))

    ## TODO: Update parameters with command line args?
    if False:  # True: #cpo.parameters.manually_adjust_loadprofile:
        logger.info("Manual adjustment of loadprofile: ")
        cpo.adjust_loadprofile()
    cpo.initialize_process()
    cpo.process.build()

    if True:  # options.get("--lp" ,'') =='y':
        logger.info("Write lp-file.")
        cpo.process.model.write(
            os.path.join(cpo.pth_output, "lpfile.lp"),
            io_options={"symbolic_solver_labels": True},
        )

    if not options.get("--buildonly"):

        logger.info("CPO: Solve model")
        model = cpo.process.solve(verbose=True, solverlogfile=None)
        output_values = cpo.process.extract_data()
        cpo.write_values(output_values)

    if False:  # options['--pickle_model']:
        pickle.dumps(model)

    logger.info(" - End - ")
    return model


if __name__ == "__main__":
    options = docopt(__doc__)
    main(options)
