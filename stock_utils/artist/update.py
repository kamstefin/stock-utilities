import stock_utils.cmnfunc as cmn
from stock_utils.df_man import OfflineDfMan
from itertools import cycle
from stock_utils.artist.artists import candle
import matplotlib.pyplot as plt
from matplotlib import dates as mdates
from datetime import timedelta
import numpy as np


class _BlitManager:
    def __init__(self, canvas, artists: tuple):
        """
        class that manages blitting of single artists.
        simply by:
            *  add artist(s)
            *  set_altering()
            *  change the data for the artist
            *  update()
        """
        self.canvas = canvas
        self.bg_ = self.axes_ = None
        self.artists = artists

    def set_altering(self, axes_name: str, artist_index=0):
        """
        *   sets the changing artist to be animated
        *   draws the figure without the artist # sometimes slow
        *   stores the pixel buffer
        *   draw the artist internally
        *   blit the axes
        """
        artist_ = self.artists[axes_name][artist_index]
        self.axes_ = axes_ = artist_.axes
        self.bg_ = self.canvas.copy_from_bbox(axes_.bbox)
        artist_.set_animated = True
        axes_.draw_artist(artist_)
        self.canvas.blit(axes_.bbox)

    def update(self, axes_name: str, artist_index=0):
        """
        *   restore the region
        *   draw the artist alone
        *   blit the canvas
        *   persist the plot
        *"""
        artist_ = self.artists[axes_name][artist_index]
        self.canvas.restore_region(self.bg_)
        self.axes_.draw_artist(artist_)
        self.canvas.blit(self.axes_.bbox)
        artist_.set_animated = False

    def draw_idle(self):
        plt.draw()


