#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 26 13:41:57 2024

@author: DFuh
"""
import numpy as np
from loguru import logger
import pyomo.environ as pyo
#from pyomo.environ import *
from pyomo.opt import SolverFactory
from pyomo.util.infeasible import log_infeasible_constraints

def constr2d(data):
    out = {}
    for i,d in enumerate(data):
        for j,elm in enumerate(d):
            out[i,j] = elm

    return out


def create_simple_process_model(load_timeseries=None, price_timeseries=None,
                            number_of_processes=2,total_number_of_cycles=2,
                            timerange=30,
                            loadprofile=[0,1,1,0],
                            target_power_level=0,
                            quadratic_powerdev=False,
                            test=False,
                            obj_electricitycosts=False,
                            obj_powerdev=True,
                            obj_total_electricitycosts=False,
                            test_no_binaries=False,
                            Pqlim=None,
                            **kwargs
                                ):
    abort = False
    logger.info("Create simple process (optimization) model")
    logger.info("Objective settings: \n powerdev={}, \n electricitycosts={}, \n total_electricitycosts={}",
                obj_powerdev,obj_electricitycosts,obj_total_electricitycosts)
    if obj_powerdev is True:
        if obj_electricitycosts is True:
            logger.warning('Multiple objectives chosen: Set >powerdev< ')
        obj_electricitycosts = False

    if load_timeseries is not None:
        timerange = len(load_timeseries)
    elif load_timeseries is None and timerange is not None:
        load_timeseries = np.ones(timerange)
    else:
        abort = True
        model = None
        logger.info(" ---Abort--- ")

    if not abort:

        logger.info("Setup concrete model")
        model = pyo.ConcreteModel()

        logger.info("Initialize Sets")
        model.S = pyo.Set(initialize=np.arange(number_of_processes))
        model.T = pyo.Set(initialize=np.arange(timerange))

        logger.info("Initialize Parameters")
        model.ds = pyo.Param(initialize=len(loadprofile))
        model.TN = pyo.Param(initialize=timerange)
        model.pfix = pyo.Param(model.T, initialize=load_timeseries)

        if obj_electricitycosts or obj_total_electricitycosts:
            model.cfix = pyo.Param(model.T, initialize=price_timeseries)
        model.ptar = pyo.Param(initialize=target_power_level)

        logger.info("Initialize Variables")
        if test_no_binaries:
            logger.warning('No domain specified for variable: model.w')
            model.w = pyo.Var(model.T, model.S)
        else:
            model.w = pyo.Var(model.T, model.S, within=pyo.Binary)

        model.pprc = pyo.Var(model.T, model.S, within=pyo.NonNegativeReals)
        if obj_electricitycosts or obj_total_electricitycosts:
            model.cres = pyo.Var(model.T,within=pyo.Reals)
        model.pres = pyo.Var(model.T)  # Resulting power
        model.pabs = pyo.Var(model.T)

        model.auxvar0 = pyo.Var(model.T, initialize=0, within=pyo.NonNegativeReals)
        model.auxvar1 = pyo.Var(model.T, initialize=0, within=pyo.NonNegativeReals)
        model.powerdev = pyo.Var()
        if obj_total_electricitycosts:
            timeindex_l = np.arange(timerange + 1)
            timeindex_quarterly = timeindex_l[timeindex_l % 15 == 0]
            model.Tq = pyo.Set(initialize=np.arange(len(timeindex_quarterly)))  # k-quarterly
            model.gs_price_energy = pyo.Param(initialize=0.34 / 1e2)  # €/kWh
            model.gs_price_power = pyo.Param(initialize=107.08)  # €/kW
            model.aux_gs_b = pyo.Var(model.Tq, within=pyo.Binary)
            model.P_quart = pyo.Var(model.Tq, within=pyo.Reals)
            model.P_max_quart = pyo.Var()
            model.costs_gridsurcharges = pyo.Var()

            model.aux_kq = pyo.Param(model.Tq, initialize=timeindex_quarterly, within=pyo.NonNegativeIntegers)
            model.aux_gs_M = pyo.Param(initialize=1e6)
            model.gs_price_energy = pyo.Param(initialize=0.34 / 1e2)  # €/kWh
            model.gs_price_power = pyo.Param(initialize=107.08)  # €/kW
        ###############################################################################

        ###############################################################################

        logger.info("Initialize Objective function")
        def powerdev_objective(model):
            return model.powerdev  # sum( model.pres[t] - model.ptar for t in model.T)

        def electricitycosts_objective(model):
            return sum(model.cres[t] for t in model.T)  # sum( model.pres[t] - model.ptar for t in model.T)

        def total_electricitycosts_objective(model):
            #return sum(model.cres[t] for t in model.T) + model.costs_gridsurcharges # sum( model.pres[t] - model.ptar for t in model.T)

            return model.costs_gridsurcharges  # sum( model.pres[t] - model.ptar for t in model.T)

        if obj_powerdev:
            model.Objective = pyo.Objective(rule=powerdev_objective, sense=pyo.minimize)
        elif obj_electricitycosts:
            model.Objective = pyo.Objective(rule=electricitycosts_objective, sense=pyo.minimize)
        elif obj_total_electricitycosts:
            model.Objective = pyo.Objective(rule=total_electricitycosts_objective, sense=pyo.minimize)

        if obj_powerdev:
            ### Absolute value in objective function
            def absolute_value_Pdiff(model, t):
                return model.auxvar0[t] - model.auxvar1[t] == (model.ptar - model.pres[t])

            ### Absolute power deviation

            if quadratic_powerdev:
                logger.info("Objective function: Quadratic powerdev")
                def abspowerdev(model):
                    return model.powerdev == sum(((2 * (model.auxvar0[t] + model.auxvar1[t]))**2 ) for t in model.T)
            else:
                logger.info("Objective function: Non-Quadratic powerdev")
                def abspowerdev(model):
                    return model.powerdev == sum(((2 * (model.auxvar0[t] + model.auxvar1[t])) ) for t in model.T)

            ### Variable for testing purposes
            if test:
                def check_pabs(model, k):
                    return model.pabs[k] == (2 * (model.auxvar0[k] + model.auxvar1[k]))

                model.CheckPabs = pyo.Constraint(model.T, rule=check_pabs)

            model.AbsPdiff = pyo.Constraint(model.T, rule=absolute_value_Pdiff)
            model.PowerDev = pyo.Constraint(rule=abspowerdev)

        elif obj_electricitycosts or obj_total_electricitycosts:
            def resultingcosts(model,t):
                return model.cres[t] == model.pres[t]/60 * model.cfix[t]

            model.rescosts = pyo.Constraint(model.T, rule=resultingcosts)

        if obj_total_electricitycosts:
            model = add_constraints_gridsurcharges_(model, plimq=Pqlim)
        ###############################################################################

        ###############################################################################
        logger.info("Initialize Constraints")
        def resultingpower(model, t):
            return model.pres[t] == model.pfix[t] + sum(model.pprc[t, s] for s in model.S)

        model.ResPow = pyo.Constraint(model.T, rule=resultingpower)
        logger.info('Test')
        def processpower(model, t, s):
            # if (t - model.ds) >= 0:
            return model.pprc[t, s] == sum(model.w[t - i, s] * val for i, val in enumerate(loadprofile) if t-i >=0)

        model.ProcessPower = pyo.Constraint(model.T, model.S, rule=processpower)

        def numberofcycles(model):
            return sum(model.w[i] for i in model.T * model.S) == total_number_of_cycles

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

        logger.info("Finished setup of model")
    return model



def add_constraints_gridsurcharges_(model, plimq=None):
    ### Grid surcharges
    logger.debug("Define Constraints for grid surcharges")

    #model.Costs_powerdev = Var()

    def gridsurcharges(model):

        return model.costs_gridsurcharges == (0 #sum(model.pres[k] / 60 * model.gs_price_energy for k in model.T)
                                          + model.P_max_quart * model.gs_price_power)

    #def aux_cgs(model, t):
    #    return model.pres[t] / 60 * model.gs_price_energy + model.P_max_quart * model.gs_price_power)


    def gs_power_quarterly(model, kq):
        if model.aux_kq[kq] < model.TN+1:
            return model.P_quart[kq] == sum(model.pres[k] for k in model.T if
                                            pyo.value(k) >= model.aux_kq[kq] and pyo.value(k) <= model.aux_kq[kq + 1]) / 15
        else:
            return pyo.Constraint.Skip

    def gs_power_quarterly0(model, kq):

        return model.P_max_quart >= model.P_quart[kq]

    def gs_power_quarterly1(model, kq):

        return model.P_max_quart <= model.P_quart[kq] + (1 - model.aux_gs_b[kq]) * model.aux_gs_M

    def gs_power_quarterly2(model):

        return sum(model.aux_gs_b[kq] for kq in model.Tq) == 1

    if plimq is not None:
        logger.info("Add constraint for ul P_max_quarterly")
        def lim_pmax_quart(model,kq):
            return model.P_max_quart <= plimq
        model.ulPqlim = pyo.Constraint(model.Tq, rule=lim_pmax_quart)

    logger.debug("Ini Constraints for grid surcharges")
    model.GridSurcharges = pyo.Constraint(rule=gridsurcharges)
    model.gs_PowerQuart = pyo.Constraint(model.Tq, rule=gs_power_quarterly)
    model.gs_PowerQuart0 = pyo.Constraint(model.Tq, rule=gs_power_quarterly0)
    model.gs_PowerQuart1 = pyo.Constraint(model.Tq, rule=gs_power_quarterly1)
    model.gs_PowerQuart2 = pyo.Constraint(rule=gs_power_quarterly2)

    return model


def create_process_model(load_timeseries=None, price_timeseries=None,
                            number_of_processes=2,total_number_of_cycles=2,
                            timerange=30,loadprofile=[0,1,1,0],
                            target_power_level=0,
                            enable_obj_powerdeviation=1,
                            enable_obj_surcharges=0):

    logger.info("Create process (optimization) model")

    TN = len(load_timeseries)
    ls = number_of_processes
    #loadprofile = eaf_loadprofile

    f_par = constr2d(np.array([loadprofile] * ls))

    logger.info("Setup concrete model")
    ### Create pyomo model
    model = ConcreteModel()

    ### Sets
    logger.debug("Ini Sets")
    model.S = Set(initialize=np.arange(ls))  # Systems
    model.R = Set(initialize=np.arange(len(loadprofile))) # Steps

    timeindex = np.arange(TN)
    timeindex_l = np.arange(TN+1)
    timeindex_quarterly = timeindex_l[timeindex_l % 15 == 0]
    logger.trace("t_idx_q: {}", timeindex_quarterly)
    model.K = Set(initialize=timeindex)  # Timeindex
    model.Kq = Set(initialize=np.arange(len(timeindex_quarterly)))  # k-quarterly

    ### Parameters
    logger.debug("Ini Parameters")
    model.aux_kq = Param(model.Kq,initialize=timeindex_quarterly,within=NonNegativeIntegers)
    model.aux_gs_M = Param(initialize=1e6)
    model.gs_price_energy = Param(initialize=0.34 / 1e2)  # €/kWh
    model.gs_price_power = Param(initialize=107.08)  # €/kW

    model.fs_r = Param(model.S, model.R, initialize=f_par)
    model.ds = Param(model.S, initialize=[len(loadprofile)] * ls)
    model.prodmin = Param(initialize=ls)
    model.limparallel = Param(initialize=2)

    model.P_fix = Param(model.K, initialize=load_timeseries)
    model.P_price = Param(model.K, initialize=price_timeseries)

    ### Variables
    logger.debug("Ini Variables")
    model.P_s_k = Var(model.S, model.K, within=NonNegativeReals)
    model.P_res = Var(model.K, within=NonNegativeReals)

    model.ws_r_k = Var(model.S, model.R, model.K, within=Binary)

    model.P_lb = Param(model.S, initialize=[loadprofile.sum()] * ls, within=NonNegativeReals)

    model.sp_s_k = Var(model.S, model.K, within=Binary)  # Start process (of system s)
    model.idxsp_s = Var(model.S, within=Integers)  # (time) Index of process Start (of system s)
    model.ep_s_k = Var(model.S, model.K, within=Binary)  # end process of system s
    model.actp_s_k = Var(model.S, model.K, within=Binary)  # process of system s active

    model.auxvar0 = Var(model.K, initialize=0, within=NonNegativeReals)
    model.auxvar1 = Var(model.K, initialize=0, within=NonNegativeReals)
    model.P_tar = Param(initialize=target_power_level)
    model.P_res_obj = Var(model.K, initialize=0, within=NonNegativeReals)

    #    model.auxvar_idx = Param(model.K, initialize=np.arange(model.K.__len__()), within=NonNegativeIntegers)
    model.testv_r = Var(model.S, model.K,
                        # initialize=constr2d(np.array([np.zeros(model.K.__len__()),np.zeros(model.K.__len__())])),
                        # within=NonNegativeReals
                        )
    model.penalty = Var(model.K, within=Reals)
    model.testv_k = Var(model.K, )



    model.aux_gs_b = Var(model.Kq,within=Binary)
    model.P_quart = Var(model.Kq,within=Reals)
    model.P_max_quart =Var()
    model.Costs_surcharges = Var()
    model.Costs_powerdev = Var()


    ###########################################################################
    ### Objective function
    ######################################
    logger.debug("Ini Objective")
    def objective_rule(model):

        return (model.Costs_powerdev * enable_obj_powerdeviation
                + model.Costs_surcharges * enable_obj_surcharges
                )

    model.Objective = Objective(rule=objective_rule, sense=minimize)

    ###########################################################################
    ### Constraints
    ###########################################################################
    logger.debug("Ini Constraints")

    ### check P_abs

    def check_pabs(model, k):
        return model.testv_k[k] == (2 * (model.auxvar0[k] + model.auxvar1[k])) * model.P_price[k] # (model.P_res[k]-model.P_tar)

    model.CheckPdiff = Constraint(model.K, rule=check_pabs)
    logger.debug("Ini Constraint: {}",model.CheckPdiff.name)

    ### Absolute value in objective function
    def absolute_value_Pdiff(model, k):
        # if value(model.auxvar0[k])>=0 and value(model.auxvar1[k])>=0:
        return model.auxvar0[k] - model.auxvar1[k] == (model.P_res[k] - model.P_tar)

    model.AbsPdiff = Constraint(model.K, rule=absolute_value_Pdiff)
    logger.debug("Ini Constraint: {}", model.AbsPdiff.name)

    ### Absolute power deviation
    def abspowerdev(model):
        return model.Costs_powerdev == sum(((2 * (model.auxvar0[k] + model.auxvar1[k]))) * model.P_price[k] for k in model.K)

    model.CPowerDev = Constraint(rule=abspowerdev)
    logger.debug("Ini Constraint: {}", model.CPowerDev.name)

    ### Grid surcharges
    logger.debug("Define Constraints for grid surcharges")
    def gridsurcharges(model):

        return model.Costs_surcharges == (sum(model.P_res[k]/60 * model.gs_price_energy for k in model.K)
                        + model.P_max_quart * model.gs_price_power)



    def gs_power_quarterly(model,kq):
        if model.aux_kq[kq] < TN:
            return model.P_quart[kq] == sum(model.P_res[k] for k in model.K if value(k)>= model.aux_kq[kq] and value(k)<= model.aux_kq[kq+1])/15
        else:
            return Constraint.Skip

    def gs_power_quarterly0(model,kq):

        return model.P_max_quart >= model.P_quart[kq]

    def gs_power_quarterly1(model, kq):

        return model.P_max_quart <= model.P_quart[kq] + (1-model.aux_gs_b[kq])*model.aux_gs_M

    def gs_power_quarterly2(model):

        return sum(model.aux_gs_b[kq] for kq in model.Kq) == 1

    logger.debug("Ini Constraints for grid surcharges")
    model.GridSurcharges = Constraint(rule=gridsurcharges)
    model.gs_PowerQuart = Constraint(model.Kq, rule=gs_power_quarterly)
    model.gs_PowerQuart0 = Constraint(model.Kq, rule=gs_power_quarterly0)
    model.gs_PowerQuart1 = Constraint(model.Kq, rule=gs_power_quarterly1)
    model.gs_PowerQuart2 = Constraint(rule=gs_power_quarterly2)


    ### Penalty constraint
    def maxloadpenalty(model,k):
        #if value(model.P_res[k]) <= 500:#value(model.P_tar):
        #    return model.penalty[k] ==0
        #elif value(model.P_res[k]) <= 1000:#value(model.P_tar)*1.1:
        #    return model.penalty[k] == 10000
        #else:
        #    return model.penalty[k] == 20000
        return model.penalty[k] == (model.P_res[k] - 1300)*10000
    #model.MaxLoadPenalty = Constraint(model.K,rule=maxloadpenalty)

    ### Resulting Power

    def resulting_power(model, k):
        return model.P_res[k] == sum(model.P_s_k[s, k] for s in model.S) + model.P_fix[k]

    model.ResultingPower = Constraint(model.K, rule=resulting_power)
    logger.debug("Ini constraint: {}", model.ResultingPower.name)
    ### Power of single Process
    def process_power(model, s, k):

        return model.P_s_k[s, k] == sum(model.fs_r[s, r] * model.ws_r_k[s, r, k] for r in model.R)

    model.ProcessPower = Constraint(model.S, model.K, rule=process_power)
    logger.debug("Ini constraint: {}", model.ProcessPower.name)
    ####################################
    ########## w_srk
    logger.debug("Ini constraints for {}", model.ws_r_k.name)
    ### >=0
    def fix_w00(model, s, r, k):

        return model.ws_r_k[s, r, k] >= 0

    model.fix_w_00 = Constraint(model.S, model.R, model.K, rule=fix_w00)

    ### >=1
    def fix_w01(model, s, r, k):

        return model.ws_r_k[s, r, k] <= 1

    model.fix_w_01 = Constraint(model.S, model.R, model.K, rule=fix_w01)

    ### Additional Variable for Testing
    def check_w(model, s, k):
        # if k >0:
        return sum((model.ws_r_k[s, r, k] * value(r)) for r in model.R) == model.testv_r[s, k]

    model.CheckW = Constraint(model.S, model.K, rule=check_w)

    ### Ensure sequence

    def ensure_sequence(model, s, r, k):
        if value(k) > 0 and k < TN - 1 and r < model.ds[
            s] - 1:  # and value(k) >= value(model.idxsp_s[s]) and value(k) <= value(model.idxsp_s[s])+model.ds[s]-1 and r<model.ds[s]-1:

            return model.ws_r_k[s, r + 1, k + 1] >= model.ws_r_k[s, r, k]
        else:
            return Constraint.Skip

    model.EnsureSequence = Constraint(model.S, model.R, model.K, rule=ensure_sequence)
    logger.debug("Ini constraint: {}", model.EnsureSequence.name)
    ### Ensure activation

    def fix_w1(model, s, r):
        return sum(model.ws_r_k[s, r, k] for k in model.K) == 1

    # model.fix_w_1 = Constraint(model.S, model.R,rule=fix_w1)

    # if False:
    #    ### Initiate loadprofile
    #    def fix_w3(model,s,k):
    #        if k<TN-model.ds[s]:
    #            return sum(model.ws_r_k[s,0,k] for k in model.K) >=1
    #        else:
    #            return Constraint.Skip
    #    #model.fix_w_3 = Constraint(model.S,model.K, rule=fix_w3)

    # if False:
    #    def fix_w4(model,s):
    #        return sum(model.ws_r_k[s,r,k] for r in model.R for k in model.K) >=len(model.R)

    ### Fix Start
    def fix_w_start(model, s, r):

        return model.ws_r_k[s, r, 0] == 0

    model.FixWStart = Constraint(model.S, model.R, rule=fix_w_start)

    ### Fix End
    def fix_w_end(model, s, r):

        return model.ws_r_k[s, r, TN - 1] == 0

    model.FixWEnd = Constraint(model.S, model.R, rule=fix_w_end)

    ### Index of production start
    # def production_idx(model,s):
    #
    #    return model.idxsp_s[s] == sum(model.sp_s_k[s,k] * value(k)  for k in model.K)
    #
    # model.ProdIdx = Constraint(model.S, rule=production_idx)

    ### Limit of parallel processes
    def limit_parallel_processes(model, s, k):

        return sum(model.actp_s_k[s, k] for s in model.S) <= model.limparallel

    model.ParallelLim = Constraint(model.S, model.K, rule=limit_parallel_processes)
    logger.debug("Ini constraint: {}", model.ParallelLim.name)
    ###########################################################################
    ### Edit multi sequences
    logger.debug("Ini constraints for process: start/end/active")
    if True:
        ### Start Variable
        def start0(model, s, k):
            return model.sp_s_k[s, k] <= model.actp_s_k[s, k]

        def start1(model, s, k):
            if k > 0:
                return model.sp_s_k[s, k] <= 1 - model.actp_s_k[s, k - 1]
            else:
                return Constraint.Skip

        def start2(model, s, k):
            if k > 0:
                return model.actp_s_k[s, k] - model.actp_s_k[s, k - 1] <= model.sp_s_k[s, k]
            else:
                return Constraint.Skip

        ### End Variable
        def end0(model, s, k):
            return model.ep_s_k[s, k] <= model.actp_s_k[s, k]

        def end1(model, s, k):
            if k < TN - 1:
                return model.ep_s_k[s, k] <= 1 - model.actp_s_k[s, k + 1]
            else:
                return Constraint.Skip

        def end2(model, s, k):
            if k < TN - 1:
                return model.actp_s_k[s, k] - model.actp_s_k[s, k + 1] <= model.ep_s_k[s, k]
            else:
                return Constraint.Skip

        ### Activation
        def act(model, s, k):
            return model.actp_s_k[s, k] == sum(model.ws_r_k[s, r, k] for r in model.R)

        ### bind on/off
        def start_end_binding(model, s, k):
            if k < TN - model.ds[s]:
                return model.sp_s_k[s, k] == model.ep_s_k[s, k + model.ds[s] - 1]
            else:
                return Constraint.Skip

        model.Start0 = Constraint(model.S, model.K, rule=start0)
        model.Start1 = Constraint(model.S, model.K, rule=start1)
        model.Start2 = Constraint(model.S, model.K, rule=start2)
        model.End0 = Constraint(model.S, model.K, rule=end0)
        model.End1 = Constraint(model.S, model.K, rule=end1)
        model.End2 = Constraint(model.S, model.K, rule=end2)
        model.Act = Constraint(model.S, model.K, rule=act)
        model.BindStartEnd = Constraint(model.S, model.K, rule=start_end_binding)


        logger.debug("Ini constraints for numbers of cycles")
        ### Number of cycles
        def numcyc(model):
            return sum(model.sp_s_k[s, k] for s in model.S for k in model.K) == total_number_of_cycles

        model.NumCyc = Constraint(rule=numcyc)

        def numcyc2(model, r):
            return sum(model.ws_r_k[s, r, k] for s in model.S for k in model.K) == total_number_of_cycles

        model.NumCyc2 = Constraint(model.R, rule=numcyc2)


    logger.debug("Finished ini of constraints")
    return model












