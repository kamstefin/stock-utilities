import numpy as np
from matplotlib.path import Path
from matplotlib.patches import PathPatch
import pandas as pd
from matplotlib.path import Path
from matplotlib import pyplot as plt
from matplotlib.axes._axes import Axes
import matplotlib.dates as m_dates

# plt.style.use("dark_background")
M_KWARGS = {"lw": 1, "fill": None, "alpha": 1}
RECT_WIDTH = 0.0003
CANDLE_PATCH_COUNT = 9
RED, GREEN = "#ff2d21", "green"


class Candle:
    """
       simple trail for making 2 mega candles, red and green candles:
    >>> red,green=separate_df(df)
    >>> for x in (red,green):
        >>> vnc=make_vertices_and_codes(x)
        >>> axes.add_patch(PathPatch(Path(vnc[0],vnc[1])))
    """

    class _MegaCandle:
        def __init__(self):
            """
            ::

                d0 d1 d2
                ........
                 d|        --------->p0
                  |
                 c|
                b----e     --------->p1
                |    |
                |    |
                |    |
                a----f     --------->p2
                 g|
                  |
                 h|        --------->p3
            """
            self.__codes__, self.__vertices__ = [1, 2, 2, 2, 2, 1, 2, 1, 2], None
            self._c = self.__codes__.copy()

        def __add__(self, vertices: tuple[list, list]):
            p, d = vertices
            new_vertices = [
                (d[0], p[2]),
                (d[0], p[1]),
                (d[2], p[1]),
                (d[2], p[2]),
                (d[0], p[2]),
                (d[1], p[3]),
                (d[1], p[2]),
                (d[1], p[0]),
                (d[1], p[1]),
            ]
            if self.__vertices__ is None:
                self.__vertices__ = new_vertices
                return
            else:
                self.__vertices__ += new_vertices
            self.__codes__ += self._c

        def __sub__(self):
            self.__vertices__, self.__codes__ = None, self._c

        def get_mega_candle(self):
            return self.__vertices__, self.__codes__

    def make_verts_n_codes(pdf: pd.DataFrame, openvsclose):
        y = "o" if openvsclose else "c"
        i0 = pd.Series(pdf.index)
        p = (pdf["h"], abs(pdf["o"] - pdf["c"]) + pdf[y], pdf[y], pdf["l"])
        d = (i0, i0 + (RECT_WIDTH / 2), i0 + RECT_WIDTH)
        micro_candle = Candle._MegaCandle()
        for x in range(pdf.shape[0]):
            micro_candle + ([e.iloc[x] for e in p], [e.iloc[x] for e in d])
        vnc = micro_candle.get_mega_candle()
        return vnc

    def _sep_df(pdf: pd.DataFrame):
        cgo = pdf["c"] >= pdf["o"]
        ogc = cgo[cgo == False].index
        cgo = cgo[cgo == True].index
        return ogc, cgo

    def make_raw_paths(pdf: pd.DataFrame):
        ogc, cgo = Candle._sep_df(pdf)
        red = green = None
        if not ogc.empty:
            red = Candle.make_verts_n_codes(pdf.loc[ogc], 0)
        if not cgo.empty:
            green = Candle.make_verts_n_codes(pdf.loc[cgo], 1)
        return red, green

    def make_candles(
        pdf: pd.DataFrame, ax_: Axes = None
    ) -> tuple[PathPatch, PathPatch]:
        """
        returns a tuple of  2 PathPatches containing candles for data provided -> (bear_patch,bull_patch)/(red,green)
        if ax_ : candles are added to ax
        """
        from time import perf_counter as pf

        x = pf()
        red, green = Candle.make_raw_paths(pdf)
        if red:
            red = PathPatch(Path(*red), ec=RED, **M_KWARGS)
        if green:
            green = PathPatch(Path(*green), ec=GREEN, **M_KWARGS)
        patches = (red, green)
        if ax_:
            patches = [
                ax_.add_patch(patch) if patch is not None else None for patch in patches
            ]
        print(f"adding candle patches: {pf()-x:.4f}s")
        return patches


class Update:
    KEY_ = ("e", "u")  # KEY=("b-e-ar","b-u-ll")

    def __init__(
        self, patches: tuple[PathPatch, PathPatch], index: list, update_len, fig, axe_
    ):
        self._index = index[1] - index[0]
        self.__controller__ = update_len
        self.patches = dict(zip(Update.KEY_, patches))
        self.fig = fig
        self.axe = axe_
        self.__update_patch_data__()

    def __update_patch_data__(self):
        """update a simple array for keeping starting indexes for  `1` single candle"""
        self.patch_data = dict(
            zip(
                Update.KEY_,
                (
                    x.get_path().vertices[:, 0][::CANDLE_PATCH_COUNT] if x else None
                    for x in self.patches.values()
                ),
            )
        )

    def update(self, direction: int, data: pd.DataFrame, to_remove: list) -> None:
        """updates Pathpatches from index according to direction with data"""
        self.__update_patch_data__()
        olde, oldu = self.get_unchanged_patch(direction, to_remove)
        add2 = Candle.make_raw_paths(data)
        red, green = Update.append_(olde, oldu, add2, direction)
        # redc, greenc = [len(x.codes) / CANDLE_PATCH_COUNT for x in (red, green)]
        # print(f"(+) red codes: {redc}\tgreen codes: {greenc}\ttotal: {redc+greenc}")
        return red, green

    def make_new(self, data, color):
        return self.axe.add_patch(PathPatch(data, color=color, **M_KWARGS))

    def append_(olde, oldu, add2, direction):
        """appends new data to the original one
        olde & oldu contains red and green old data respectively while
        add2 contains new data."""
        newe, newu = add2
        if olde:
            if newe:
                if direction:
                    new, old = olde, newe
                else:
                    new, old = newe, olde
                red = [np.append(new[x], old[x], axis=0) for x in range(2)]
            else:
                red = olde
        else:
            red = newe
        if oldu:
            if newu:
                if direction:
                    new, old = oldu, newu
                else:
                    new, old = newu, oldu
                green = [np.append(new[x], old[x], axis=0) for x in range(2)]
            else:
                green = oldu
        else:
            green = newu
        if red:
            red = Path(*red)
        if green:
            green = Path(*green)
        return red, green

    def get_unchanged_patch(
        self, direction, to_remove
    ) -> tuple[tuple[list, tuple], tuple[list, tuple]]:
        """returns the vert and codes for the paths that will remain unchanged"""
        u_remove = len(set(to_remove).intersection(self.patch_data["u"]))
        e_remove = len(to_remove) - u_remove
        e_remove, u_remove = (
            e_remove * CANDLE_PATCH_COUNT,
            u_remove * CANDLE_PATCH_COUNT,
        )
        olde = oldu = None
        if direction:
            if e_remove:
                el = e_remove
            else:
                el = 0
            el = slice(el, None, 1)
            if u_remove:
                ul = u_remove
            else:
                ul = 0
            ul = slice(ul, None, 1)
        else:
            if e_remove:
                el = -e_remove
            else:
                el = None
            el = slice(0, el, 1)
            if u_remove:
                ul = -u_remove
            else:
                ul = None
            ul = slice(0, ul, 1)
        if eraw := self.patches["e"]:
            eraw = eraw.get_path()
            olde = eraw.vertices.__getitem__(el), eraw.codes.__getitem__(el)
        if uraw := self.patches["u"]:
            uraw = uraw.get_path()
            oldu = uraw.vertices.__getitem__(ul), uraw.codes.__getitem__(ul)
        return olde, oldu


if __name__ == "__main__":
    ...
