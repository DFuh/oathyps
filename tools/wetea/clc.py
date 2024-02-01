#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 29 08:13:17 2024

@author: DFuh
"""
def clc_annuity_factor(interestrate, lifetime):
    '''
    Calculate the annuity factor

    Parameters
    ----------
    interestrate : FLOAT
        Theoretical interest rate for given investment in $\%/100$.
    lifetime_we : INT
        Lifetime of plant or system in years.

    Returns
    -------
    annuity factor .

    '''

    return  (interestrate * (interestrate + 1)**lifetime ) /
            ( ( ( interestrate + 1 )**lifetime ) - 1 )


def capitalcosts(nominal_power, annuity_factor, capex_specific_tot):
    '''
    Clc yearly (total) capital expenditures of plant

    Parameters
    ----------
    nominal_power : FLOAT
        Nominal power of plant in kW.
    annuity_factor : FLOAT
        .
    capex_specific_tot : FLOAT
        Specific capex in €/kW.

    Returns
    -------
    Total yearly capex of plant.

    '''
    return nominal_power * annuity_factor * capex_specific_tot# capex_costs // in €/a



def total_costs_electricity(logger=None, electrical_energy_utilized_dc=0, electrical_energy_utilized_ac=0,
                     electrical_energy_utilized_tot=0,
                    surcharges_spc_dc=0, surcharges_spc_ac=0,
                           electricity_costs_from_simu=False,
                    ce_from_simu=0, exclude_first_gwh=False):

    if electrical_energy_utilized_tot > 0 and electrical_energy_utilized_AC == 0:
        w_el_ac = electrical_energy_utilized_tot
    else:
        w_el_ac = electrical_energy_utilized_ac

    if electrical_energy_utilized_dc > 0:
        w_el_ac = w_el_ac - electrical_energy_utilized_dc


    surcharges_dc, surcharges_ac = surcharges(w_el_dc, w_el_ac, surcharges_spc_dc, surcharges_spc_ac,
                                              surcharges_1gwh_spc_dc=0, surcharges_1gwh_spc_ac=0)

    if electricity_costs_from_simu and ce_from_simu != 0:  # and self.CE_agora:
        if logger is not None:
            logger.info(' --- Use (CE) data from simu (agora) --- ')
        c_elec = ce_from_simu
        c_elec_incl = ce_from_simu + surcharges_ac + surcharges_dc
        if c_elec == c_elec_incl:
            if logger is not None:
                logger.warning('Identical values for electricity costs w/o surcharges '))

    else:
        c_elec_dc, c_elec_ac = electricitycosts(electrical_energy_utilized_dc, electrical_energy_utilized_ac,
                         electrical_energy_utilized_tot, electricity_costs_from_simu=False, exclude_first_gwh=False)

    return

def costs_electricity(utilized_electrical_energy, electricity_costs_spc):

    return utilized_electrical_energy * electricity_costs_spc

def costs_surcharges(w_el_dc, w_el_ac, surcharges_spc_dc, surcharges_spc_ac, surcharges_1gwh_spc_dc=0, surcharges_1gwh_spc_ac=0):
    '''
    Read/Calc surcharges in €/kWh

    '''
    if surcharges_1gwh_spc_dc >0:
        surcharges_1gwh_dc = (surcharges_1gwh_spc_dc * 1e6)
    else:
        surcharges_1gwh_dc = 0

    if surcharges_1gwh_spc_ac >0:
        surcharges_1gwh_ac = (surcharges_1gwh_spc_ac * 1e6)
    else:
        surcharges_1gwh_ac =
    c_surch_dc = surcharges_1gwh_dc + surcharges_spc_dc * w_el_dc
    c_surch_ac =  surcharges_1gwh_ac + surcharges_spc_ac * w_el_ac

    return c_surch_dc, c_surch_ac

def stackreplacement(self, cost_stack_bare, # capital costs Stack
                            nominal_power,  # Nominal Power of plant
                            total_operation_time_we, #total_operation_time_stack
                            lifetime_stack, lifetime_we,
                            offset_n_replacements=0,
                            skip_clc=False,
                            apply_old_method=False, debug=False):
    ### stack replacement

    if skip_clc:
        n_strpl = 0
    else:

        if apply_old_method:
            n_strpl = math.ceil(((t_op_st_tot / self.n_yrs) * lifetime_we) / l
                                    ifetime_stack) -1 # Number of events of stackreplacement


        else:
            ''' new method taking into account replacement every n years and 1 existing stack (in CAPEX)'''

            effective_lifespan_st = (lifetime_stack / total_operation_time_we ) #mat['t_op_el'])
            if np.isnan(effective_lifespan_St):
                effective_lifespan_St = 0
                n_strpl = 0
            else:
                n_strpl = math.ceil(lifetime_we / effective_lifespan_St) -1# number of additional stack(s) to be replaced (every n operation hours)

    k_strpl_spc = n_strpl+offset_n_replacements * cost_stack_bare / lifetime_we  # // in €/Stack * Stacks / operation_time

    k_strpl = k_strpl_spc * nominal_power


    if debug:
        print('tec: ', self.tec)
        print('lt_st || t_op || lt_el', lifetime_stack,'||',
                total_operation_time_we,'||', lifetime_we)
        print('bare_Stack_Costs: ', self.cost_stack_bare
        print('effective lifespan: ', self.effective_lifespan_St)
        print('self.n_strpl: ', self.n_strpl)
        print('k_strpl_spc: ', self.k_strpl_spc)
        print('k_strpl: ', self.k_strpl)

    return k_strpl, k_strpl_spc

def costs_maintenancec(maintenance_costs_spc, nominal_power_we):
    return maintenance_costs_spc * nominal_power_we

def costs_taxes_and_insurances(tax_and_ins_frc, total_capex):
    return tax_and_ins_frc * total_capex

def costs_labor(num_supervisor_per_plant, time_for_plant_suvervision, hourly_labor_costs):
    return num_supervisor_per_plant * time_for_plant_suvervision * hourly_labor_costs

def costs_water(price_water_spc_gravimetric, mass_consumed_water):
    return price_water_spc_gravimetric * mass_consumed_water

def revenues_oxygen(price_oxygen_spc_gravimetric, mass_oxygen):
    return abs(price_oxygen_gravimetric) * mass_oxygen