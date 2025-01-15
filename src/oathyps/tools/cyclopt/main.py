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
import pickle
from loguru import logger
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
    logger.info("Default model setup.")

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
    
    

    
    return ico.create_process_model(load_timeseries=fixed_load,
                                    price_timeseries=fixed_price,
                         number_of_processes=2,timerange=30,
                         loadprofile=loadprofile,
                         target_power_level=1000)


def extract_decision_data(model,pth_out=''):

    w = model.ws_r_k
    varname = w.name
    r = np.array(model.R.value)
    logger.info("Extract data for decision variable {}",w.name)
    # make a pd.Series from each
    s = pd.Series(w.extract_values(), index=w.extract_values().keys())
    #r = pd.Series(r.extract_values(), index=r.extract_values().keys())

    logger.trace('Index r: {r}')
    # if the series is multi-indexed we need to unstack it...
    if type(s.index[0]) == tuple:  # it is multi-indexed
        s = s.unstack(level=1)

    else:
        s = pd.DataFrame(s)  # force transition from Series -> df
    logger.trace("Index levels in variable: {}",s.index.nlevels)
    logger.trace("Column levels in variable: {}",s.columns.nlevels)

    if s.index.nlevels >1:
       for lvl in  range(s.index.nlevels):
        dfi = s.loc[0,:]
        dfi = dfi.mask(dfi <=0)
        if pth_out:
            filepath = pth_out.replace('data','df_'+varname+'_'+str(lvl)+'_')
            logger.info("Write file: {}",filepath)
            dfi.to_csv(filepath)
        #print('1: ',s.loc[1, :].plot())
    # multi-index the columns
    # s.columns = pd.MultiIndex.from_tuples([(k, t) for k,t in s.columns])

    #serieses.append(s)

    return

def mk_output_dataframes():
    w_dct = {k: v for (k, v) in zip(kl_w, l_w)}
    P_dct = {k: v for (k, v) in zip(kl_Psk, l_Psk)}
    dct_out = {'index': idx,

               'P_price': P_price,
               'P_fix': P_fix,
               'P_diff': P_diff,
               'P_res': P_res,
               'sp0': sp_idx0,
               'sp1': sp_idx1,
               'ep0': ep_idx0,
               'ep1': ep_idx1,
               'x0': act_idx0,
               'x1': act_idx1
               }

    P_dct.update({'idx': idx})
    w_dct.update({'w_idx': x})
    pd.DataFrame.from_dict(dct_out).to_csv(pth_out.replace('fig', 'data').replace('.pdf', '.csv'))
    pd.DataFrame.from_dict(w_dct).fillna(-99).to_csv(pth_out.replace('fig', 'w_data').replace('.pdf', '.csv'))
    pd.DataFrame.from_dict(P_dct).to_csv(pth_out.replace('fig', 'P_data').replace('.pdf', '.csv'))

    return

def extract_data(modelvariable,pth_out=''):

    logger.info("Generate model output for attribute: {}",modelvariable.name)
    # make a pd.Series from each
    s = pd.Series(modelvariable.extract_values(), index=modelvariable.extract_values().keys())

    # if the series is multi-indexed we need to unstack it...
    if type(s.index[0]) == tuple:  # it is multi-indexed
        s = s.unstack(level=1)
        #print(s)
    else:
        s = pd.DataFrame(s)  # force transition from Series -> df
    logger.trace("Index levels in variable: {}",s.index.nlevels)
    logger.trace("Column levels in variable: {}",s.columns.nlevels)

    if s.index.nlevels >1:
       data = {}
       for lvl in  range(s.index.nlevels):
           dfi = s.loc[lvl,:]
           dfi = dfi.mask(dfi <=0)
           if pth_out:
               filepath = pth_out.replace('data','df_'+modelvariable.name+'_'+str(lvl)+'_')
               logger.info("Write {} data to file: \n {}",modelvariable.name,filepath)
               dfi.to_csv(filepath)
           data['df_'+modelvariable.name+'_'+str(lvl)] = dfi
    else:
        if pth_out:
            filepath = pth_out.replace('data','df_'+modelvariable.name+'_')
            logger.info('Write {} data to file: \n {}',modelvariable.name,filepath)
            s.to_csv(filepath)
        data = s

        #print('1: ',s.loc[1, :].plot())
    # multi-index the columns
    # s.columns = pd.MultiIndex.from_tuples([(k, t) for k,t in s.columns])

    #serieses.append(s)

    return data

def extract_and_store_data(model, pth_data, lst_data=[]):
    logger.info("Extract and store data")

    for varnm in lst_data:
        var = getattr(model, varnm, None)
        if var is not None:
            extract_data(var, pth_out=pth_data)
        else:
            logger.info("Could not extract: {}", varnm)
    return

