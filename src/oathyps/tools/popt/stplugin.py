import os
import streamlit as st
import pandas as pd
from oathyps.tools.popt import clc
from oathyps.misc import plotting as plp
from oathyps.misc import readfiles as rf


@st.cache_data
def process_data(args, file=None, use_default_data=False):
    we = None

    read_file_successfully = False
    if file is not None:
        try:
            df_in = pd.read_csv(file)
            read_file_successfully = True
        except:
            df_in = None


        if df_in is not None:
            if len(df_in.columns) >2:
                st.write('Columns should be [Date,Power] (slicing df)')
                df_in = df_in.iloc[:,[0,1]]
        else:
            st.write('-- Invalid type of file --')

            use_default_data = True

    if use_default_data == True or read_file_successfully == False:
        power_output = clc.read_default_data()
        df_in = pd.DataFrame(power_output)
        df_in = df_in.reset_index()
    df_in.columns = ['Date', 'P']
    df_in['Date'] = pd.to_datetime(df_in.Date)




    df_in['tdelta'] = (df_in['Date'].diff().dt.seconds.div(3600, fill_value=0))
    df = clc.power_specific_key_values(df_in, we, **args)
    return df, df_in, read_file_successfully

with (st.sidebar):

    use_default_data = st.checkbox('Use default data')

    if not use_default_data:
        file_in = st.file_uploader('Specify path to file (DataFrame wit [Date, Power] columns)' )
    else:
        file_in = None


    args = {
    "n_iterations": st.slider("Select resolution (n iterations)", 1, 1000,100),
    "sig_column": st.text_input("Column name for power-signal ", value='P'),
    "P_we_max": st.slider("Maximum Rated Power of Water-Electrolyzer",0.,2.0,1.5,step=0.05)*1e6,
    "P_sig_max": st.slider("Scaling of input power data", 0., 2.,2.,step=0.05)*1e6,
    "frc_P_we_min": st.slider("Minimum power fraction of Water-Electrolyzter", 0.,1.,0.1),
    "efficiency_we_hhv": st.slider("Efficiency (HHV) of WE", 0.,1.,0.75),
    "capex_we_specific": st.slider("Specific CAPEX of WE (€/kW)", 0,5000,500),
    "opex_we_specific": st.slider("Specific OPEX of WE (€/kW)",0, 200,10),
    "costs_stack_we_specific": st.slider("Costs of WE-stack (€/kW)", 0,5000,500),
    "costs_electricity_spc": st.slider("Costs of electricity (€/MWh)",0,500,100)*1e-3,
    "lifetime_stack_we": st.slider("Lifetime of WE_Stack in hours",1,500000,100000),  # h
    "lifetime_plnt_we": st.slider("Lifetime WE-plant in years",1,100,20)  # a
    }

    df, df_in, external_data = process_data(args,file=file_in,use_default_data=use_default_data)
    #st.dataframe(df)


    st.button("Rerun")

plt_dct = {
        'energy_utilized_we': {'scl': 1e-9, 'unit': 'TWh', 'label': 'Utilized energy \n in \n ', 'limits': [0, 10]},
        'full_load_hours_we': {'scl': 1, 'unit': 'h', 'label': 'Full Load\n Hours in \n ', 'limits': [0, 10000]},
        'mass_hydrogen_produced': {'scl': 1e-6, 'unit': 'kt', 'label': 'Produced amount \n of hydrogen \n in \n ',
                                   'limits': [0, 150]},
        'lcoh': {'scl': 1, 'unit': '€/kg', 'label': 'LCOH \n in \n ', 'limits': [0, 10]}}
if external_data:
    st.write('Using your data: ')
    dffig = plp.plot_df(df_in)
    st.pyplot(dffig)
# anno_value = st.slider("Aim for flh: ", min_value=0,max_value=8700,value=5000,step=10)
anno_value = st.slider("Rated power: ", min_value=0.,max_value=1.5,value=0.5,step=0.01)*1e6

fig = clc.plot_popt(df, plt_dct, anno_key='rated_power_we', #full_load_hours_we',
                    anno_val=anno_value,
                    key_x='rated_power_we', scale_x=1e-6, unit_x='GW', no_labels=True)
st.pyplot(fig)
