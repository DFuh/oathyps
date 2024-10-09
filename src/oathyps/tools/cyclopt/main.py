#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  4 10:29:11 2024

@author: DFuh
"""
import os
import sys
import numpy as np
import pandas as pd
import glob
import matplotlib.pyplot as plt
from pyomo.environ import *
from pyomo.opt import SolverFactory

from oathyps.misc import helpers as hlp
from oathyps.misc import readfiles as rf
from oathyps.tools.cyclopt import indcyclop as ico, plotting as pplt

usage = """

Usage: python -m oathyps.tools.cyclopt.main [PATH_TO_INPUT_DIRECTORY [PATH_TO_OUTPUT_DIRECTORY]] 

"""

def default_setup(load_ones=False,price_ones=False):
    # loadprofile = np.array([0,0,0,10,12,9,0,0,0])*90
    # loadprofile = np.array([8,9,10,12,12,12,5,4,4])*90
    loadprofile = np.array([0,0,0,12,12,12,12,0,0])*90

    # Sets
    ls = 5 #1000#9#0
    TN = 30 #2000#8760
    
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
    
    

    
    return cyclopt.create_process_model(load_timeseries=fixed_load,
                                    price_timeseries=fixed_price,
                         number_of_eaf=2,timerange=30,
                         eaf_loadprofile=loadprofile,
                         target_power_level=1000)


def run_copt(pth_to_inputfiles=None, pth_to_outputfiles=None, solver_verbose=True):
    ### Add possibility of reading external files
    ### setup

    ### File output
    if pth_to_outputfiles != False:
        full_pth_outputfiles = hlp.mk_dir(pth_to_outputfiles,'out')
        logfile = os.path.join(full_pth_outputfiles,"cyclopt_solver.log")
        pth_figure=os.path.join(full_pth_outputfiles,"fig_cyclopt.pdf")
    else:
        logfile=None
        full_pth_outputfiles = None
        pth_figure = None

    if not pth_to_inputfiles:
        model = default_setup()
    else:
        flst = glob.glob(pth_to_inputfiles+'/*.json')
        if len(flst)>0:
            fl = flst[0]
        ### Read cyclopt input data
        parameters = rf.read_json_file(abspth_to_fl=fl)
        print('parameters: ', parameters)
        filename_data = parameters.get('filename_data',None)
        filename_loadprofile = parameters.get('filename_loadprofile', None)
        if filename_data:
            pth_to_df = os.path.join(pth_to_inputfiles,filename_data)
            df = pd.read_csv(pth_to_df)
            df = df[1000:2000]
            print('df: ', df.head())
            pth_to_loadprofile = os.path.join(pth_to_inputfiles, filename_loadprofile)
            df_loadprofile = pd.read_csv(pth_to_loadprofile)
            TN = len(df) if parameters.get('timerange',None) is None else parameters.get('timerange',None)

            loadprofile = df_loadprofile.cyclic_process.to_numpy()/1e3
            print('loadprofile: ', loadprofile)
            # loadprofile = parameters.get('loadprofile', np.array([0, 0, 0, 10, 10, 10, 10, 0, 0]))

            model = ico.create_process_model(load_timeseries=df['residualload'].to_numpy()/1e3+2e3,
                                 price_timeseries=np.ones(len(df['price_electricity']))*0+1,#.to_numpy()/1,
                                 number_of_processes=parameters.get('number_of_processes',None),
                                total_number_of_cycles=parameters.get('total_number_of_cycles',None),
                                             timerange=TN,
                                 loadprofile=loadprofile,
                                 target_power_level=parameters.get('P_target',{'val':0})['val'])

        else:
            print('Could not read file: ', filename_data)
    ### Solve
    opt = SolverFactory('gurobi')  # , solver_io="python")
    x = opt.solve(model, tee=solver_verbose,logfile=logfile)
    # log_infeasible_constraints(model)

    # model.display()

    # for i in x:
    #    print(f'{i}: {x[i]}')
    # # print(value(model.obj))

    pplt.plot_cyclopt_results(model,pth_out=pth_figure)
    return

    

    
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(usage)
        sys.exit(0)
    elif len(sys.argv) > 2:
        input_pth = sys.argv[1]
        output_pth = sys.argv[2]
    else:
        input_pth = sys.argv[1]
        output_pth = None


    run_copt(pth_to_inputfiles=input_pth,pth_to_outputfiles=output_pth)
    

    
