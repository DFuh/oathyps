import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from oathyps.tools.wetea import clc as tea
from oathyps.misc import readfiles as rf

def find_nearest(array, value):
    array = np.array(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]

def plot_popt(df, plt_dct, anno_key='full_load_hours_we', anno_val=5000,
              key_x='rated_power_we', scale_x=1e-6, unit_x='GW', no_labels=True):
    plt_keys = list(plt_dct.keys())

    ### Annotations

    fig, axes = plt.subplots(len(plt_keys), sharex=True)

    if no_labels:
        prfx_lbl = '_'
    else:
        prfx_lbl = ''

    x_val = df[key_x]
    for i, ax in enumerate(axes):
        key = plt_keys[i]
        y_scl = plt_dct[key]['scl']
        y_val = df[key] * y_scl

        ax.plot(x_val * scale_x, y_val, label=prfx_lbl + key)

        anno_val_exact = find_nearest(df[anno_key],anno_val)
        if hasattr(anno_val_exact,'len'):
            if len(anno_val_exact) >1:
                anno_val_exact[0]
        anno_x_val = df[df[anno_key] == anno_val_exact][key_x].to_numpy()[0] * scale_x
        anno_x = [0, anno_x_val,anno_x_val]
        anno_y_val = df[df[anno_key] == anno_val_exact][key].to_numpy()[0] * y_scl
        anno_y = [anno_y_val, anno_y_val,0]
        ax.plot(anno_x, anno_y, linestyle='--', color='orangered')
        ax.scatter(anno_x[1], anno_y[1], color='orangered', marker='x')

        if not no_labels:
            ax.legend()
        ax.grid()
        ax.set_ylabel(plt_dct[key]['label'] + plt_dct[key]['unit'])
        ax.set_ylim(plt_dct[key]['limits'])
    ax.set_xlabel('Nominal elecrical power of water-electrolyzer in ' + unit_x)
    plt.tight_layout()

    plt.show()
    return fig

class WE():

    def __init__(self,):
        pass

    def efficiency(self,x, a1, B1, k1, a2, B2, k2):
            return B1 * np.log(x + 1) / np.exp(a1 * x ** k1) + B2 * np.log(x + 1) / np.exp(a2 * x ** k2)

def power_specific_key_values(df,we_obj=None, n_iterations=100, sig_column='P', P_we_max=1, frc_P_we_min=0.1,
                                P_sig_max=1,
                              efficiency_we_hhv=0.7, par_eff_we=None, e_spc_h2=39.4,
                              capex_we_specific=0, opex_we_specific = 0, costs_stack_we_specific = 1,
                              costs_electricity_spc = 60,
                              lifetime_stack_we = 50000,  # h
                              lifetime_plnt_we = 20,  # a
                              interestrate=0.05
                                ):
    '''

    TODO: add docstring and comments
    TODO: include we-instances
    '''

    ### Initialize data
    keys = ['scale',
                'sig_energy_available',
               'energy_utilized_we',
               'rated_power_we',
               'minimum_power_we',
               'time_of_operation_we',
               'full_load_hours_we',
               'time_in_full_load_we',
               'energy_in_hydrogen_produced',
               'mass_hydrogen_produced',
               'capex_of_plant_we',
               'opex_of_plant_we',
                'costs_stacks_we',
               'costs_electricity',
               'total_costs_plant_operation_we',
               'lcoh',
               'lifespan_stack_act',
               'number_of_stackreplacements',
               'costs_stackreplacement_we',
            'costs_electricity_sig'
               ]





    dfs = df.sort_values(by=sig_column).copy()
    dfs = dfs.rename({sig_column:'P'})
    ### Normalize and scale
    dfs['P'] = dfs.P/dfs.P.max() * P_sig_max
    s = np.linspace(0, 1, n_iterations)  # 1000)#200)


    ### TODO: include dict in we-instance
    dct = {}
    for key in keys:
        dct[key] = np.zeros(n_iterations)

    ### Iterate through scaling
    for j,scl in enumerate(s):

        dfs['energy_available'] = dfs.P * dfs.tdelta
        dct['rated_power_we'][j] = P_in = P_we_max * scl
        P_we_min = P_we_max * scl *frc_P_we_min
        dfs['P_we'] = np.where(dfs.P <= P_in, dfs.P, P_in)  # set possible values of plant power
        dfs.loc[dfs.P_we < P_we_min, 'P_we'] = 0  #

        dfs['cnt'] = np.where((dfs.P >= P_we_min), 1, 0)  # count only allowed values of power    (min)
        dfs['energy_utilized'] = (dfs.P_we * dfs.tdelta)  # theoretical utilized amount of energy @ time step

        dfs['t_operation_we'] = (dfs.cnt * dfs.tdelta)  # consider every period of time @ plant op


        ### produced amount of hydrogen

        ### Energy based
        if we_obj is None or par_eff_we is None:
            dfs['E_H2'] = dfs.P_we * dfs.tdelta * efficiency_we_hhv  # eff
        else:
            dfs['E_H2'] = dfs.P_we * dfs.tdelta * we_obj.efficiency(dfs.P_we / P_we_max, *par_eff_we)

        ### FLH
        dfs['cnt_flact'] = np.where((dfs.P >= P_in), 1, 0)
        dfs['t_flact'] = (dfs.cnt_flact * dfs.tdelta)

        ### calculate according/ achieved properties

        dct['sig_energy_available'][j] = dfs.energy_available.sum()
        dct['energy_utilized_we'][j] = dfs.energy_utilized.sum()  # calc theoretical utilized amount of energy // in kWh
        dct['rated_power_we'][j] = P_in  # rated plant power // in kW
        dct['time_of_operation_we'][j] = dfs.t_operation_we.sum()  # resulting operation time // in h

        ###
        dct['energy_in_hydrogen_produced'][j] = dfs.E_H2.sum()
        dct['mass_hydrogen_produced'][j] = dct['energy_in_hydrogen_produced'][j] / e_spc_h2

        dct['capex_of_plant_we'][j] = P_in * capex_we_specific * tea.annuity_factor(interestrate, lifetime_plnt_we)
        dct['opex_of_plant_we'][j] = P_in * opex_we_specific
        dct['costs_electricity'][j] = dct['energy_utilized_we'][j] * costs_electricity_spc
        dct['costs_electricity_sig'][j] = dct['sig_energy_available'][j] * costs_electricity_spc


        ### operational time
        if dct['energy_utilized_we'][j] >0:
            dct['full_load_hours_we'][j] = (dct['energy_utilized_we'][j] / P_in)  # resulting operation time // in h
        else:
            dct['full_load_hours_we'][j] = 0

        ### clc StackReplacement costs || taken from elteco
        dct['costs_stackreplacement_we'][j] = tea.stackreplacement(costs_stack_we_specific,  # capital costs Stack
                                                                         P_in,  # Nominal Power of plant
                                                                         dct['time_of_operation_we'][j],  # total_operation_time_stack
                                                                         lifetime_stack_we,
                                                                        lifetime_plnt_we,
                                                                         offset_n_replacements=0,
                                                                         skip_clc=False,
                                                                         apply_old_method=False, debug=False,
                                                                                   return_specific=False)


        ### total costs
        dct['total_costs_plant_operation_we'][j] = (dct['capex_of_plant_we'][j]
                                                    + dct['opex_of_plant_we'][j]
                                                    + dct['costs_electricity'][j]
                                                    + dct['costs_stackreplacement_we'][j]
                                                    )
        if dct['total_costs_plant_operation_we'][j] > 0:
            dct['lcoh'][j] = dct['total_costs_plant_operation_we'][j] / dct['mass_hydrogen_produced'][j]
        else:
            dct['lcoh'][j] = np.nan
    df_o = pd.DataFrame(dct)
    return df_o


