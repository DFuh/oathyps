import os
import streamlit as st
import pandas as pd
from oathyps.tools.popt import clc
from oathyps.misc import readfiles as rf


@st.cache_data
def process_data(args, file=None, use_default_data=False):
    we = None

    if file is not None:
        if isinstance(file, pd.DataFrame):
            if len(file.columns) >2:
                st.write('Columns should be [Date,Power] (slicing df)')
                df_in = file.iloc[:,[0,1]]
            else:
                df_in = file.copy()
        else:
            st.write('-- Invalid type of file --'):

            use_default_data = True

    if use_default_data == True or file is None:
        power_output = clc.read_default_data()
        df_in = pd.DataFrame(power_output)
        df_in = df_in.reset_index()
    df_in.columns = ['Date', 'P']




    df_in['tdelta'] = (df_in['Date'].diff().dt.seconds.div(3600, fill_value=0))
    df = clc.power_specific_key_values(df_in, we, **args)
    return df, default_params

with (st.sidebar):

    use_default_data = st.checkbox('Use default data')

    if not use_default_data:


    args = {
    "n_iterations": st.slider("Select resolution (n iterations)", 1, 1000,100),
    "sig_column": st.text_input("Column name for power-signal ", value='P'),
    "P_we_max": st.slider("Rated Power of Water-Electrolyzer",0,2000000,300,step=100),
    "P_sig_max": st.slider("Scaling of input power data", 0, 2000000,1,step=100),
    "frc_P_we_min": st.slider("Minimum power fraction of Water-Electrolyzter", 0.,1.,0.1),
    "efficiency_we_hhv": st.slider("Efficiency (HHV) of WE", 0.,1.,0.75),
    "capex_we_specific": st.slider("Specific CAPEX of WE (€/kW)", 0,5000,500),
    "opex_we_specific": st.slider("Specific OPEX of WE (€/kW)",0, 200,10),
    "costs_stack_we_specific": st.slider("Costs of WE-stack (€/kW)", 0,5000,500),
    "costs_electricity_spc": st.slider("Costs of electricity (€/MWh)",0,500,100)*1e-3,
    "lifetime_stack_we": st.slider("Lifetime of WE_Stack in hours",1,500000,100000),  # h
    "lifetime_plnt_we": st.slider("Lifetime WE-plant in years",1,100,20)  # a
    }

    df, params = process_data(args,file=file,use_default_data=True)
    #st.dataframe(df)

    st.button("Rerun")


anno_value = st.slider("Aim for flh: ", min_value=0,max_value=8700,value=5000,step=10)
fig = clc.plot_popt(df, params.get("plt_dct",{}), anno_key='full_load_hours_we', anno_val=anno_value,
              key_x='rated_power_we', scale_x=1e-6, unit_x='GW', no_labels=True)
st.pyplot(fig)