class Updater:
    def __init__(
        self,
        controller: int,
        dfman: OfflineDfMan,
        update_size: int,
        canvas,
        artist,
        key: str,
        *update_methods,
    ) -> None:
        """
        A class that  manages update of specified artists when blitting

        args
        ----
        controller: when hovering, how much time period to elapse before the plot is updated
        key,artist,update: belongs to the plot on axes 1
        dfman: `pd.DataFrame` manager instance
        canvas: `figure.canvas` of the current figure
        update_size: length of data to update
        """
        self.artists = {key: artist}
        self.__valid_motion__ = cycle((controller,))
        self.click_data = self.direction = None
        self.dfutils = dfman
        self._int_funcs = (int.__sub__, int.__add__)
        self.ax0U = update_methods[0]
        self.ax1U = update_methods[1]
        self.bm = None
        self.canvas = canvas
        self.__update_size__ = cycle((update_size,))
        self.__minute_delta__ = timedelta(seconds=120)

    def connect(self):
        """connect useful mouse events"""
        self.con = (
            self.canvas.mpl_connect("button_press_event", self.on_press),
            self.canvas.mpl_connect("motion_notify_event", self.on_motion),
            self.canvas.mpl_connect("button_release_event", self.on_release),
        )

    def disconnect(self):
        tuple(map(self.canvas.mpl_disconnect, self.con))

    def plot_line(self, key: str, artist, ax_, **kwargs):
        """
        some artists may not be plotted before initializing the class,
        this `plot_line` function will plot an artist and add it to the collectible of the artists

        args
        ----
        key: string which is unique to eaxh axes
        artist_data: data to the artist instance
        ax_:    the axes to add the artist
        **kwargs: any addational parameter that will be passed to ax_.plot(...,**kwargs)
        """
        (artist,) = ax_.plot(artist, **kwargs)
        if key in self.artists.keys():
            self.artists[key].append(artist)
        else:
            self.artists.update({key: [artist]})

    def add_artists(self):
        """
        *   adds artist to be managed by `_Blitmanager`.
        *   called after making all needed artists.
        *   if new artists are made after this call, they -may- not be managed when blitting
        """
        self.bm = _BlitManager(self.canvas, self.artists)

    def on_press(self, event_):
        if event_.button == 1 and event_.inaxes:
            self.click_data = event_.xdata
            if event_.dblclick:
                print(self.dfutils.find_index(self.click_data))

    def on_release(self, _):
        self.click_data = self.direction = None

    def on_motion(self, event_):
        if not event_.inaxes:
            self.on_release(None)
        if self.click_data:
            direction = event_.xdata - self.click_data
            time_int = cmn.mpl2datetime2int(abs(direction))
            if time_int > next(self.__valid_motion__):
                self.click_data = None
                self.direction = 1 if direction < 0 else 0
                xlim = list(event_.inaxes.get_xlim())
                xlim[1] = mdates.date2num(
                    mdates.num2date(xlim[1]) - self.__minute_delta__
                )
                if cindex := self.set_new_xlim(self.dfutils.get_ilocs(xlim)):
                    self.update_artists(cindex)

    def _to_remove(self, cindex: list):
        """find date2num indexes that will be removed"""
        index_new_data = [cindex[x][self.direction] for x in range(1, -1, -1)]
        toremove = [x[int(not self.direction)] for x in (cindex[1], cindex[0])]
        if self.direction:
            index_new_data = index_new_data[::-1]
            index_new_data[1] += 1
            toremove = toremove[::-1]
        return toremove, index_new_data

    def update_artists(self, cindex):
        """calls every artist manager's update method with required arguments"""
        self._ax0(cindex)
        self._ax1nax2nax3(cindex)
        self.bm.draw_idle()

    def _ax_axis(self, cindex, which_: int):
        lim = self.dfutils.get_locs(cindex[1])
        lim[1] = mdates.date2num(mdates.num2date(lim[1]) + self.__minute_delta__)
        self.artists["ax0"][which_].axes.set_xlim(lim)
        if lim := self.dfutils.get_ylims(cindex[1]):
            self.artists["ax0"][which_].axes.set_ylim(lim)

    def validate_n_call(self, axes: str, index: int, data, func, *args):
        if data:
            artist_ = self.artists[axes][index]
            if artist_:
                self.bm.set_altering(axes, index)
                self.artists[axes][index].set_path(data)
                self.bm.update(axes, index)
            else:
                self.artists[axes][index] = func(data, *args)

    def _ax0(self, cindex):
        to_remove, index_new_data = self._to_remove(cindex)
        df = self.dfutils.get_data(index_new_data)
        to_remove = self.dfutils.get_locs(range(to_remove[0], to_remove[1]))
        red, green = self.ax0U.update(self.direction, df, to_remove)
        self.validate_n_call("ax0", 0, red, self.ax0U.make_new, candle.RED)
        self.validate_n_call("ax0", 1, green, self.ax0U.make_new, candle.GREEN)
        self._ax_axis(cindex, 0) if red else self._ax_axis(cindex, 1)

    @staticmethod
    def _general_limit(ax_art):
        """return the limit(min(min(x)),max(max(y)))"""
        return (min([x.min() for x in ax_art]), max([x.max() for x in ax_art]))

    def _general_axis(self, ax_art, key: str):
        self.bm.set_altering(key, 0)
        self.bm.set_altering(key, 1)
        self.artists[key][0].set_data((ax_art[0].index, ax_art[0].values))
        self.artists[key][1].set_data((ax_art[1].index, ax_art[1].values))
        lim = self._general_limit(ax_art)
        if all(lim) and not all(
            [all([not lim[x] > 0, not lim[x] < 0]) for x in range(2)]
        ):
            self.artists[key][0].axes.set_ylim(lim)
        self.bm.update(key, 0)
        self.bm.update(key, 1)

    def _ax1nax2nax3(self, cindex):
        cindex = cindex[1]
        cindex[1] += 1
        if cindex[0]>100:
            cindex[0]-=100
        data = self.dfutils.get_data(cindex)
        self.ax1U.set_df(data)
        ax1_art, ax2_art = self.ax1U.update()

        self._general_axis(ax1_art, "ax1")
        self._general_axis(ax2_art, "ax2")

    def _ax3(self, data):
        ...

    def set_new_xlim(self, xlim):
        """set the new xlimits and return old xlimits"""
        change = xlim.copy()
        index = [
            self._int_funcs[self.direction](i, j)
            for i, j in zip(xlim, self.__update_size__)
        ]
        validated = self.validate_xlim(index, change[1])
        change = [change, index]
        if validated[0]:
            if validated[1]:
                validated = validated[1]
                change[1][0] -= validated
                change[1][1] -= validated
        else:
            change = False
        return change

    def validate_xlim(self, index: list, last_):
        """validate whether new index in range of global index"""
        max_index = self.dfutils.max_index
        available_size = None
        val = True
        if not all([max(0, index[x]) for x in range(2)]):
            val = False
        if index[1] > max_index:
            if last_ < max_index:
                val = True
                available_size = index[1] - max_index
            else:
                val = False
        return val, available_size