if __name__ == '__main__':

    parameters_eff_we = (10, 1, 1e-1, 30, 200, 1e-2)
    we = WE()

    pth_to_dir = input('Please enter path to file (directory)')
    flnm_df_in = input('Please enter filename')
    pth_out = input('Please enter output directory')
    fl = os.path.join(pth_to_dir, flnm_df_in)
    df_in = pd.read_csv(fl)
    df_in['Date'] = pd.to_datetime(df_in.Date)
    df_in = df_in.rename(columns={'P_wp': 'P'})

    df_in = df_in[['Date', 'P']]
    if False:
        ddata = np.zeros((5, 2))
        dt_idx = pd.date_range('2019-01-01 00:00:00', periods=len(ddata), freq='10m')
        df_in = pd.DataFrame(data=ddata, columns=['Date', 'P'])

        df_in['Date'] = dt_idx

    print('columns: ', df_in.columns)
    df_in['tdelta'] = (df_in['Date'].diff().dt.seconds.div(3600, fill_value=0))
    df_ret = power_specific_key_values(df_in, we, n_iterations=100,
                                           sig_column='P', P_we_max=1500e3,
                                           P_sig_max=2e6,
                                           frc_P_we_min=0.005,
                                           efficiency_we_hhv=0.75,
                                           par_eff_we=None, e_spc_h2=39.4,
                                           capex_we_specific=500/20, opex_we_specific=12,
                                           costs_stack_we_specific=0.5 * 500,
                                           costs_electricity_spc=60e-3,  # €/kWh
                                           lifetime_stack_we=50000,  # h
                                           lifetime_plnt_we=20  # a
                                           )

    plt_dct = {
        'energy_utilized_we': {'scl': 1e-9, 'unit': 'TWh', 'label': 'Utilized energy \n in \n ', 'limits': [0, 10]},
        'full_load_hours_we': {'scl': 1, 'unit': 'h', 'label': 'Full Load\n Hours in \n ', 'limits': [0, 8700]},
        'mass_hydrogen_produced': {'scl': 1e-6, 'unit': 'kt', 'label': 'Produced amount \n of hydrogen \n in \n ',
                                   'limits': [0, 150]},
        'lcoh': {'scl': 1, 'unit': '€/kg', 'label': 'LCOH \n in \n ', 'limits': [0, 10]}}
    fig = plot_popt(df_ret, plt_dct)
    if False:
        parameters_eff_we = (10,1,1e-1,30,200,1e-2)
        we = WE()
        ddata = np.zeros((5, 2))
        dt_idx = pd.date_range('2019-01-01 00:00:00', periods=len(ddata), freq='10m')
        df_in = pd.DataFrame(data=ddata, columns=['Date','P'])
        df_in['Date'] = dt_idx
        df_in['tdelta'] = (df_in['Date'].diff().dt.seconds.div(3600, fill_value=0))
        df_ret = power_specific_key_values(df_in,we,n_iterations=100, sig_column='P', P_we_max=1, frc_P_we_min=0.1,
                                           efficiency_we_hhv=0.7, par_eff_we=parameters_eff_we)
        cwd = os.getcwd()
        print('cwd: ', cwd)
        if input('Save testfile [y/n] ?') == 'y':
            df_ret.to_csv(cwd+'/testdf_popt.csv')
        print(' --finish --')