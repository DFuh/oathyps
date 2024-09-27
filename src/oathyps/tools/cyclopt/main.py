#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  4 10:29:11 2024

@author: dafu_res
"""
import numpy as np
import matplotlib.pyplot as plt 
from pyomo.environ import *
from pyomo.opt import SolverFactory
from pyomo.util.infeasible import log_infeasible_constraints

import plotting_eaf_opt as pplt
import cmpl_eaf_scheduling_pyomo_model as cmplmod






def model_setup(load_ones=False,price_ones=False):
    # loadprofile = np.array([0,0,0,10,12,9,0,0,0])*90
    # loadprofile = np.array([8,9,10,12,12,12,5,4,4])*90
    loadprofile = np.array([0,0,0,12,12,12,12,0,0])*90

    # Sets
    ls = 5 #1000#9#0
    TN = 40 #2000#8760
    
    randomarr = np.array([0.06377479, 0.89821124, 0.53202501, 0.65797417, 0.59679081,
           0.5979558 , 0.50484718, 0.60746121, 0.08740392, 0.88140759,
           0.4640891 , 0.24153676, 0.88385653, 0.60720857, 0.67206298,
           0.31144279, 0.22920587, 0.19679191, 0.96458801, 0.49686338,
           0.85786756, 0.59390205, 0.7299656 , 0.08557479, 0.17888485,
           0.46621239, 0.54625578, 0.33585135, 0.8400578 , 0.36893637])

    if load_ones:
        randomarr = np.ones(TN)
    fixed_load = randomarr * 800 #np.random.random(l)*800
    fixed_load[int(TN*1/3):int(TN*2/3)] = fixed_load[int(TN*1/3):int(TN*2/3)]*1
    #fixed_load[:int(l*1/3)] = fixed_load[:int(l*1/3)]*2
    #fixed_load[int(l*2/3):] = fixed_load[int(l*2/3):]*2 

    randomarr2 = np.array([0.47084758, 0.67351803, 0.26481586, 0.06419481, 0.13716286,
           0.02875246, 0.1905407 , 0.99337754, 0.97630424, 0.55034975,
           0.43569003, 0.57391175, 0.44695175, 0.32031519, 0.8878972 ,
           0.6716083 , 0.05499064, 0.39889085, 0.40539432, 0.78259963,
           0.5703822 , 0.2805261 , 0.10835486, 0.36896552, 0.95492279,
           0.30387697, 0.23798274, 0.07862252, 0.366868  , 0.2073201 ])
    fixed_price = randomarr2*10 #np.random.random(model.K.__len__())*10
    #fixed_price[0:10] = fixed_price[0:10]+40
    # fixed_price[20:] = fixed_price[20:]+40
    fixed_price[10:20] = fixed_price[10:20]+40
    if price_ones:
        fixed_price = np.ones(TN)#fixed_price * 0
    
    

    
    return cmplmod.create_eaf_model(load_timeseries=fixed_load, 
                                    price_timeseries=fixed_price,
                         number_of_eaf=2,timerange=30,
                         eaf_loadprofile=loadprofile,
                         target_power_level=1000)


def main(solver_verbose=True):
    
    ### Add possibility of reading external files
    
    ### setup
    model = model_setup()
    
    ### Solve
    opt = SolverFactory('cbc')#, solver_io="python")
    x = opt.solve(model,tee=solver_verbose)
    # log_infeasible_constraints(model)
    
    # model.display()
    
    
    #for i in x:
    #    print(f'{i}: {x[i]}')
    # # print(value(model.obj))
    
    pplt.plot_eaf_opt(model)
    return

    

    
if __name__ == '__main__':


    main()
    

    
