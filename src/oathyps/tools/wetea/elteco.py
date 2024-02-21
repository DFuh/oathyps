# -*- coding: utf-8 -*-
"""
Main Class for TEA

@author: David Fuhrländer
"""
import os
import json
import numpy as np
import pandas as pd
from oathyps.misc import helpers
from oathyps.tools.wetea import clc


#TODO: make ouput of data/ file status

class elTeco():
    """main class elEco."""

    def __init__(self, pth_to_dir_parameters=None, pth_to_file_inputdata=None,
                pth_to_dir_outputfile=None,
                flnm_matbal='', addkey_flnm_teares='',
                debug=False, slct_par_version=True):

        self.timestamp = helpers.timestamp(how='ISO')
        self.name = 'elEco'

        self.logger, self.logger_nm = helpers.ini_logging(self)
        self.logger.info('Ini logging: {}'.format(self.logger_nm))
        self.debug = debug
        if self.debug:
            self.logger.info('Setup in debug mode')

        self.addkey_flnm_teares=addkey_flnm_teares

        self.pth_to_dir_parameters = pth_to_dir_parameters
        self.pth_to_file_inputdata = pth_to_file_inputdata
        self.pth_to_dir_outputfile = pth_to_dir_outputfile


        self.parameters_in, self.parameters_flat  = self.read_parameters(
                                pth_to_dir_parameters,
                                debug=debug, skip=False) # read parameters, return dict
        self.materialbalance = self.read_materialbalance()

        #self.tea_instances = self.setup_tea()


    def read_parameters(self, pth_to_parameters, debug=False, skip=False):

        '''
        read parameter files and return full dict or None
        '''
        # TODO: check existence of mandatory parameters
        # TODO: make path-to-parameters an input-variable

        parameters = {}
        parameters_flat = {}
        lst_par_sets = ['static',
                        'basic',
                    'electricity_costs',
                    'electricity_surcharges',
                    'acquisition_PEM',
                    'acquisition_AEL',
                    'teco_AEL',
                    'teco_PEM',
                    'teco_storage',]

        if pth_to_parameters is not None:
            parameters_in = {}
            for par_set in lst_par_sets:

                if debug:
                    self.logger.info('Read Parameter Set: %s', par_set)
                    suffix = '.json' #'_debug.json'
                else:
                    suffix = '.json'


                jsonpth = os.path.join(pth_to_parameters, 'parameters_' + par_set + suffix)

                if not os.path.exists(jsonpth):
                    self.logger.info('Parameter-Set not found: %s', jsonpth)
                    skip = True
                if not skip:
                    with open(jsonpth) as jsonfile:
                        data=json.load(jsonfile)

                        parameters_in[par_set] = data
                        parameters_flat.update(data)
        else:
            self.logger.info('Could not read parameters (no path specified)')
            parameters_in = None
            parameters_flat = None

        return parameters_in, parameters_flat


    def read_materialbalance(self,):
        '''
        '''
        ### Read data
        df = None
        if (self.pth_to_file_inputdata is not None) and os.path.exists(self.pth_to_file_inputdata):
            self.logger.info('Read external Scenario-Data: %s', self.pth_to_file_inputdata)
            try:
                if '.csv' in self.pth_to_file_inputdata:
                    df = pd.read_csv(self.pth_to_file_inputdata)
                elif '.xls' in self.pth_to_file_inputdata:
                    df = pd.read_excel(self.pth_to_file_inputdata)
                else:
                    df = None
            except:
                df = None

        if df is None:
            self.logger.info('Could not read external Scenario-Data')

        return df


    def prepare_simufiles(self):
        '''
        Setup tea for simulation results (from EpoS)
        '''
        if True:
            self.inFls = hf.handleInputFiles(self.parameters.dct,
                                            pth_data_loc=self.pth_data_loc)
            # print('Props: ', self.inFls.dct_props)
        if True:
            self.instances = self.make_simu_instances()
        return


    def setup_tea(self, materialbalance_external=None, external_scenario=False,
                enable_CE=False):
        '''
        Setup tea for external scenario(s)
        '''

        if materialbalance_external is None:
            materialbalance = self.materialbalance
        else:
            materialbalance = materialbalance_external

        print('mb: ', materialbalance)
        if materialbalance is not None:

            instances = []
            for num,(idx,row) in enumerate(materialbalance.iterrows()):
                if self.debug:
                    self.logger.info('[%s]-----> idx=%s, data=%s', num, idx, row)
                    self.logger.info('df.name =  %s, %s', row['name'], type(row['name']))
                instances.append(TeaScenario(row['name'],
                                        logger=self.logger,
                                        external_scenario=external_scenario,
                                        parameters=self.parameters_in,
                                        parameters_flat=self.parameters_flat,
                                        data_materialbalance=row.to_dict(),
                                        #enable_CE=enable_CE,
                                        # pth_output=self.pth_to_dir_outputfile,
                                        debug=self.debug
                                        ))
        self.instances = instances
        return instances

    def run_tea(self):
        for scenario in self.instances:
            for year,we in scenario.we_instances.items():
                we.clc_total_costs()
                we.clc_lcohydrogen()
        return

    def short_results(self):
        for scenario in self.instances:
            for year,we in scenario.we_instances.items():
                #print(f'{year} | {scenario.name} | {we.name} | lcoh2: {we.lcoh2} ')
                print('{:>6} | {:>12} | {:>14} | lcoh2: {:>6}'.format(year,scenario.name,we.name, we.lcoh2))
        return

