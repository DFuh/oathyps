'''

'''


from loguru import logger
import pyomo.environ as pyo



def storage(model):
    '''
    Based on https://link.springer.com/chapter/10.1007/978-3-319-96355-6_4
    '''
    def balance(model,t):
        expr = 0

        expr += model.capacity[t]
        expr += model.capacity[t-1]
        expr += -model.flow_in[t]
        expr += model.flow_out[t]

        return expr == 0
    model.storagebalance = pyo.Constraint(model.T,rule=balance)
    return