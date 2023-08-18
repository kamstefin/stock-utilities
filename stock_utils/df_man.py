"""
contains a class that provides general commonly used function by the artists"""
from matplotlib.dates import num2date
from . import cmnfunc as cfc
from datetime import datetime
from stock_utils.resrcutils.lockables import TCounter
import pandas as pd
import time
from threading import Thread,Event

fmt = cfc.FORMAT


class common_funcs:
    def __init__(self, pdf: pd.DataFrame):
        self.pdf = pdf
        self.index = pd.Series(self.pdf.index)

    def get_data(self, index):
        """returns data from the DataFrame int-indexed by index[0]:index[1]"""
        return self.pdf.iloc[index[0] : index[1]]

    def get_locs(self, ilocs):
        """`return` DataFrame index given integer locators"""
        return list(self.pdf.iloc[list(ilocs)].index)

    def get_ilocs(self, locs):
        """returns  absolute  int-DataFrame index given DataFrame locators"""
        return [int(self.index[self.index == x].index[0]) for x in locs]

    def get_ylims(self, index: tuple):
        """get y limits.
        *   if limits are equal, return None"""
        temp_pdf = self.pdf.iloc[index[0] : index[1]][cfc.COLUMNS]
        lim=(temp_pdf.min().min() , temp_pdf.max().max())
        if lim.count(lim[0])==len(lim):
            lim=None
        return lim

    def find_index(self, loc, ifnot=None):
        index = self.index[self.index >= loc]
        int_index, loc_index = index.index[0], index.iloc[0]
        return int_index, loc_index


class OfflineDfMan(common_funcs):
    def __init__(self, df: pd.DataFrame) -> None:
        """
        args
        ----
            df - whole dataframe (the source df)
        """
        super().__init__(df)
        self.pdf = df
        self.index = pd.Series(self.pdf.index)
        self.max_index = self.get_ilocs((self.index.iloc[-1],))[0]
        self.str_index = self.index.apply(num2date).apply(
            lambda x: datetime.strftime(x, fmt)
        )


class OnlineDFman(common_funcs):
    def __init__(self, recv, sigok:int,sigkill: int) -> None:
        """
        args
        ----
        recv    endpoint of a mutliprocessing.Pipe
        sigok   for checking everything is alright on the other end
        sigkill for sending to the other end if this end decides to quit

        Notes
        -----
        a thread will be used to update local values an any shared data locally will be held by a thread lock
        """
        super().__init__(pd.DataFrame())
        self.data = recv
        self._sigok, self._sigkill = sigok,sigkill
        self.index = self.max_index = None

        self.data_thread = Thread(target=(self.recv_data))
        self.data_thread.start()

    def local_update(self):
        """update local values after a read on the pipe"""
        self.index = pd.Series(self.pdf.index)
        self.max_index = self.get_ilocs((self.index.iloc[-1],))[0]

    def recv_data(self):
        while 1:
            data = self.data.recv()
            if isinstance(data, pd.DataFrame):
                print("data-length: ",data.shape,' as of ',cfc.convert(int(time.time())))
                self.pdf = pd.concat([self.pdf, data], axis=0)
                self.data.send(self._sigok)
                self.local_update()
            else:
                if data == self._sigkill:
                    return
