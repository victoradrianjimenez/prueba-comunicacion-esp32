import json
import logging
import time

from .com import SerialHandler


class FakeSerialHandler(SerialHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buffer_in = list()
        self.msg_index = 0
        self.msg_lst = [
            '{"origin":"NodoTest001","timestamp":204686,"class":"keepAlive"}',
            '{"origin":"NodoTest001","timestamp":326423,"class":"changedConnection","nodes":"3005803657 3005803657"}',
            '{"origin":"NodoTest001","timestamp":23319,"class":"newConnection","nodeId":3005803657}',
        ]

    def start(self) -> bool:
        self._close_event.clear()
        self._thread.start()
        return True

    def _read(self):
        """Leer datos desde el puerto (no bloqueante).
        :return: En caso de que no existan datos retorna None.
        """
        if len(self.buffer_in) > 0:
            res = self.buffer_in.pop(0)
        else:
            time.sleep(1)
            res = self.msg_lst[self.msg_index]
            self.msg_index = (self.msg_index + 1) % len(self.msg_lst)
        return res + self._delimiter

    def _write(self, msg: str):
        """Escribir datos en el puerto.
        :param msg: Cadena de caracteres.
        """
        try:
            data = json.loads(msg)
        except ValueError:
            logging.warning(f"Mensaje con formato inválido: {msg}")
            return
        response = {
            "origin": "NodoTest001",
            "timestamp": time.time_ns()//1000000,
            "class": "received",
            "origin_ts": data['timestamp']
        }
        self.buffer_in.append(json.dumps(response))
