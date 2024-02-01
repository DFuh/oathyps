# -*- coding: utf-8 -*-
"""
Main Class for TEA

@author: David Fuhrländer
"""
import os

from clc import TeaScenario

#TODO: make ouput of data/ file status

class elTeco():
    """main class elEco."""

    def __init__(self, pth_to_dir_parameters=None, pth_to_file_inputdata=None,
                pth_to_dir_outputfile=None,
                flnm_matbal='', addkey_flnm_teares='',
                debug=False, slct_par_version=True):

        self.timestamp = hlp.timestamp(how='ISO')
        self.name = 'elEco'

        self.logger, self.logger_nm = hlp.ini_logging(self)
        self.logger.info('Ini logging: {}'.format(self.logger_nm))

        self.pth_data_loc=pth_data_loc
        self.pth_output = pth_output

        self.addkey_flnm_teares=addkey_flnm_teares

        self.pth_to_dir_parameters = pth_to_dir_parameters
        self.pth_to_file_inputdata = pth_to_file_inputdata
        self.pth_to_dir_outputfile = pth_to_dir_outputfile


        self.parameters_in, self.parameters_flat  = self.read_parameters(self,
                                pth_to_parameters,
                                debug, skip=False) # read parameters, return dict
        self.materialbalnce = self.read_materialbalance()

        #self.tea_instances = self.setup_tea()


    def read_parameters(self, pth_to_parameters, test, skip=False):

        '''
        read parameter files and return full dict or None
        '''
        # TODO: check existence of mandatory parameters
        # TODO: make path-to-parameters an input-variable

        parameters = {}
        parameters_flat = {}
        lst_par_sets = ['basic',
                    'electricity_costs',
                    'electricity_surcharges',
                    'acquisition_PEM',
                    'acquisition_AEL',
                    'teco_AEL',
                    'teco_PEM',
                    'teco_storage',]

        for par_set in lst_par_sets:

            if debug:
                self.logger.INFO('Read Parameter Set: %s', par_set)
                suffix = '_debug.json'

            jsonpth = os.path.join(pth_to_parameters,
                            'parameters_' + par_set + suffix)

            if not os.path.exists(jsonpth):
                self.logger.INFO('Parameter-Set not found: %s', jsonpth)
                skip = True
            if not skip:
                with open(jsonpth) as jsonfile:
                    data=json.load(jsonfile)

                    parameters_in[pr_set] = data
                    parameters_flat.update(data)

        return parameters_in, parameters_flat


    def read_materialbalance(self,):
        '''
        '''
        ### Read data
        if (self.pth_to_file_inputdata is not None and
                os.path.exists(self.pth_to_file_inputdata):
            self.logger.info('Read external Scenario-Data: %s',
                            self.pth_to_file_inputdata)
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

        if materialbalance is not None:

            instances = []
            for num,(idx,row) in enumerate(df.iterrows()):
                if self.debug:
                    self.logger.info('[%s]-----> idx=%s, data=%s', num, idx, row)
                    self.logger.info('df.name =  %s, %s', row['name'], type(row['name']))
                instances.append(TeaScenario(row['name'],
                                        logger=self.logger,
                                        external_scenario=external_scenario,
                                        parameters=self.parameters_flat,
                                        data_materialbalance=row.to_dict(),
                                        #enable_CE=enable_CE,
                                        pth_output=self.pth_to_dir_outputfile,
                                        )

        return instances


class TeaScenario():
    '''
    TEA-scenario class
    creates an instance for every simulation including multiple years,
    or
    for multiple external scenarios
    '''

    def __init__(self, name, logger=None, external_scenario=False, parameters=None,
                    data_materialbalance=None, include_all_costs=False):

        ### Basics
        self.timestamp = hlp.timestamp(how='ISO')
        self.name = name
        self.ext_scenario = external_scenario
        self.tag = kwargs.get('tag', 'notag')

        self.include_all_costs = include_all_costs
        ## Ini Logging
        if logger is None:
            self.logger, self.lggrnm = fx.ini_logging(self, name=name, pth=logpth)
        self.logger = logger
        self.logger.info('Ini External Scenario: %s', name)



        ### Ini materialbalance
        if data_materialbalance is not None:
            self.materialbalance = data_materialbalance
        else:
            self.logger.warning('No input for materialbalance ... ')

        ### Set source for electricity
        self.src_electricity = materialbalance.get(self.keys_technology.get('source_electricity', 'source_electricity'),
                                                   None)

        ### Get WE-technology
        self.tec_we = materialbalance.get(self.keys_technology.get('technology_we', 'tec'), None)
        self.src_electricity = materialbalance.get(self.keys_technology.get('source_electricity', 'src_electricity'), None)
        self.mode_operation = materialbalance.get(self.keys_technology.get('mode_operation', 'mode_operation'),None)

        self.years_tea = self.get_years_tea(materialbalance)


        ### Ini parameters
        if parameters is not None:
            self.parameters = parameters  # Parameters as dict
        else:
            self.logger.warning('No parameter input... ')
        # basic, electricity_costs, teco_AEL, teco_PEM, external_scenario

        self.we_instances = {}
        for year_tea in self.years_tea:
            ### Ini water-electrolyzer instance
            we = WaterElectrolyzer()



            we_instances[year] = we
        return

    def get_years_tea(self, materialbalance):
        ### Get specified years for tea
        years_in = materialbalance.get(self.keys_technology.get('years_tea', 'years_tea'), None)
        if isinstance(years_in,(int,float)):
            years_tea = [str(years_in)]
        if isinstance(years_in, list):
            years_tea = [str(int(item)) for item in years_in]

        return years_tea

    def setup_parameters(self, parameters):
        self.par_bsc = parameters.get('basic',{})

        ### Get year-specific parameters
        self.dct_price_electricity = parameters.get('electricity_costs', {}).get(self.source_electricity, None)
        self.dct_surcharges_electricity = parameters.get('electricity_surcharges', {}).get(self.electricity_supply, None)
        # costs_electrolyzer_year_spc = parameters.get('acquisition_' + self.tec_we, {}).get(self., None)

        # par_elec = self.par['electricity_costs']
        # par_surch = self.par['electricity_surcharges']
        # par_cpx = self.par['acquisition_'+self.tec_el]

        yrs_eCe = bsc_par.get('evaluate_years_eCe', [])

        return

    def set_keys(self):
        param_keys = {

        }

        matbal_keys = {
            'year': 'year',
            'nominal_power_we': 'P_N_el',
            'max_power_we': 'P_max_el',
            'max_power_generation': 'P_max_gen',
            'E_HHV_H2': 'E_HHV_H2',
            'E_LHV_H2': 'E_LHV_H2',
            'mass_of_hydrogen_produced': 'm_H2',
            'volume_of_hydrogen_produced': 'V_H2',
            'mass_of_hydrogen_exchange': 'm_H2_ext',
            'mass_of_oxygen_produced': 'm_O2',
            'volume_of_oxygen_produced': 'V_O2',
            'mass_of_water_consumed': 'm_H2O',
            'mass_of_hydrogen_demand': 'm_H2_dmnd',
            'utilized_electricity_we': 'E_util',
            'electricity_feed-in_potential': 'E_in',
            'electricity_demand_compressor': 'E_cmp',
            'electricity_costs_we_simu': 'CE_util',
            'electricity_costs_compressor_simu': 'CE_cmp',
            'theoretical_emissions_from_electricity_demand_we': 'emiss_E_util',
            'theoretical_emissions_from_electricity_demand_compressor': 'emiss_E_cmp',
            'operation_time_we': 't_op_el',
            'operation_time_electricity_feed-in': 't_op_gen',
            'full_load_hours_we': 't_fl_we',
            'full_load_hours_feed-in': 't_fl_gen',
            'time_period_simu': 't_simu',
            'mass_of_hydrogen_to_grid_simple': 'm_H2_to_grid_sc',
            'mass_of_hydrogen_from_grid_simple': 'm_H2_frm_grid_sc',
            'mass_of_hydrogen_to_storage_simple': 'm_H2_to_strg_sc',
            'mass_of_hydrogen_from_storage_simple': 'm_H2_frm_strg_sc'
        }

    parameter_keys = {

    }

    return


    def setup_we(self, year, materialbalance=None, parameters=None):
        #### Initialize auxilliary DataClass
        av = AuxVal()

        if materialbalance is None:
            materialbalance = self.materialbalance
        if parameters is None:
            parameters = self.parameters

        if self.tec_we is not None:

            ### Read technology parameters
            par_tec = parameters.get('teco_' + self.tec_we)
            for key,val in par_tec.items():
                value = val.get('value', None)
                if isinstance(value,(int,float)):
                    setattr(self.we,key,value)
                else:
                    self.logger.warning('Could not set Parameter-value %s: %s ', key,value)

            for key,matbalkey in self.keys_technology.items():
                val = materialbalance.get(matbalkey, None)
                if val is None:
                    self.logger.warning('could not retrieve value (from materialbalance): %s (%s)', key, matbalkey)
                setattr(self.we, key, val)

        self.we.setup()
        setattr(self.we, 'electricity_costs', self.dct_electricity_costs.get(year,None)
        setattr(self.we, 'electricity_surcharges', self.dct_surcharges_electricity.get(year, None)
        return



class WE():

    def __init__(self)):
        pass

    def setup(self):

        ### Capex we
        if self.costs_plantacquisition is not 0:

            self.capex_plant = self.costs_plantacquisition  * self.nominal_power
        else:
            self.capex_plant = self.costs_electrolyzer * self.lang_factor



        self.capex_st = self.costs_electrolyzer * (1 - self.fraction_stackacquisition)

        ### Capex stack
        capex_stack_spc = self.costs_plantacquisition * self.fraction_stackacquisition_pacq

        # Capex, total
        capex_tot_spc = self.costs_plantacquisition * self.lang_factor


        return

