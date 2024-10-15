#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 26 13:41:57 2024

@author: DFuh
"""
import numpy as np
from pyomo.environ import *
from pyomo.opt import SolverFactory
from pyomo.util.infeasible import log_infeasible_constraints

def constr2d(data):
    out = {}
    for i,d in enumerate(data):
        for j,elm in enumerate(d):
            out[i,j] = elm

    return out



def create_process_model(load_timeseries=None, price_timeseries=None,
                            number_of_processes=2,total_number_of_cycles=2,
                            timerange=30,loadprofile=[0,1,1,0],
                            target_power_level=0):
    TN = len(load_timeseries)
    ls = number_of_processes
    #loadprofile = eaf_loadprofile

    f_par = constr2d(np.array([loadprofile] * ls))

    print('Setup model')
    ### Create pyomo model
    model = ConcreteModel()

    ### Sets
    model.S = Set(initialize=np.arange(ls))  # Systems
    model.R = Set(initialize=np.arange(len(loadprofile))) # Steps

    timeindex = np.arange(TN)
    timeindex_l = np.arange(TN+1)
    timeindex_quarterly = timeindex_l[timeindex_l % 15 == 0]
    print('t_idx_q: ', timeindex_quarterly)
    model.K = Set(initialize=timeindex)  # Timeindex
    model.Kq = Set(initialize=np.arange(len(timeindex_quarterly)))  # k-quarterly

    ### Parameters
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


    ###########################################################################
    ### Objective function
    ######################################

    def objective_rule(model):

        return (#sum( ((2 * (model.auxvar0[k] + model.auxvar1[k]))) * model.P_price[k]   for k in model.K)
                + model.Costs_surcharges)

    model.Objective = Objective(rule=objective_rule, sense=minimize)

    ###########################################################################
    ### Constraints
    ###########################################################################

    ### check P_abs
    def check_pabs(model, k):
        return model.testv_k[k] == (2 * (model.auxvar0[k] + model.auxvar1[k])) * model.P_price[k] # (model.P_res[k]-model.P_tar)

    model.CheckPdiff = Constraint(model.K, rule=check_pabs)

    ### Absolute value in objective function
    def absolute_value_Pdiff(model, k):
        # if value(model.auxvar0[k])>=0 and value(model.auxvar1[k])>=0:
        return model.auxvar0[k] - model.auxvar1[k] == (model.P_res[k] - model.P_tar)

    model.AbsPdiff = Constraint(model.K, rule=absolute_value_Pdiff)


    ### Grid surcharges
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

    ### Power of single Process
    def process_power(model, s, k):

        return model.P_s_k[s, k] == sum(model.fs_r[s, r] * model.ws_r_k[s, r, k] for r in model.R)

    model.ProcessPower = Constraint(model.S, model.K, rule=process_power)

    ####################################
    ########## w_srk

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

    ###########################################################################
    ### Edit multi sequences
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

        ### Number of cycles
        def numcyc(model):
            return sum(model.sp_s_k[s, k] for s in model.S for k in model.K) == total_number_of_cycles

        model.NumCyc = Constraint(rule=numcyc)

        def numcyc2(model, r):
            return sum(model.ws_r_k[s, r, k] for s in model.S for k in model.K) == total_number_of_cycles

        model.NumCyc2 = Constraint(model.R, rule=numcyc2)


    return model












