
import numpy as np
import pandas as pd
import oathyps.tools import wetea




def power_specific_key_values(n_iterations=100, sig_column='P', P_max_we=1, efficiency_we_hhv=0.7):
    '''

    TODO: include we-instances
    '''

    ### Initialize data
    keys = ['scale',
                'sig_energy_available',
               'we_energy_utilized',
               'we_rated_power',
               'we_minimum_power',
               'we_time_of_operation',
               'we_full_load_hours',
               'we_time_in_full_load',
               'energy_in_hydrogen_produced',
               'mass_hydrogen_produced',
               'capex_of_plant',
               'opex_of_plant',
                'costs_stacks_we',
               'costs_electricity',
               'total_costs_plant_operation_we',
               'lcoh',
               'lifespan_stack_act',
               'number_of_stackreplacements',
               'costs_stackreplacement'
               ]

    capex_we_specific_annual = 0
    opex_we_specific = 0
    costs_stack_we_specific = 1
    lifetime_stack_we = 20

    dfs = df.sort_values(by=sig_column).copy()
    dfs = dfs.rename({sig_column:'P'})

    s = np.linspace(0, 1, n_iterations)  # 1000)#200)


    ### TODO: include dict in we-instance
    dct = {}
    for key in keys:
        dct[key] = np.zeros(len(n_iterations))

    ### Iterate through scaling
    for j,scl in enumerate(s):

        dfs['energy_available'] = dfs.P * dfs.tdelta
        dct['we_rated_power'][j] = P_in = P_max_we * scl

        dfs['P_we_plnt'] = np.where((dfs[sig_column] <= dfs.P, dfs.P, P_in)  # set possible values of plant power
        dfs.loc[dfs.P_plnt < P_min_we, 'P_plnt'] = 0  #

        dfs['cnt'] = np.where((dfs.P >= P_min_we), 1, 0)  # count only allowed values of power    (min)
        dfs['energy_utilized'] = (dfs.P_plnt * dfs.tdelta)  # theoretical utilized amount of energy @ time step

        dfs['t_operation_we'] = (dfs.cnt * dfs.tdelta)  # consider every period of time @ plant op


        ### produced amount of hydrogen

        ### Energy based
        if eff_fnct is None or not callable(eff_fnct):
            dfs['E_H2'] = dfs.P_plnt * dfs.tdelta * efficiency_we_hhv  # eff
        else:
            dfs['E_H2'] = dfs.P_plnt * dfs.tdelta * eff_fnct(dfs.P_plnt / Pmax_we)

        ### FLH
        dfs['cnt_flact'] = np.where((dfs.P >= P_in), 1, 0)
        dfs['t_flact'] = (dfs.cnt_flact * dfs.tdelta)

        ### calculate according/ achieved properties

        dct['sig_energy_available'][j] = dfs.energy_available.sum()
        dct['energy_utilized_we'][j] = dfs.energy_utilized.sum()  # calc theoretical utilized amount of energy // in kWh
        dct['rated_power_we'][j] = P_in  # rated plant power // in kW
        dct['time_of_operation_we'][j] = dfs.t_we_op.sum()  # resulting operation time // in h

        ###
        dct['energy_in_hydrogen_produced'][j] = dfs.E_H2.sum()
        dct['mass_hydrogen_produced'][j] = dct['energy_in_hydrogen_produced'][j] / e_HHV_h2

        dct['capex_of_plant_we'][j] = P_in * capex_spc_an  # 500/20 # 1431/20 # cpx_fun(P_in)
        dct['opex_of_plant_we'][j] = P_in * opex_spc_an  # 12.04
        dct['costs_electricity'][j] = E[j] * coe  # 8.29e-2 #3.94e-2 # Fraunh ISI 2021  ||| old: 95e-3 # €/kWh Posteeg
        dct['costs_stacks_we']c_st_bare[j] = CPX_plnt[j] * frc_stackreplacement  # 0.5

        ### operational time
        dct['we_full_load_hours'][j] = (dct['we_energy_utilized'][j] / P_in)  # resulting operation time // in h

        t_flact[j] = dfs.t_flact.sum()

        ### clc StackReplacement costs || taken from elteco
        # lt_st = 50e3 # Lifetime of stack // in h
        # lt_el = 20 # Lifetime of Plant // in a

        dct['lifespan_stack_act_we'][j] = (lifetime_stack / tdct['time_of_operation_we'][j])  # mat['t_op_el'])
        dct['number_of_stackreplacements'][j] = wetea.stackreplacement(cost_stack_bare,  # capital costs Stack
                                                                         nominal_power,  # Nominal Power of plant
                                                                         total_operation_time_we,  # total_operation_time_stack
                                                                         lifetime_stack, lifetime_we,
                                                                         offset_n_replacements=0,
                                                                         skip_clc=False,
                                                                         apply_old_method=False, debug=False,
                                                                                   return_specific=False)
        if np.isnan(lifespan_st_act[j]):
            lifespan_st_act[j] = 0
            dct['number_of_stackreplacements'][j] = 0
        else:
            dct['number_of_stackreplacements'][j] = math.ceil(lifetime_plnt / lifespan_st_act[
                j]) - 1  # number of additional stack(s) to be replaced (every n operation hours)

        k_strpl[j] = n_strpl[j] * c_st_bare[j] / lifetime_plnt

        ### total costs
        dct['total_costs_plant_operation_we'][j] = CPX_plnt[j] + OPX_plnt[j] + csts_E[j] + k_strpl[j]
        dct['lcoh'][j] = dct['total_costs_plant_operation_we'][j] / m_H2[j]

    #arr = np.zeros((len(columns),n_iter))
    #iter_df = pd.DataFrame(data=arr.T, columns=columns)

    #iter_df.loc[:,'scale'] = np.linspace(0,1,n_iter)
    #parr = np.zeros((len(df_iter),len(sig_df)))
    #parr[:] = sig_df['power']
    #np.where(parr)
    # np.meshgrid(iter_df.loc[:,'scale'], )[0] * np.meshgrid(a, b)[1]

    #iter_df.loc[:,'rated_power_we'] = P_we_max = iter_df.loc[:,'scale']
    #iter_df.loc[:,'we_minimum_power'] = frc_power_min * iter_df.loc[:,'we_rated_power']
    #iter_df[:,'P_act'] = np.where((sig_df['power_sig'] <= P_in), dfs.P, P_in)

    df_o = pd.DataFrame(dct)
    return df_o