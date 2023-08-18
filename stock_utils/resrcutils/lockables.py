from threading import Condition, Lock
from multiprocessing import Value
from time import sleep


class TCounter:
    """A class that implement a thread-locked value"""

    def __init__(self, intial_value: int = 0, step=1):
        self.__mutex__ = Lock()
        self.__condition__ = Condition(self.__mutex__)
        self.__value__ = intial_value
        self.__step__ = step

    def get(self):
        """return the value"""
        with self.__mutex__:
            return self.__value__

    def inc(self):
        """increment the value"""
        with self.__mutex__:
            self.__value__ += self.__step__
            self.__condition__.notify_all()

    def get_inc(self):
        """return conunter's value and increment it"""
        with self.__mutex__:
            x = self.__value__
            self.__value__ += self.__step__
            self.__condition__.notify_all()
        return x

    def get_dec(self):
        """return a counter's value and decrement it"""
        with self.__mutex__:
            x = self.__value__
            self.__value__ -= self.__step__
            self.__condition__.notify_all()
        return x

    def dec(self):
        """decrement the value"""
        with self.__mutex__:
            self.__value__ -= self.__step__
            self.__condition__.notify_all()

    def set_(self, value):
        """overwrite the existing value"""
        with self.__mutex__:
            self.__value__ = value
            self.__condition__.notify_all()

    def hold_indefinetly(self, time_):
        """holds the lock indefinetly for `time_` seconds"""
        with self.__mutex__:
            sleep(time_)
            self.__condition__.notify_all


class MultipleCallError(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "A call to clear_status() should only happen once"


class PController:
    def __init__(self):
        """
        Process controller
        -----------------
        *   This class implements a multiprocessing.Value instance for controlling multiple processes.
            if Proc-A depends on Proc-B; Proc-B could ancounter an error or gracefully be terminated and
            any other processes depending on it should terminate or handle that mishappen

        Methods
        -------
           get_status():
                returns the value.
            clear_status():
                set the Value to 1. This is usually done once as another call to get_status() should
            return 1.
        *   A @Bug may cause this unwanted behaviour. An internal multiprocessing.Value is set once the first call to
         clear_status() happens. Raises MultipleCallError if another call to clear_status() is encountered.
        """

        self._signal_, self.__signal_set__ = (Value("i", 0) for _ in range(2))

    def get(self):
        return self._signal_.value

    def __set_status__(self):
        if self.__signal_set__.value:
            raise MultipleCallError

        self._signal_.value = 1
        self.__signal_set__.value = 1

    def is_set(self):
        return bool(self.__signal_set__)

    def set(self):
        value = self._signal_.value
        self.__set_status__()
        return value


class ContainerNotIterableError(Exception):
    pass


class TGenerator:
    def __init__(self, container_):
        """
        ThreadLockGenerator
        -------------------

        A class that implements  generator with a thread lock."""
        self.__mutex__ = Lock()
        self.__condition__ = Condition(self.__mutex__)
        self.update_container(container_)

    def update_container(self, container_):
        try:
            iter(container_)
            with self.__mutex__:
                self.__container__ = container_
                self.__condition__.notify_all()
        except TypeError:
            raise ContainerNotIterableError

    def get(self):
        for x in range(len(self.__container__)):
            with self.__mutex__:
                value_ = self.__container__[x]
                self.__container__ = self.__container__[x:]
                self.__condition__.notify_all()
            yield value_

    def __len__(self):
        with self.__mutex__:
            len_ = len(self.__container__)
            self.__condition__.notify_all()
        return len_


if __name__ == "__main__":
    ...
