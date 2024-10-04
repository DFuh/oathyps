#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 26 13:36:13 2024

@author: DFuh
"""
import numpy as np
import matplotlib.pyplot as plt 
from pyomo.environ import *

### Plotting

def plot_eaf_opt(model, keys=[],printvals=False, pth_out=None):
    
    #if not keys:
    #    keys = ['P_res', 'P_s_k', '']
    #    print('Plot default: ')
    var = getattr(model,'P_res',None)
    idx = list(var)
    P_price = list(model.P_price[:])
    P_diff = value(model.testv_k[:])
    P_fix = list(model.P_fix[:])
    P_res = value(model.P_res[:])
    
    
    l_Psk = []
    kl_Psk =[]
    l_w = []
    kl_w = []
    
    for s in range(len(model.S)):
        
        #['w_srk0','w_srk1']
        l_Psk.append(value(model.P_s_k[s,:]))
        kl_Psk.append('P_sk_'+str(s))
        
        #P_sk1 = value(model.P_s_k[1,:])
    
        # ridx0 = []
        # ridx1 = []
        ws_r_k = []
        # ws_r_k1 = []
        for r in model.R:
            

            l = len(list(value(model.ws_r_k[0,r,:])))
            ws_r_k.append(np.array(value(model.ws_r_k[s,r,:]))*(r+1))

        w0 = []
        for arr in ws_r_k:
            w0.append(np.where(arr <=0,None, arr))
        l_w.append(w0)
        kl_w.append('w_srk_'+str(s))
    

    x = [np.arange(len(model.K))]*len(model.R)
    sp_idx0 = value(model.sp_s_k[0,:])
    sp_idx1 = value(model.sp_s_k[1,:]) 
    act_idx0 = value(model.actp_s_k[0,:])
    act_idx1 = value(model.actp_s_k[1,:])

    pltlst = [[P_price], [P_fix, P_res] + l_Psk, [P_diff, ], l_w]  # [sp_idx0,sp_idx1,act_idx0,act_idx1]]
    keylst = [['P_price'], ['P_fix', 'P_res'] + kl_Psk, ['P_diff'], kl_w]
    mrk0 = ['none','none','o','x','+','>','*']+['o','x','+','>','*']*int(len(model.S)/5)
    mrk = ['o','x','+','>','*']+['o','x','+','>','*']*int(len(model.S)/5)
    if True:
        lp = len(pltlst)
        fig,ax = plt.subplots(lp,sharex=True,)
        for i,lsts in enumerate(pltlst):
            for j,res in enumerate(lsts):
                if printvals:
                    print(f'{keylst[i][j]}: {res}')
                if i <lp-1:
                    #for k,resi in enumerate(res):
                    ax[i].plot(idx,res,linewidth=1,marker=mrk0[j],label=keylst[i][j])
                else:
                    ax[i].scatter(x,res,marker=mrk[j],label=keylst[i][j])
        
        for axi in ax:
            axi.legend()
            axi.grid()
        plt.xlabel('Variable Indices')
        plt.ylabel('Values')
        #plt.legend()
        #plt.grid()
        plt.show()
    if pth_out is not None:
        fig.savefig(pth_out)
    return #x, ws_r_k0


