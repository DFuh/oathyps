import numpy as np
from loguru import logger

import pyomo.environ as pyo
from .. import io


class ProcessModel:
    # TODO: rename timeseries -> proper names
    objectives = [
        "powerdeviation",
        "powerdeviation_quadratic",
        "electricitycosts",
        "electricitycosts_incl_surcharges",
        "electricitycosts_incl_surcharges_poweronly",
    ]

    def __init__(self, parameters: dict, timeseries: dict, objective=None):
        self.model = None
        self.objective = objective
        self.parameters = parameters
        self.timeseries = timeseries

        if not self.parameters.timerange:
            self.parameters.timerange = len(self.timeseries["load"])

    def solve(self, verbose=False, solverlogfile=None):
        logger.info(f"Solve model using solver: {self.parameters.solver}...")
        opt = pyo.SolverFactory(self.parameters.solver)
        logger.info("Start solving model")
        x = opt.solve(
            self.model,
            tee=verbose,
            logfile=solverlogfile,
        )
        return self.model

    def extract_data(self):
        """
        Create nested dict of structure {variable: {variablename_level: values}}
        """

        self.variable_values = {
            varnm: io.extract_variablevalue(getattr(self.model, varnm, None))
            for varnm in self.parameters.extract_data
        }
        return self.variable_values

    def build(self):
        logger.info("Build model ... ")
        self.model = self.basic_model()
        logger.info(f"Objective: {self.objective} ")
        match self.objective:
            case "powerdeviation":
                self.model = self.powerdev_objective(self.model, quadratic=False)

            case "powerdeviation_quadratic":
                self.model = self.powerdev_objective(self.model, quadratic=True)

            case "electricitycosts":
                self.model = self.electricitycosts_objective(
                    self.model, include_surcharges=False
                )

            case "electricitycosts_incl_surcharges":
                self.model = self.electricitycosts_objective(
                    self.model, include_surcharges=True, poweronly=False
                )
            case "electricitycosts_incl_surcharges_poweronly":
                self.model = self.electricitycosts_objective(
                    self.model, include_surcharges=True, poweronly=True
                )
        return

    def basic_model(self):

        loadprofile = self.timeseries["loadprofile"]  # .to_numpy()

        logger.info("Setup concrete model")
        model = pyo.ConcreteModel()

        logger.info("Initialize basic Sets")
        model.S = pyo.Set(initialize=np.arange(self.parameters.number_of_processes))
        model.T = pyo.Set(initialize=np.arange(self.parameters.timerange))

        logger.info("Initialize basic Parameters")
        model.ds = pyo.Param(initialize=len(loadprofile))
        model.TN = pyo.Param(initialize=self.parameters.timerange)
        model.pfix = pyo.Param(
            model.T, initialize=self.timeseries["load"]
        )  # .to_numpy())

        logger.info("Initialize Variables")

        model.w = pyo.Var(model.T, model.S, within=pyo.Binary)
        model.pprc = pyo.Var(model.T, model.S, within=pyo.NonNegativeReals)
        model.pres = pyo.Var(model.T)  # Resulting power
        model.pabs = pyo.Var(model.T)

        model.auxvar0 = pyo.Var(model.T, initialize=0, within=pyo.NonNegativeReals)
        model.auxvar1 = pyo.Var(model.T, initialize=0, within=pyo.NonNegativeReals)
        model.powerdev = pyo.Var()

        # ===================================================================
        logger.info("Initialize Constraints")

        def resultingpower(model, t):
            return model.pres[t] == model.pfix[t] + sum(
                model.pprc[t, s] for s in model.S
            )

        model.ResPow = pyo.Constraint(model.T, rule=resultingpower)

        def processpower(model, t, s):
            return model.pprc[t, s] == sum(
                model.w[t - i, s] * val
                for i, val in enumerate(loadprofile)
                if t - i >= 0
            )

        model.ProcessPower = pyo.Constraint(model.T, model.S, rule=processpower)

        def numberofcycles(model):
            return (
                sum(model.w[i] for i in model.T * model.S)
                == self.parameters.total_number_of_cycles
            )

        model.NumCyc = pyo.Constraint(rule=numberofcycles)

        def nooverlap(model, t, s):
            if (t + model.ds) < model.TN:
                return sum(model.w[t + i, s] for i in range(pyo.value(model.ds))) <= 1
            else:
                return model.w[t, s] == 0  # pyo.Constraint.Skip

        model.NoO = pyo.Constraint(model.T, model.S, rule=nooverlap)

        def limw(model, t, s):
            if (t - model.ds) <= 0:
                return model.w[t, s] == 0
            else:
                return pyo.Constraint.Skip

        # model.LimW = pyo.Constraint(model.T, model.S, rule=limw)

        return model

    def powerdev_objective(self, model, quadratic=False):

        model.ptar = pyo.Param(initialize=self.parameters.target_power_level)

        def absolute_value_Pdiff(model, t):
            return model.auxvar0[t] - model.auxvar1[t] == (model.ptar - model.pres[t])

        if quadratic:
            logger.info("Objective function: Quadratic powerdev")

            def abspowerdev(model):
                return model.powerdev == sum(
                    ((2 * (model.auxvar0[t] + model.auxvar1[t])) ** 2) for t in model.T
                )

        else:
            logger.info("Objective function: Non-Quadratic powerdev")

            def abspowerdev(model):
                return model.powerdev == sum(
                    ((2 * (model.auxvar0[t] + model.auxvar1[t]))) for t in model.T
                )

        ### Variable for testing purposes
        if False:

            def check_pabs(model, k):
                return model.pabs[k] == (2 * (model.auxvar0[k] + model.auxvar1[k]))

            model.CheckPabs = pyo.Constraint(model.T, rule=check_pabs)

        model.AbsPdiff = pyo.Constraint(model.T, rule=absolute_value_Pdiff)
        model.PowerDev = pyo.Constraint(rule=abspowerdev)

        def powerdev_objective(model):
            return model.powerdev  # sum( model.pres[t] - model.ptar for t in model.T)

        model.Objective = pyo.Objective(rule=powerdev_objective, sense=pyo.minimize)
        return model

    def electricitycosts_objective(
        self, model, include_surcharges=False, poweronly=False
    ):
        model.cres = pyo.Var(model.T, within=pyo.Reals)
        model.cfix = pyo.Param(
            model.T, initialize=self.timeseries["price"]
        )  # .to_numpy())

        def resultingcosts(model, t):
            return model.cres[t] == model.pres[t] / 60 * model.cfix[t]

        model.rescosts = pyo.Constraint(model.T, rule=resultingcosts)

        if not include_surcharges:

            def electricitycosts_objective(model):
                return sum(
                    model.cres[t] for t in model.T
                )  # sum( model.pres[t] - model.ptar for t in model.T)

            model.Objective = pyo.Objective(
                rule=electricitycosts_objective, sense=pyo.minimize
            )
        else:
            model = self.gridsurcharges_objective(model, poweronly=poweronly)
        return model

    def gridsurcharges_objective(self, model, poweronly=False):
        timeindex_l = np.arange(self.parameters.timerange + 1)
        timeindex_quarterly = timeindex_l[timeindex_l % 15 == 0]
        model.Tq = pyo.Set(
            initialize=np.arange(len(timeindex_quarterly))
        )  # k-quarterly
        model.gs_price_energy = pyo.Param(initialize=0.34 / 1e2)  # €/kWh
        model.gs_price_power = pyo.Param(initialize=107.08)  # €/kW
        model.aux_gs_b = pyo.Var(model.Tq, within=pyo.Binary)
        model.P_quart = pyo.Var(model.Tq, within=pyo.Reals)
        model.P_max_quart = pyo.Var()
        model.costs_gridsurcharges = pyo.Var()

        model.aux_kq = pyo.Param(
            model.Tq, initialize=timeindex_quarterly, within=pyo.NonNegativeIntegers
        )
        model.aux_gs_M = pyo.Param(initialize=1e12)

        model = self.add_constraints_gridsurcharges_(
            model, poweronly=poweronly, plimq=None
        )  # Pqlim)

        logger.warning("PQlim hardcoded to -> None")

        def total_electricitycosts_objective(model):
            # return sum(model.cres[t] for t in model.T) + model.costs_gridsurcharges # sum( model.pres[t] - model.ptar for t in model.T)

            return (
                model.costs_gridsurcharges
            )  # sum( model.pres[t] - model.ptar for t in model.T)

        model.Objective = pyo.Objective(rule=total_electricitycosts_objective)
        return model

    def add_constraints_gridsurcharges_(self, model, poweronly=False, plimq=None):
        ### Grid surcharges
        logger.debug("Define Constraints for grid surcharges")

        if poweronly:

            def gridsurcharges(model):
                return (
                    model.costs_gridsurcharges
                    == model.P_max_quart * model.gs_price_power
                )

        else:

            def gridsurcharges(model):

                return model.costs_gridsurcharges == (
                    sum(model.pres[k] / 60 * model.gs_price_energy for k in model.T)
                    + model.P_max_quart * model.gs_price_power
                )

        def gs_power_quarterly(model, kq):
            if model.aux_kq[kq] < model.TN + 1:
                return (
                    model.P_quart[kq]
                    == sum(
                        model.pres[k]
                        for k in model.T
                        if pyo.value(k) >= model.aux_kq[kq]
                        and pyo.value(k) <= model.aux_kq[kq + 1]
                    )
                    / 15
                )
            else:
                return pyo.Constraint.Skip

        def gs_power_quarterly0(model, kq):
            return model.P_max_quart >= model.P_quart[kq]

        def gs_power_quarterly1(model, kq):
            return (
                model.P_max_quart
                <= model.P_quart[kq] + (1 - model.aux_gs_b[kq]) * model.aux_gs_M
            )

        def gs_power_quarterly2(model):
            return sum(model.aux_gs_b[kq] for kq in model.Tq) == 1

        if plimq is not None:
            logger.info("Add constraint for ul P_max_quarterly")

        def lim_pmax_quart(model, kq):
            return model.P_max_quart <= 1000  # plimq

        model.ulPqlim = pyo.Constraint(model.Tq, rule=lim_pmax_quart)

        logger.debug("Ini Constraints for grid surcharges")
        model.GridSurcharges = pyo.Constraint(rule=gridsurcharges)
        model.gs_PowerQuart = pyo.Constraint(model.Tq, rule=gs_power_quarterly)
        model.gs_PowerQuart0 = pyo.Constraint(model.Tq, rule=gs_power_quarterly0)
        model.gs_PowerQuart1 = pyo.Constraint(model.Tq, rule=gs_power_quarterly1)
        model.gs_PowerQuart2 = pyo.Constraint(rule=gs_power_quarterly2)
        model.PqLim = pyo.Constraint(model.Tq, rule=lim_pmax_quart)
        return model
