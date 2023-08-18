from matplotlib import pyplot as plt
from stock_utils.artist.artists import candle, common_artists
import stock_utils.cmnfunc as cfc
import pandas as pd
from stock_utils import df_man
from stock_utils.artist.update import Updater


VALID_MOTION = 5
UPDATE_SIZE = 100
plt.style.use("dark_background")

index = [0,300]
fig, ax = plt.subplots(
    3,
    1,
    figsize=(40, 20),
    layout="constrained",
    sharex=True,
    gridspec_kw={"height_ratios": [4, 2, 2]},
)


pdf = cfc.get_pdf("btc.csv", date_2_num=True, drop_timestamp=True)
dfm = df_man.OfflineDfMan(pdf)
candles = candle.Candle.make_candles(pdf.iloc[index[0] : index[1]], ax[0])
candleu = candle.Update(candles, index, UPDATE_SIZE, fig, ax[0])
carts = common_artists.CArtists(pdf.iloc[index[0] : index[1]])
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

ax[0].set_xlim(dfm.get_locs(index))
ax[0].set_ylim(dfm.get_ylims(index))

cursor = cfc.set_xy_labels(ax, axis_facecolor="#000000")
plt.show()
