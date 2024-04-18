
import numpy as np
import pandas as pd


def power_specific_key_values(n_iter=100):
    '''

    '''

    columns = ['sig_energy_available',
               'we_energy_utilized',
               'we_rated_power',
               'we_time_of_operation',
               'we_full_load_hours',
               'we_time_in_full_load',
               'energy_in_hydrogen_produced',
               'mass_hydrogen_produced',
               'capex_of_plant',
               'opex_of_plant',
               'costs_electricity',
               'total_costs_',
               'lcoh',
               'lifespan_stack_act',
               'number_of_stackreplacements',
               'costs_stackreplacement'
               ]
    arr = np.zeros((len(columns),n_iter))
    iter_df = pd.DataFrame(data=arr.T, columns=columns)

    return iter_df