
#import pandas as pd
import matplotlib.pyplot as plt
def plot_df(df, sep_col_plots=False,idx_col=None):
    date_col = 'Date'
    if idx_col is None or idx_col not in df.columns:
        if date_col in df.columns:

            idx_col = date_col
            x_arr = df[date_col]
            df = df.drop(columns=date_col)
        else:
            x_arr = df.index
    else:
        x_arr = df[idx_col]
        df = df.drop(columns=[idx_col])


    if sep_col_plots:
        fig,axes = plt.subplots(len(df.columns))
    else:
        fig, axes = plt.subplots(1)
        axes = [axes]

    for i,col in enumerate(df.columns):
        idx = 0
        if sep_col_plots:
            idx=i
        axes[idx].plot(x_arr, df[col], label=[col],
                       linewidth=1)

    for ax in axes:
        ax.legend()
        ax.grid()
    plt.show()
    return fig