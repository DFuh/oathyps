#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 26 13:41:57 2024

@author: dafu_res
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



def create_eaf_model(load_timeseries=None, price_timeseries=None,
                     number_of_eaf=2,timerange=30,eaf_loadprofile=[0,1,1,0],
                     target_power_level=0):

    TN = timerange
    ls = number_of_eaf
    loadprofile = eaf_loadprofile
    
    f_par = constr2d(np.array([loadprofile]*ls))
    
    
    ### Create pyomo model
    model = ConcreteModel()
    
    ### Sets
    model.S = Set(initialize=np.arange(ls))  # Beispielhafte Systeme
    model.R = Set(initialize=np.arange(len(loadprofile))) #[1, 2, 3])  # Beispielhafte Stufen
    
    model.K = Set(initialize=np.arange(TN)) #[1, 2, 3, 4])  # Beispielhafte Zeitintervalle


    ### Parameters
    model.fs_r = Param(model.S, model.R, initialize=f_par)
    model.ds = Param(model.S, initialize=[len(loadprofile)]*ls)
    model.prodmin = Param( initialize=ls)
    model.limparallel = Param( initialize=2)

    model.P_fix = Param(model.K, initialize=load_timeseries)
    model.P_price = Param(model.K, initialize=price_timeseries)

    ### Variablen
    model.P_s_k = Var(model.S, model.K, within=NonNegativeReals)
    model.P_res = Var(model.K, within=NonNegativeReals)

    model.ws_r_k = Var(model.S, model.R, model.K, within=Binary)

    model.P_lb = Param(model.S, initialize=[loadprofile.sum()]*ls, within=NonNegativeReals)

    model.sp_s_k = Var(model.S, model.K, within=Binary,initialize=0) # Start process (of system s)
    model.idxsp_s = Var(model.S, within=Integers, initialize=0) # (time) Index of process Start (of system s)
    model.ep_s_k = Var(model.S, model.K, within=Binary) # end process of system s
    model.actp_s_k = Var(model.S, model.K, initialize=0,within=Binary) # process of system s active

    model.slack0 = Var(model.K, initialize=0, within=NonNegativeReals)
    model.slack1 = Var(model.K, initialize=0, within=NonNegativeReals)
    model.P_tar = Param( initialize=target_power_level)
    model.P_res_obj = Var(model.K,initialize=0, within=NonNegativeReals)


#    model.slack_idx = Param(model.K, initialize=np.arange(model.K.__len__()), within=NonNegativeIntegers)
    model.testv_r = Var(model.S,model.K, #initialize=constr2d(np.array([np.zeros(model.K.__len__()),np.zeros(model.K.__len__())])),
                          #within=NonNegativeReals
                          )
    
    model.testv_k = Var(model.K,)
    ###########################################################################
    ### Objective function
    ######################################
    
    def objective_rule(model):
        
        return sum((2*(model.slack0[k] + model.slack1[k]))*model.P_price[k] for k in model.K)
    
    model.Objective = Objective(rule=objective_rule, sense=minimize)

    
    ###########################################################################
    ### Constraints
    ###########################################################################
    
    ### check P_abs
    def ckeck_pabs():
        return model.testv_k[k] == (model.P_res[k]-model.P_tar)

    ### Absolute value in objective function
    def absolute_value_Pdiff(model,k):
        #if value(model.slack0[k])>=0 and value(model.slack1[k])>=0: 
        return model.slack0[k] - model.slack1[k] == (model.P_res[k]-model.P_tar)    
    
    model.AbsPdiff = Constraint(model.K, rule=absolute_value_Pdiff)
    
    
    ### Resulting Power 
    def resulting_power(model,k):
        return model.P_res[k] == sum(model.P_s_k[s, k] for s in model.S) + model.P_fix[k]
    
    model.ResultingPower = Constraint(model.K, rule=resulting_power)
    
    
    ### Power of single Process
    def process_power(model, s,k):

        return model.P_s_k[s,k] == sum(model.fs_r[s,r] * model.ws_r_k[s,r,k] for r in model.R)

    model.ProcessPower = Constraint(model.S, model.K, rule=process_power)


    ####################################
    ########## w_srk
    
    ### >=0
    def fix_w00(model,s,r,k):
        
        return model.ws_r_k[s,r,k] >= 0
    model.fix_w_00 = Constraint(model.S, model.R, model.K, rule=fix_w00)

    ### >=1
    def fix_w01(model,s,r,k):
        
        return model.ws_r_k[s,r,k] <= 1
    model.fix_w_01 = Constraint(model.S, model.R, model.K, rule=fix_w01)


    ### Additional Variable for Testing 
    def check_w(model,s,k):
        #if k >0:
        return sum((model.ws_r_k[s,r,k] * value(r)) for r in model.R) == model.testv_r[s,k]

    model.CheckW = Constraint(model.S,model.K,rule=check_w)    



    ### Ensure sequence


    def ensure_sequence(model,s,r,k):
        if value(k)>0 and k <TN-1 and r<model.ds[s]-1: # and value(k) >= value(model.idxsp_s[s]) and value(k) <= value(model.idxsp_s[s])+model.ds[s]-1 and r<model.ds[s]-1:
    
            return model.ws_r_k[s,r+1,k+1] >= model.ws_r_k[s,r,k]
        else:
            return Constraint.Skip
    model.EnsureSequence = Constraint(model.S,model.R,model.K,rule=ensure_sequence)



    ### Ensure activation

    def fix_w1(model,s,r):
        return sum(model.ws_r_k[s,r,k] for k in model.K) ==1

    model.fix_w_1 = Constraint(model.S, model.R,rule=fix_w1)

    if False:
        ### Initiate loadprofile
        def fix_w3(model,s,k):
            if k<TN-model.ds[s]:
                return sum(model.ws_r_k[s,0,k] for k in model.K) >=1
            else:
                return Constraint.Skip
        #model.fix_w_3 = Constraint(model.S,model.K, rule=fix_w3)

    if False:
        def fix_w4(model,s):
            return sum(model.ws_r_k[s,r,k] for r in model.R for k in model.K) >=len(model.R)


    ### Fix Start
    def fix_w_start(model,s,r):
        
        return model.ws_r_k[s,r,0] ==0
    model.FixWStart = Constraint(model.S,model.R,rule=fix_w_start)

    ### Fix End
    def fix_w_end(model,s,r):
        
        return model.ws_r_k[s,r,TN-1] ==0
    model.FixWEnd = Constraint(model.S,model.R,rule=fix_w_end)
    

    ### Index of production start
    def production_idx(model,s):
        
        return model.idxsp_s[s] == sum(model.sp_s_k[s,k] * value(k)  for k in model.K)
        
    model.ProdIdx = Constraint(model.S, rule=production_idx)


    ### Limit of parallel processes
    def limit_parallel_processes(model,s,k):
        
        return sum( model.actp_s_k[s,k] for s in model.S ) <= model.limparallel
    
    model.ParallelLim = Constraint(model.S, model.K, rule=limit_parallel_processes)    





    
    return model












