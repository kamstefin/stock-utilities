import requests
import json
import os
import pandas as pd
import time
from urllib.parse import urlencode
from itertools import cycle
from stock_utils.cmnfunc import COLUMNS
import datetime
from multiprocessing import Process, Pipe, Event
from matplotlib.dates import date2num
from stock_utils import cmnfunc as cfc
from . import exceptions

URI = "https://www.bitstamp.net/api/v2/ohlc/"
PATH_ = "stock_utils/bitstamp.json"


class Uri:
    def __init__(self) -> None:
        self.params = {}
        self.cdl = self.sleep_time = self.__delay__ = None
        self.make_url()

    def __get_data__(self):
        rd = open(PATH_, "r")
        data = json.load(rd)["bitstamp"]
        assert data["exchange"]
        rd.close()
        return data

    def make_url(self):
        data = self.__get_data__()
        self.params.update(
            {
                "limit": data.pop("start_data_length"),
                "step": data.pop("sec_data_interval"),
            }
        )
        if self.params["limit"] > exceptions.LIMIT["limit"]:
            raise exceptions.LimitError(self.params["limit"])
        self.cdl = data.pop("continous_data_length")
        self.__delay__ = data.pop("delay")
        self.params.update({"start": self.get_start_epoch()})
        self.uri = f"{URI}{data.pop('exchange')}/?"

    def tweak_uri(self):
        """
        lots of useless calls to -> self.params["limit"] = self.cdl
        """
        self.params["limit"] = self.cdl
        self.params["start"] = self.get_start_epoch()

    def get_start_epoch(self):
        """
        >>> we cannot print this minute's data in this minute ):
         >>> sleep set a sleep timer until the next minute/hour/nanosecond is reached
        """
        step = self.params["step"]
        now_ = int(time.time())
        remain = now_ % step
        now_ -= remain
        self.sleep_time = (step - remain) + self.__delay__
        return now_ - (self.params["limit"] * 60)


class BFeed:
    """
    Bitstamp_Feed
    =============
    we're running this thing on a different process

    args
    ----
        interval: interval at which to query more data
    *   this instance will put new data in a queue.Queue() container
    """

    def __init__(self, sigok, sigkill: int):
        self.uri_maker = Uri()
        self.__sender__, self.recver = Pipe(duplex=True)
        self.proc_pull = None
        self.kill_event = Event()
        self.sigok, self.sigkill = sigok, sigkill
        

    def start_pull(self, run_forever: bool = False, csv_file="main1.csv"):
        """
        determine whether to run forever or not and start a process
        """
        count = range(1)
        if run_forever:
            count = cycle(count)
            self.proc_pull = Process(target=self._pull, args=(count, csv_file, True))
            self.proc_pull.start()
        else:
            self._pull(count, csv_file)

    def __pull__(self):
        data = requests.get(f"{self.uri_maker.uri}{urlencode(self.uri_maker.params)}")
        if text := data.text:
            data = json.loads(text)
            return data
        else:
            self.__sender__.send(self.sigkill)
            raise exceptions.EmptyResponseError(data.content)

    def sleep_aware(self):
        """
        sleep for specified time. wake up in between to check any kill_event if an
        exception already occurred while asleep
        """
        sleep_time = self.uri_maker.sleep_time
        done_sleeping = True
        for _ in range(sleep_time):
            time.sleep(0.5)
            if self.kill_event.is_set():
                done_sleeping = False
                break
            time.sleep(0.5)
        if done_sleeping:
            if self.__sender__.recv() == self.sigkill:
                raise exceptions.SenderError
            self.uri_maker.tweak_uri()
        return done_sleeping

    def _pull(self, count, csv_file, run_forever=False):
        """
        start the data pulling from Bitstamp and manage pauses between pulls
        """
        for _ in count:
            print(
                f"{self.uri_maker.uri}{urlencode(self.uri_maker.params)}  {datetime.datetime.now().strftime('%H:%M:%S')}"
            )
            try:
                data = self.__pull__()
                data = data["data"]["ohlc"]
                data = BFeed.json_2_pandas(data)
                self.__sender__.send(data)
                if run_forever:
                    if not self.sleep_aware():
                        return
            except (json.decoder.JSONDecodeError, KeyError):
                raise exceptions.UnkownSocketError(data)
            except requests.exceptions.ConnectionError:
                self.__sender__.send(self.sigkill)
                raise Exception("cannot reach www.bitstamp.net")

    def json_2_pandas(data_: json) -> pd.DataFrame:
        data = pd.DataFrame(data_)
        data = data.drop("volume", axis=1).iloc[:, [3, 1, 2, 0, 4]]
        data = data.applymap(float)
        data.index = (
            pd.Series(data.pop("timestamp"), name="d")
            .apply(cfc.convert)
            .apply(date2num)
        )
        data.columns = COLUMNS
        return data
