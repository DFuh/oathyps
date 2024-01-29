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