def run_copt(pth_to_inputfiles=None, pth_to_outputfiles=None, solver_verbose=True):
    ### Add possibility of reading external files
    ### setup

    ### Read parameters
    logger.info("Read parameters")
    flst = glob.glob(pth_to_inputfiles + '/*.json')
    if len(flst) > 0:
        parameters = rf.read_json_file(abspth_to_fl=flst[0])
        logger.info("Use parameters: {}",flst[0])
    else:
        parameters = None

    logger.debug("Parameters: {}",parameters)





    ### File output
    logger.info("Initialize file output.")
    if pth_to_outputfiles != False:
        full_pth_outputfiles = hlp.mk_dir(pth_to_outputfiles,'out')
        logfile = os.path.join(full_pth_outputfiles, "cyclopt.log")
        logfile_solver = os.path.join(full_pth_outputfiles,"cyclopt_solver.log")
        pth_figure=os.path.join(full_pth_outputfiles,"fig_cyclopt.pdf")
        pth_data = os.path.join(full_pth_outputfiles,"data_cyclopt.csv")
        lpfile = os.path.join(full_pth_outputfiles, "lp_file.lp")
    else:
        logfile = None
        logfile_solver=None
        full_pth_outputfiles = None
        pth_figure = None
    logger.add(logfile)
    logger.info("Setup cyclic process optimization.")
    if parameters is None:
        model = default_setup()
        parameters = {}
    else:
        filename_data = parameters.get('filename_data',None)
        filename_loadprofile = parameters.get('filename_loadprofile', None)
        if filename_data:
            pth_to_df = os.path.join(pth_to_inputfiles,filename_data)
            df = pd.read_csv(pth_to_df)
            slc0 = parameters.get('slice_df_start',0)
            slc1 = parameters.get('slice_df_end',len(df))
            logger.info("Slice df: Start = {} || End = {}",slc0,slc1)
            df = df[slc0:slc1] #[2000:2300]
            logger.debug('df (head): {}', df.head())

            fctr_price_electricity = parameters.get('factor_price_electricity',1)
            offset_price_electricity = parameters.get('offset_price_electricity', 0)
            timeseries_price_electricity = df['price_electricity'].to_numpy() * fctr_price_electricity + offset_price_electricity

            fctr_residualload = parameters.get('factor_residualload', 1)
            offset_residualload = parameters.get('offset_residualload', 0)
            timeseries_residualload = df['residualload'].to_numpy() * fctr_residualload + offset_residualload

            p_target = parameters.get('P_target',0)
            if not type(p_target) in (int,float):
                logger.info('Use mean value of input-timeseries as power-target')
                p_target = timeseries_residualload.mean()
            logger.info('power-target = {}',p_target)

            pth_to_loadprofile = os.path.join(pth_to_inputfiles, filename_loadprofile)
            df_loadprofile = pd.read_csv(pth_to_loadprofile)
            TN = len(df) if parameters.get('timerange',None) is None else parameters.get('timerange',None)
            slc_lop_0 = parameters.get('slice_loadprofile_start', 0)
            slc_lop_1 = parameters.get('slice_loadprofile_end', len(df_loadprofile))
            slc_lop_1  = min(len(df_loadprofile),slc_lop_1)
            logger.info("Slice loadprofile: Start = {} End = {}",slc_lop_0,slc_lop_1)
            loadprofile = df_loadprofile[slc_lop_0:slc_lop_1].cyclic_process.to_numpy()/1e3

            logger.info("Create model.")
            if parameters.get("simple_model",False):
                create_model =  ico.create_simple_process_model
            else:
                create_model = ico.create_process_model

            solver = parameters.get('solver', 'cbc')
            if (solver == 'gurobi') and parameters.get("quadratic_powerdev",False):
                quadratic_objf = True
            else:
                quadratic_objf = False

            model = create_model(load_timeseries=timeseries_residualload,
                                 price_timeseries=timeseries_price_electricity,
                                 number_of_processes=parameters.get('number_of_processes',None),
                                 total_number_of_cycles=parameters.get('total_number_of_cycles',None),
                                 timerange=TN,
                                 loadprofile=loadprofile,
                                 target_power_level=p_target,
                                 enable_obj_powerdeviation=parameters.get("enable_obj_powerdeviation",1),
                                 enable_obj_surcharges=parameters.get("enable_obj_surcharges",0),
                                 quadratic_powerdev=quadratic_objf,
                                 test=True)

        else:
            logger.info("Could not read file: {}",filename_data)
            model = None



    ### Solve
    if model is not None:

        if parameters.get('write_lp_file', False):
            logger.info("Write lp-file.")
            model.write(lpfile,io_options={'symbolic_solver_labels': True})
        ###


        if not parameters.get('do_not_solve', False):


            logger.info("Initialize solver: {}",solver)

            opt = SolverFactory(solver,)
            #opt.options['slog'] = 1
            #opt.options['MIPGap'] = 1
            #opt.options['TimeLimit'] = 600
            #opt.Params.MIPGap = 0.1
            #opt.setParam('MIPGap', 0.1)
            #opt.setParam('Timelimit', 30)
            #opt.setParam('OptimalityTol',6e-1)
            #opt.options['OptimalityTol'] = 0.01

            #opt.options['IterationLimit'] = 400e3
            #solver.options['max_iter'] = 40e3
            logger.info("Start solving model")
            x = opt.solve(model, tee=solver_verbose,logfile=logfile_solver, )
            # log_infeasible_constraints(model)

            # model.display()

            # for i in x:
            #    print(f'{i}: {x[i]}')
            # # print(value(model.obj))
            if not parameters.get('simple_model',False):
                extract_decision_data(model,pth_out=pth_data)
                pplt.plot_cyclopt_results(model, pth_out=pth_figure, printvals=True)

            ### Save data
            extract_and_store_data(model,
                                   pth_data,
                                   parameters.get('extract_data',[])
                                   )

            # extract_data(model.ws_r_k, pth_out=pth_data)
            # print('ws_r_k: ', model.ws_r_k[0,0,:].extract_values())

        if parameters.get('pickle_model',False):
            pickle.dumps(model)


    else:
        logger.info(" -- Abort optimization")

    logger.info(" - End - ")
    return model

    

    
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

    logger.info("Run cyclopt main")
    run_copt(pth_to_inputfiles=input_pth,pth_to_outputfiles=output_pth)
    

    
