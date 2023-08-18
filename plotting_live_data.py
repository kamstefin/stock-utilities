from stock_utils.data_pull.bitstamp import datafeed
from stock_utils.df_man import OnlineDFman
from matplotlib import pyplot as plt
from stock_utils import cmnfunc as cfc
from stock_utils.artist.artists import candle, common_artists
from stock_utils.artist.update import Updater
from select import select
import json
import matplotlib.pyplot as plt


SIGKILL = 1
SIGOK = 0
VALID_MOTION = 5
UPDATE_SIZE = 100
bitstamp = datafeed.BFeed(SIGOK, SIGKILL)
bitstamp.start_pull(run_forever=True)
dfm = OnlineDFman(bitstamp.recver, SIGOK, SIGKILL)

select((bitstamp.recver,), [], [])

plt.style.use("dark_background")
index = [0, 300]
fig, ax = plt.subplots(
    3,
    1,
    figsize=(9, 10),
    layout="constrained",
    sharex=True,
    gridspec_kw={"height_ratios": [4, 2, 2]},
)

ax[0].set_title(json.load(open("stock_utils/bitstamp.json", "r"))["bitstamp"]["exchange"])

pdf = dfm.pdf.copy()
candles = candle.Candle.make_candles(pdf.iloc[index[0] : index[1]], ax[0])
candleu = candle.Update(candles, index, UPDATE_SIZE, fig, ax[0])
carts = common_artists.CArtists(pdf)
upd = Updater(
    VALID_MOTION, dfm, UPDATE_SIZE, fig.canvas, candles, "ax0", candleu, carts
)

upd.connect()

# adding some line2d artists such as macd
x, y = carts.ax1()
upd.plot_line("ax1", x, ax[1], lw=0.8)
upd.plot_line("ax1", y, ax[1], lw=0.8)
ax[1].set_ylim(upd._general_limit((x, y)))

# adding some line2d artists such as stoch
x, y = carts.ax2()
upd.plot_line("ax2", x, ax[2], lw=0.8)
upd.plot_line("ax2", y, ax[2], lw=0.8)
ax[2].set_ylim(upd._general_limit((x, y)))

upd.add_artists()
ax[0].set_ylim(dfm.get_ylims(index))
ax[0].set_xlim(dfm.get_locs(index))

cursor = cfc.set_xy_labels(ax, axis_facecolor="#000000")
plt.show()


def close():
    bitstamp.__sender__.send(SIGKILL)
    bitstamp.kill_event.set()


close()