class TeaScenario():
    '''
    TEA-scenario class
    creates an instance for every simulation including multiple years,
    or
    for multiple external scenarios
    '''

    def __init__(self, name, logger=None, external_scenario=False, parameters=None, parameters_flat=None,
                    data_materialbalance=None, include_all_costs=False, tag='notag', debug=False):

        ### Basics
        self.debug = debug
        self.timestamp = helpers.timestamp(how='ISO')
        self.name = name
        self.ext_scenario = external_scenario
        self.tag = tag
        self.parameters = parameters
        self.translation = self.parameters['static']['translate']
        self.parameters_flat = parameters_flat

        self.include_all_costs = include_all_costs

        ## Ini Logging
        if logger is None:
            self.logger, self.lggrnm = helpers.ini_logging(self, name=name, pth=logpth)
        self.logger = logger
        self.logger.info('Ini External Scenario: %s', name)



        ### Ini materialbalance
        materialbalance={}
        if data_materialbalance is not None:
            for key, matbalkey in self.translation.items():
                val = data_materialbalance.get(matbalkey, None)
                if val is None:
                    self.logger.warning('could not retrieve value (from materialbalance): %s (%s)', key, matbalkey)
                materialbalance[key] = val
        else:
            self.logger.warning('No input for materialbalance ... ')
        self.materialbalance = materialbalance

        ### Get WE-technology
        self.tec_we = materialbalance.get('technology_we', None)
        if not self.tec_we:
            self.logger.info('No technology specified: ', self.tec_we)
        ### Set important keys
        self.src_electricity = materialbalance.get(self.translation.get('source_electricity', 'source_electricity'), None)
        self.mode_operation = materialbalance.get(self.translation.get('mode_operation', 'mode_operation'),None)
        self.years_tea = self.get_years_tea(materialbalance)




        ### Ini parameters
        if parameters is not None:
            self.parameters = parameters  # Parameters as dict
        else:
            self.logger.warning('No parameter input... ')
        # basic, electricity_costs, teco_AEL, teco_PEM, external_scenario

        # TODO: check if years exist in parameters
        self.setup_parameters( include_all_costs=False)

        self.setup_we_instances()

        return
    def setup_we_instances(self):
        self.we_instances = {}
        for year_tea in self.years_tea:
            ### Ini water-electrolyzer instance

            we = WaterElectrolyzer(self.logger, self.name, technology=self.tec_we, year=year_tea,
                                   materialbalance=self.materialbalance,
                                   parameters=self.parameters, parameters_flat=self.parameters_flat,
                                   price_electricity=self.dct_price_electricity.get(year_tea, None),
                                   surcharges_electricity_dc=self.dct_surcharges_electricity.get(year_tea, {}).get('dc',0),
                                   surcharges_electricity_ac=self.dct_surcharges_electricity.get(year_tea, {}).get('ac', 0),
                                   surcharges_electricity_1gwh=self.dct_surcharges_electricity.get(year_tea, {}).get('1gwh', 0),
                                   dct_include_costs=self.dct_include_costs,
                                   debug=self.debug
            )
            self.we_instances[year_tea] = we
        return



    def get_years_tea(self, materialbalance):
        ### Get specified years for tea
        years_in = materialbalance.get(self.translation.get('years_tea', 'years_tea'), None)
        if isinstance(years_in,(int,float)):
            years_tea = [str(years_in)]
        else:
            years_in = years_in.split(',')
        if isinstance(years_in, list):
            years_tea = [str(int(item)) for item in years_in]
        else:
            self.logger.warning('No year specified: %s', years_in)
        return years_tea

    def setup_parameters(self, include_all_costs=False):

        ### Ini dicts
        self.dct_price_electricity = self.parameters.get('electricity_costs', {}).get(self.src_electricity, None)
        self.dct_surcharges_electricity = self.parameters.get('electricity_surcharges', {}).get(self.mode_operation,
                                                                                                None)
        if self.dct_price_electricity is None:
            self.logger.info('Error in parameters (electricity costs): ', self.dct_price_electricity)
        if self.dct_surcharges_electricity is None:
            self.logger.info('Error in parameters (electricity surcharges): ', self.dct_surcharges_electricity)
        # print('dct params: ', self.parameters)
        if self.tec_we is None:
            print('Materialbalance: ', self.materialbalance)
        # costs_electrolyzer_year_spc = parameters.get('acquisition_' + self.tec_we, {}).get(self., None)

        self.dct_include_costs = {}
        for key in self.parameters['static']['include']: #keys_include:
            if include_all_costs == True:
                self.dct_include_costs[key] = True
                val = True
            elif key in self.parameters.get('basic',{}):
                val = self.parameters.get('basic',{}).get(key,False)
            else:
                val = False
            self.dct_include_costs[key] = val
            if val == False:
                self.logger.info('Exclude %s from cost calculation', key)

        return







