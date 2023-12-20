import logging
import threading
import serial
from typing import Callable


class SerialHandler:
    """ Serial communication handler. """

    _delimiter = b"\r\n"

    def __init__(self, address: str, baudrate: int, callback: Callable):
        """ Constructor.
        :param address: Port name.
        :param baudrate: Bits per second (ej. 115200).
        :param callback: Optional callback function for message receiving.
        """
        conn = serial.Serial()
        conn.port = address
        conn.timeout = 0
        conn.baudrate = baudrate
        conn.setDTR(False)  # avoid problem with ESP32
        conn.setRTS(False)
        conn.write_timeout = 0
        self._conn = conn
        self._callback = callback
        self._close_event = threading.Event()
        self._thread = threading.Thread(target=self._recv)
        self._buffer = ''
        self._messages = []
        self.__del__ = self.close

    def start(self) -> bool:
        self.close()
        try:
            self._conn.open()
            self._close_event.clear()
            self._thread.start()
            return True
        except serial.serialutil.SerialException:
            return False

    def send(self, msg: str):
        """ Send a complete message.
        :param msg: Message without _delimiter.
        """
        self._conn.write(msg.encode() + self._delimiter)
        self._conn.flushOutput()

    def close(self):
        """Clean variables and close connections.
        """
        if self._thread.is_alive():
            self._close_event.set()
            self._thread.join()
        if self._conn.isOpen():
            self._conn.close()

    def _recv(self):
        """ Thread for message receive.
        :return: None
        """
        while not self._close_event.is_set():
            data = self._conn.read_until(self._delimiter).decode()
            if data:

                blocks = (self._buffer + data).split(self._delimiter.decode())
                self._buffer = blocks[-1]
                if len(blocks) > 1:

                    self._messages += blocks[0:-1]
                    # get message
                    while len(self._messages) > 0:
                        msg = self._messages.pop(0) if self._messages else None
                        if msg:
                            self._callback(msg)
