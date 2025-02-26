"""
Handling input and output of data
"""

import os
import glob
from loguru import logger
from dataclasses import dataclass, field

import pandas as pd
from oathyps.misc import readfiles as rf
from oathyps.tools import mad


def make_output_dir(pth_output):
    # TODO: Write proper functionality here
    if os.path.exists(pth_output):
        exists = True

        if len(os.listdir(pth_output)) > 0:
            n = 0
            while exists:
                n += 1
                pth_output = pth_output + "_" + str(n)
                if not os.path.exists(pth_output):
                    exists = False

    os.makedirs(pth_output)

    return pth_output


def read_parameters(pth_to_inputfiles):
    logger.info("Read parameters ... ")
    files = glob.glob(pth_to_inputfiles + "/*.json")
    if len(files) > 0:
        if len(files) > 1:
            logger.warning("More than one parameter-file available")
        logger.info("Use parameters: {}", files[0])
        return rf.read_json_file(abspth_to_fl=files[0])
    else:
        return None


def read_timeseries(pth_to_directory="", path_to_file="", type_of_data=""):
    files = [file for file in glob.glob(pth + ".csv") if type_of_data in file]

    pd.read_csv()
    return


def adjust_data(data, pth_in=None, pth_out="", col=None):
    """
    Manually adjust loadprofile

    """

    def end_mad():
        print("MAD closed!")

    def use_data(data):
        print(data)

    madj = mad.MAD(data, pth_to_file=pth_in, pth_outputfile=pth_out, data_column=col)
    madj.closeEvent.connect(end_mad)  # funktioniert leider nicht!
    madj.selectEvent.connect(use_data)
    madj.start()
    del madj
    logger.debug("Finished MAD")


def store_results(results: dict, pth: str):
    if pth and os.path.exists(pth):
        for k, v in results.items():
            pth_to_file = os.path.join(pth, k)
            logger.info("Write {} data to file: \n {}", modelvariable.name, filepath)
            v.to_csv(pth_to_file)
    else:
        logger.info("Invalid path to directory for writing data: {}", pth)


def write_variable_dict_to_csv(dct):

    return


def extract_variablevalue(modelvariable) -> dict:
    """
    Extract values of given model variable and return as dict name:series

    """
    if modelvariable is not None:
        s = pd.Series(
            modelvariable.extract_values(), index=modelvariable.extract_values().keys()
        )

        # Unstack series if multi-indexed
        if type(s.index[0]) == tuple:  # it is multi-indexed
            s = s.unstack(level=1)
        else:
            s = pd.DataFrame(s)  # Force transition from Series -> df
        logger.trace("Index levels in variable: {}", s.index.nlevels)
        logger.trace("Column levels in variable: {}", s.columns.nlevels)

        if s.index.nlevels > 1:
            return {
                "_".join(["df", modelvariable.name, str(lvl)]): s.loc[lvl, :]  # .mask(
                # s.loc[lvl, :] <= 0
                # )
                for lvl in range(s.index.nlevels)
            }
        else:
            return {"_".join(["df", modelvariable.name]): s}


def extract_decision_data(model, pth_out=""):
    """
    Function customized for extracting data from variable w_srk
    """

    w = model.ws_r_k
    varname = w.name
    r = np.array(model.R.value)
    logger.info("Extract data for decision variable {}", w.name)
    # make a pd.Series from each
    s = pd.Series(w.extract_values(), index=w.extract_values().keys())
    # r = pd.Series(r.extract_values(), index=r.extract_values().keys())

    logger.trace("Index r: {r}")
    # if the series is multi-indexed we need to unstack it...
    if type(s.index[0]) == tuple:  # it is multi-indexed
        s = s.unstack(level=1)

    else:
        s = pd.DataFrame(s)  # force transition from Series -> df
    logger.trace("Index levels in variable: {}", s.index.nlevels)
    logger.trace("Column levels in variable: {}", s.columns.nlevels)

    if s.index.nlevels > 1:
        for lvl in range(s.index.nlevels):
            dfi = s.loc[0, :]
            dfi = dfi.mask(dfi <= 0)
            if pth_out:
                filepath = pth_out.replace(
                    "data", "df_" + varname + "_" + str(lvl) + "_"
                )
                logger.info("Write file: {}", filepath)
                dfi.to_csv(filepath)
            # print('1: ',s.loc[1, :].plot())
    # multi-index the columns
    # s.columns = pd.MultiIndex.from_tuples([(k, t) for k,t in s.columns])

    # serieses.append(s)

    return


def read_results(pth: str) -> dict:
    """
    Read .csv files from cyclopt-results-directory

    pth : String
        Path to directory containing cyclopt optimization output

    Returns
    -------
    Dict containing with structure variable-name: DataFrames
    """

    return {
        pd.read_csv(fl.replace(".csv", ""), index_col=0)
        for fl in glob.glob(pth + "/*.csv").sort()
    }
