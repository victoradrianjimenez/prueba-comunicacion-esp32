import logging
import threading
import serial
from typing import Callable


class SerialHandler:
    """ Serial communication handler. """

    _delimiter = "\r\n"

    def __init__(self, address: str, baudrate: int, callback: Callable):
        """ Constructor.
        :param address: Port name.
        :param baudrate: Bits per second (ej. 115200).
        :param callback: Optional callback function for message receiving.
        """
        conn = serial.Serial()
        conn.port = address
        conn.timeout = 1
        conn.baudrate = baudrate
        conn.setDTR(False)  # avoid problem with ESP32
        conn.setRTS(False)
        self._conn = conn
        self._callback = callback
        self._close_event = threading.Event()
        self._thread = threading.Thread(target=self._recv)
        self._buffer = ''
        self._messages = []
        self.__del__ = self._clean

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
        self._write(msg + self._delimiter)

    def close(self):
        """Close the port.
        """
        self._clean()

    def _read(self):
        """Leer datos desde el puerto (no bloqueante).
        :return: En caso de que no existan datos retorna None.
        """
        try:
            d = self._conn.read_until(self._delimiter)
            return d.decode()
        except UnicodeDecodeError:
            logging.warning(f"Some characters can't be decoded from serial.")
        except serial.serialutil.SerialException:
            logging.warning(f"Serial exception.")
        return None

    def _write(self, msg: str):
        """Escribir datos en el puerto.
        :param msg: Cadena de caracteres.
        """
        self._conn.write(msg.encode())

    def _recv(self):
        """ Thread for message receive.
        :return: None
        """
        while not self._close_event.is_set():
            data = self._read()
            if data:
                blocks = (self._buffer + data).split(self._delimiter)
                self._buffer = blocks[-1]
                if len(blocks) > 1:
                    self._messages += blocks[0:-1]
                    # get message
                    msg = self._messages.pop(0) if self._messages else None
                    if msg:
                        self._callback(msg)

    def _clean(self):
        """Clean variables and close connections.
        """
        if self._thread.is_alive():
            self._close_event.set()
            self._thread.join()
        if self._conn.isOpen():
            self._conn.close()
