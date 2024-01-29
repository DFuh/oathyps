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
