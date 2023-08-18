"""this file contains most of the generic methods & constants that are being reused in different code segs"""
from pytz import utc
import matplotlib.dates as mdates
from datetime import datetime
import pandas as pd
import numpy as np
from matplotlib import axes

COLUMNS = ["o", "h", "l", "c"]
FORMAT = "%d/%H:%M"


def mdate2readable(x):
    return datetime.strftime(mdates.num2date(x), FORMAT)


def sma(__ser: pd.Series, window: int):
    return __ser.rolling(window=window).mean()


def convert(__loc1):
    """Makes a datetime.datetime object without a timezone from an epoch timestamp"""
    return datetime.strptime(
        utc.localize(datetime.fromtimestamp(__loc1)).strftime(
            "%y-%m-%d %H:%M",
        ),
        "%y-%m-%d %H:%M",
    )


def avg_tr(df: pd.DataFrame, ax_: axes._axes.Axes = None, window: int = 14):
    """Average true range"""
    hl = df["h"] - df["l"]
    hc = np.abs(df["h"] - df["c"].shift(1))
    lc = np.abs(df["l"] - df["c"].shift(1))
    r = np.max(pd.concat([hl, hc, lc], axis=1), axis=1).rolling(window).sum() / window
    if ax_:
        ax_.plot(r, lw=0.9)
        ax_.set_ylim((r.min(), r.max()))
        ax_.axhline(15, lw=0.9, marker="v", color="red")
    return r


def stoch(
    df: pd.DataFrame, period=14, ax_: axes = None, h="h", l="l", c="c"
) -> tuple[pd.Series, pd.Series]:
    h = df[h].rolling(9).max()
    l = df[l].rolling(36).min()
    num = df[c] - l
    denom = h - l
    k = ((num / denom) * 100).rolling(period).mean()
    D = k.rolling(12).mean()
    if ax_:
        ax_.plot(k, label="k", lw=0.8)
        ax_.plot(D, label="d", lw=0.8)
        ax_.legend()
    return k, D


def psar(df, iaf=0.02, maxaf=0.2, h="h", l="l", c="c"):
    length = len(df)
    high = list(df[h])
    low = list(df[l])
    close = list(df[c])
    psar = close[0 : len(close)]
    bull = True
    af = iaf
    hp = high[0]
    lp = low[0]
    for i in range(2, length):
        x = hp if bull else lp
        psar[i] = psar[i - 1] + af * (x - psar[i - 1])
        reverse = False
        if bull:
            if low[i] < psar[i]:
                bull = False
                reverse = True
                psar[i] = hp
                lp = low[i]
                af = iaf
        else:
            if high[i] > psar[i]:
                bull = True
                reverse = True
                psar[i] = lp
                hp = high[i]
                af = iaf

        if not reverse:
            if bull:
                if high[i] > hp:
                    hp = high[i]
                    af = min(af + iaf, maxaf)
                if low[i - 1] < psar[i]:
                    psar[i] = low[i - 1]
                if low[i - 2] < psar[i]:
                    psar[i] = low[i - 2]
            else:
                if low[i] < lp:
                    lp = low[i]
                    af = min(af + iaf, maxaf)
                if high[i - 1] > psar[i]:
                    psar[i] = high[i - 1]
                if high[i - 2] > psar[i]:
                    psar[i] = high[i - 2]
    return pd.Series(psar, index=df.index, name="psar")


def p_sar(df, acc_f=0.02, acc_max=0.2):
    high = df["h"].values
    low = df["l"].values
    index = df.index
    trend = np.zeros(len(df))
    trend[0] = 1
    ep = np.zeros(len(df))
    sar = np.zeros(len(df))
    for x in range(1, len(df)):
        if trend[x - 1] == 1:
            if low[x] > low[x - 1]:
                trend[x] = 1
                ep[x] = max(high[x], ep[x - 1])
            else:
                trend[x] = -1
                ep[x] = min(low[x], ep[x - 1])
        else:
            if high[x] < high[x - 1]:
                trend[x] = -1
                ep[x] = min(low[x], ep[x - 1])
            else:
                trend[x] = 1
                ep[x] = max(high[x], ep[x - 1])
        if trend[x - 1] == 1:
            sar[x] = sar[x - 1] + acc_f * (ep[x - 1] - sar[x - 1])
            sar[x] = min(sar[x], low[x - 1], low[x - 2])
        else:
            sar[x] = sar[x - 1] - acc_f * (sar[x - 1] - ep[x - 1])
            sar[x] = max(sar[x], high[x - 1], high[x - 2])

        if trend[x] == 1 and sar[x] > low[x]:
            trend[x] = -1
            sar[x] = ep[x - 1]
            ep[x] = high[x]
        elif trend[x] == -1 and sar[x] < high[x]:
            trend[x] = 1
            sar[x] = ep[x - 1]
            ep[x] = low[x]
        if acc_f < acc_max:
            acc_f += acc_f
    sar = np.where(sar == 0, np.nan, sar)
    return pd.Series(sar, index=index)


def wma(ser: pd.Series, period: int = 14, name="1"):
    """weighted moving average"""
    index = ser.index
    close = ser.values
    weights = np.arange(1, period + 1)
    weights_sum = np.sum(weights)
    wma = np.zeros(len(ser))
    for i in range(period - 1, len(ser)):
        wma[i] = np.dot(weights, close[i - period + 1 : i + 1]) / weights_sum
    wma = np.where(wma == 0, np.nan, wma)
    return pd.Series(wma, index=index, name=name)