class WaterElectrolyzer():

    def __init__(self, logger, name, technology, year, materialbalance=None, parameters=None, parameters_flat=None,
                        price_electricity=None, surcharges_electricity=None ,
                        surcharges_electricity_dc=None, surcharges_electricity_ac=None ,
                    surcharges_electricity_1gwh=None, dct_include_costs={},debug=False):

        self.debug = debug
        self.name = name+'-'+str(year)+'-'+str(technology)
        self.logger = logger
        self.logger.info('Setup WE-Instance: %s', self.name)
        self.technology = technology
        self.year = year
        self.logger = logger
        self.dct_include_costs = dct_include_costs

        ### Read technology parameters
        for key,val in parameters.get('teco_' + self.technology).items():
            value = val.get('value', None)
            if isinstance(value,(int,float)):
                setattr(self,key,value)
            else:
                self.logger.warning('Could not set Parameter-value %s: %s ', key,value)

        ### Read materialbalance
        for key,val in materialbalance.items():
            setattr(self,key,val)

        # print('WE.__dict__: ', self.__dict__)

        self.price_electricity = price_electricity
        self.surcharges_electricity = surcharges_electricity
        self.surcharges_electricity_dc = surcharges_electricity_dc
        self.surcharges_electricity_ac = surcharges_electricity_ac
        self.surcharges_electricity_1gwh = surcharges_electricity_1gwh

        # TODO: iterate utiliozed energy <-> mass hydrogen <-> etc to clc missing values


        ### Capex we


        if self.costs_acquisition_we is not None:

            self.capex_plant = self.costs_acquisition_we * self.lang_factor

        elif self.costs_acquisition_plant is not None:
            self.capex_plant = self.costs_acquisition_plant  * self.nominal_power_we
            self.costs_acquisition_we  = self.capex_plant / self.lang_factor

        self.capex_st = self.costs_acquisition_we * (1 - self.fraction_stackacquisition)

        ### Capex stack
        # capex_stack_spc = self.costs_acquisition_plant * self.fraction_stackacquisition

        # Capex, total
        # capex_specific_tot = self.costs_acquisition_plant * self.lang_factor

        ### Energy demand
        if isinstance(self.specific_energy_demand_we, (int,float)):
            self.electricity_utilized_we_clc = self.specific_energy_demand_we * self.mass_of_hydrogen_produced
        if isinstance(self.electricity_utilized_we, (int,float)):
            if self.electricity_utilized_we_clc >0:
                fraction_clc_input = self.electricity_utilized_we_clc/self.electricity_utilized_we
                if 0.01 < fraction_clc_input < 1.01:
                    self.logger.info('Inconsistency in inputs: Utilized electricity we clc/input %s', fraction_clc_input)
        # else:
        self.electricity_utilized_we = self.electricity_utilized_we_clc
        if not hasattr(self, 'electricity_utilized_we_dc'):
            if hasattr(self, 'electricity_utilized_we_ac'):
                self.electricity_utilized_we_ac = electricity_utilized_we
                self.electricity_utilized_we_dc = 0


        ### Mass of hydrogen


    def clc_total_costs(self):

        if self.debug:
            self.logger.info('Clc total costs ...')
        annuity_factor = clc.annuity_factor(self.interest_rate,self.lifetime_electrolyzer)
        if self.dct_include_costs.get('include_costs_capitalinvest', False):
            if self.debug:
                self.logger.info('Clc capital invest ...')
            self.res_capitalinvest = clc.capitalinvest(self.nominal_power_we, annuity_factor, self.capex_plant)

            self.logger.info('Total capital invest: %s', self.res_capitalinvest)

        if self.dct_include_costs.get('include_costs_electricity', False):
            if self.debug:
                self.logger.info('Clc electricity costs ...')
            self.res_costs_electricity, self.res_costs_electricity_incl = clc.total_costs_electricity(self.logger,
                                        self.electricity_utilized_we_dc, self.electricity_utilized_we_ac,
                                        self.electricity_utilized_we, self.price_electricity,
                                        self.surcharges_electricity_dc, self.surcharges_electricity_ac,
                                        self.surcharges_electricity_1gwh,
                                        electricity_costs_from_simu=False,
                                        ce_from_simu=0, exclude_first_gwh=False)

            self.logger.info('Total costs electricity: %s', self.res_costs_electricity)
            self.logger.info('Total costs electricity (incl): %s', self.res_costs_electricity_incl)


        if self.dct_include_costs.get('include_costs_stackreplacement', False):
            if self.debug:
                self.logger.info('Clc stackreplacement costs ...')
                self.logger.info('Capex_stack (in) : %s', self.capex_st)
            self.res_costs_stackreplacement = clc.stackreplacement( self.capex_st, # capital costs Stack
                            self.nominal_power_we,  # Nominal Power of plant
                            self.operation_time_we, #total_operation_time_stack
                            self.lifetime_stack, self.lifetime_electrolyzer,
                            offset_n_replacements=0,
                            skip_clc=False,
                            apply_old_method=False, debug=self.debug, return_specific=False)
            self.logger.info('Total costs stackreplacement: %s', self.res_costs_stackreplacement)


        if self.dct_include_costs.get('include_costs_maintenance', False):
            self.res_costs_maintenance = clc.costs_maintenancec(self.costs_maintenance, self.nominal_power_we)

            self.logger.info('Total costs maintenance: %s', self.res_costs_maintenance)

        if self.dct_include_costs.get('include_costs_taxesandinsurances', False):
            self.res_costs_taxesandinsurances = clc.costs_taxes_and_insurances(self.costs_taxesandinsurances, self.res_capitalinvest)
            self.logger.info('Total costs taxes & insurances: %s', self.res_costs_taxesandinsurances)

        if self.dct_include_costs.get('include_costs_labor', False):
            self.res_costs_labor = clc.costs_labor(self.number_supervisor_per_plant, self.time_plant_supervision, self.costs_labor)
            self.logger.info('Total costs labor: %s', self.res_costs_labor)

        if self.dct_include_costs.get('include_costs_water', False):
            self.res_costs_water = clc.costs_water(self.costs_diwater, self.mass_of_water_consumed)
            self.logger.info('Total costs water: %s', self.res_costs_water)

        if self.dct_include_costs.get('include_revenues_oxygen', False):
            self.res_revenues_oxygen = - clc.revenues_oxygen(self.revenue_oxygen, self.mass_of_oxygen_produced)
            self.logger.info('Total revenues_oxygen: %s', self.res_revenues_oxygen)


        if self.dct_include_costs.get('include_costs_storage', False):
            self.logger.warning('Storage costs deactivated')

        if self.dct_include_costs.get('include_costs_externalcompression', False):
            self.logger.warning('Costs for external compression deactivated')



        self.sum_res_costs = 0
        self.sum_res_costs_incl = 0
        for item in ['res_capitalinvest', 'res_costs_stackreplacement', 'res_costs_electricity_incl',
                     'res_costs_maintenance', 'res_costs_labor', 'res_costs_taxesandinsurances',
                    'res_costs_water', 'res_revenues_oxygen']:
            val =  getattr(self, item, np.nan)
            if np.isnan(val):
                self.logger.info('Error in calculation for %s: %s', item, val)
            else:
                self.sum_res_costs_incl += val
        return

    def clc_lcohydrogen(self):
        self.lcoh2 =  self.sum_res_costs_incl / self.mass_of_hydrogen_produced
        return