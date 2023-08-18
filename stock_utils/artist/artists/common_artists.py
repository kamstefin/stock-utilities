import pandas as pd
from stock_utils import cmnfunc as cfc


class CArtists:
    def __init__(self, df: pd.DataFrame):
        """
        CommonArtists
        -------------
        this module implements artists functions which use the same dataframe"""
        self.pdf = df

    def set_df(self, df):
        self.pdf = df

    def ax1(self):
        return cfc.macd(self.pdf["c"])

    def ax2(self):
        return cfc.stoch(self.pdf)

    def ax3(self):
        ...

    def update(self):
        ax1 = self.ax1()
        ax2=self.ax2()
        return ax1,ax2