def macd(ser_: pd.Series, ax_: axes = None, x=12, y=26, z=9):
    ema_12 = ser_.ewm(span=x, adjust=False).mean()
    ema_26 = ser_.ewm(span=y, adjust=False).mean()
    md = ema_12 - ema_26
    signal = md.ewm(span=z, adjust=False).mean()
    if ax_:
        ax_.plot(md, label="m", lw=0.9)
        ax_.plot(signal, label="s", lw=0.9)
        ax_.legend()
    return signal, md


def get_pdf(
    _csv_name="datfiles/main1.csv",
    drop_timestamp=False,
    reset_index=False,
    column1toindex=False,
    convert_2_readable=False,
    date_2_num=False,
) -> pd.DataFrame:
    df = pd.read_csv(_csv_name, index_col=None)
    index = df.index
    if convert_2_readable:
        index = df["d"].apply(convert)
    if date_2_num:
        index = df["d"].apply(convert).apply(mdates.date2num)
    if column1toindex:
        index = df["d"]
    if drop_timestamp:
        df = df.drop("d", axis=1)
    df.index = index
    if reset_index:
        df.reset_index(inplace=True, drop=True)
    return df


def cross(ser1, ser2, count=0, direction=1):
    """returns `count` or less crossing points of  `ser1` and `ser2`.

    Notes
    -----
    * ->if count is 0, all crossing points are returned.
    * ->`direction` defines where to start looking for crossing points. if 0, `ser1` and `ser2` are reversed.
    """
    index, ser_index = [], ser1.index
    ser1 = ser1 - ser2
    ser1.reset_index(inplace=True, drop=True)
    if not direction:
        ser1 = ser1[::-1]
    ser1 = [ser1 < 0][0]
    zero, counter = ser1.iloc[0], 0
    for i in ser1.iloc[1:]:
        counter += 1
        if i == zero:
            continue
        else:
            zero = i
            index.append(counter)
            if len(index) == count:
                break
    if not direction:
        index = (np.array(index) * -1).tolist()
        if 0 in index:
            index.remove(0)
            index.append(len(ser_index))
        if len(ser_index) in index:
            index.remove(len(ser_index))
            index.append(0)
    index = [ser_index[i] for i in index]
    return index


def add_rsi(__ser: pd.Series, period: int = 14):
    __ser = __ser.diff()
    up = __ser.clip(lower=0)
    down = -1 * __ser.clip(upper=0)
    ma_up = up.rolling(period).mean()
    ma_down = down.rolling(period).mean()
    rsi = ma_up / ma_down
    rsi = 100 - (100 / (1 + rsi))
    return rsi


def set_ax_lims(df, ax_):
    ax_.set_xlim((df.index[0], df.index[-1]))
    ax_.set_ylim((df.min().min(), df.max().max()))


def set_xy_labels(ax_, is_collection=True, axis_facecolor="white"):
    if not is_collection:
        ax_ = (ax_,)
    from matplotlib.widgets import MultiCursor

    cursor_reference = MultiCursor(
        canvas=None,
        axes=ax_,
        useblit=True,
        color="gray",
        horizOn=True,
    )
    for _ax in ax_:
        _ax.autoscale_view()

    from matplotlib.ticker import NullFormatter, NullLocator

    ax_[0].xaxis.set_minor_locator(NullLocator())
    ax_[0].xaxis.set_minor_formatter(NullFormatter())
    ax_[0].xaxis.set_major_locator(mdates.HourLocator())
    ax_[0].xaxis.set_major_formatter(mdates.DateFormatter("%d:%H:%M"))
    ax_[0].set_facecolor(axis_facecolor)
    for n_spine, _spine in enumerate(("top", "right", "left", "bottom")):
        for n_ax, _ax in enumerate(ax_):
            if n_spine == n_ax == len(ax_):
                continue
            _ax.spines[_spine].set_visible(False)
    return cursor_reference


class Simulate:
    def __init__(self, __send, __kill):
        """simulates a data endpoint and sends offline data through a pipe"""
        self.sender = __send
        self.control = __kill
        self.pdf = get_pdf(
            "datfiles/main2", drop_timestamp=True, raw=True, reset_index=True
        )
        # self.pdf.index = [convert(x, True) for x in self.pdf.index]
        self.send()

    def send(self):
        """receive some control signal(0) and then sends data through  a pipe"""
        counter = 150
        while self.sender.recv() == self.control:
            if counter != 150:
                try:
                    _ = self.pdf.iloc[counter - 1]
                except IndexError:
                    _ = self.control
            else:
                _ = self.pdf.iloc[:counter]
            counter += 1
            self.sender.send(_)
            if isinstance(_, int):
                return


def human_datefmpl(mpl_date):
    return mdates.num2date(mpl_date).strftime(FORMAT)


def printall():
    pd.set_option("display.max_rows", None)


def mpl2datetime2int(mpl_time):
    """convert a matplotlib date to human readable date and return  minutes in hour+minute"""
    humn_rdble = mdates.num2date(mpl_time)
    return (humn_rdble.hour * 60) + humn_rdble.minute
