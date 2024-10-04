# -*- coding: utf-8 -*-
"""
Auxilliary functions.

@author: David Fuhrländer
"""
import os
import logging
import datetime

def timestamp(how='ISO'):
    '''
    Return datetimestamp as string
        Default is "ISO", referring to ISO 8601.
    '''

    d = {'ym':'%y%m',
         'ymd':'%y%m%d',
         'yymd':'%Y%m%d',
         'ISO':'%Y-%m-%d',
         'ISO+md':'%Y-%m-%d_%H%M',
         'yymdhm':'%Y%m%d%H%M'}

    now = datetime.datetime.now()
    strng = now.strftime(d.get(how,'ym'))

    return strng



def ini_logging(obj, name='', pth='', level='INFO'):
    '''
    Initialize logging for console output only

    '''
    loggername = 'lggr_'+name
    logger = logging.getLogger(loggername)


    if level.upper() == 'DEBUG':
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # remove all default handlers

    for handler in logger.handlers:
        logger.removeHandler(handler)
    # create console handler and set level to debug
    console_handle = logging.StreamHandler()
    if level.upper() == 'DEBUG':
        console_handle.setLevel(logging.DEBUG)
    else:
        console_handle.setLevel(logging.INFO)

    # create formatter
    formatter = logging.Formatter("%(name)-20s :: %(levelname)-8s :: %(message)s")
    # formatter =logging.Formatter('[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s %(name)s \n- %(message)s')#,
    console_handle.setFormatter(formatter)

    # now add new handler to logger
    #logger.addHandler(console_handle) # Remove to avoid duplicate output
    return logger, loggername




def print_filelist(fllst, name=None):
    '''
    print elements of list
    '''
    print('The List ({}) contains:'.format(name))
    for item in fllst:
        print(os.path.basename(item))#+'\n')
    return


def mk_dir(pth=None,nm='',timestamp_format='ISO+md'):
    if pth is None:
        pth = os.getcwd()

    tstmp = timestamp(how=timestamp_format)
    # make basic output directory
    pth_out = os.path.join(pth, nm, tstmp)
    os.makedirs(pth_out, exist_ok=True)

    return pth_out