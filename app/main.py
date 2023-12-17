import datetime
import csv
import json
import logging
import os
import threading
import time

from .com import SerialHandler
from .fake import FakeSerialHandler


class MainApp:
    serial = '/dev/ttyACM0'
    log_filename = 'log.csv'
    baudrate = 115200

    message_period = 100  # [ms] Cada cuanto tiempo se envía un mensaje
    test_period = 3000  # [ms] El tiempo considerado para estimar la taza de pérdida de mensajes
    max_response_delay = 2000  # [ms] El tiempo máximo que se espera una respuesta.
    print_period = 1000  # [ms] Cada cuanto tiempo se imprime mensaje en pantalla

    _close_event = threading.Event()
    _com = None
    _data = list()
    _recording = False
    _writer = None
    _verbose = False

    @classmethod
    def _start_recording(cls):
        cls._data.clear()
        cls._recording = True

    @classmethod
    def _stop_recording(cls):
        cls._recording = False

    @classmethod
    def _callback_serial(cls, msg: str):
        """ Método encargado de escuchar mensajes por puerto serie.
        """
        # parsear json
        try:
            data = json.loads(msg)
        except ValueError:
            logging.warning(f"Mensaje con formato inválido: {msg}")
            return

        # procesar según sea el tipo de mensaje
        details = None
        if 'class' in data:
            if data['class'] == 'keepAlive':
                details = ''
            elif data['class'] == 'received':
                details = data['origin_ts']
            elif data['class'] == 'changedConnection':
                details = data['nodes']
            elif data['class'] == 'newConnection':
                details = data['nodeId']

        # check message validity
        if details is None:
            logging.warning(f"Mensaje no esperado: {msg}")
            return

        # completar campos faltantes
        data['tiempo'] = str(datetime.datetime.now())

        # mostrar en pantalla
        if cls._verbose:
            print(f"{data['class']} from {data['origin']} - {data['timestamp']}: {details}")

        # write a row to the csv file
        if cls._recording:
            cls._data.append(data)
            row = [data[v] for v in ('tiempo', 'origin', 'timestamp', 'class')] + [details]
            cls._writer.writerow(row)

    @classmethod
    def set_message_period(cls):
        while True:
            try:
                value = int(input('Ingresar cada cuanto tiempo se envía un mensaje [ms]: '))
                cls.message_period = value
                break
            except ValueError:
                print('Valor incorrecto.')
                continue

    @classmethod
    def set_test_period(cls):
        while True:
            try:
                value = int(input('Ingresar el tiempo considerado para la prueba [ms]: '))
                cls.test_period = value
                break
            except ValueError:
                print('Valor incorrecto.')
                continue

    @classmethod
    def set_max_response_delay(cls):
        while True:
            try:
                value = int(input('Ingresar el tiempo máximo que se espera una respuesta o timeout [ms]: '))
                cls.max_response_delay = value
                break
            except ValueError:
                print('Valor incorrecto.')
                continue

    @classmethod
    def set_print_period(cls):
        while True:
            try:
                value = int(input('Ingresar cada cuanto tiempo se imprime mensaje en pantalla [ms]: '))
                cls.print_period = value
                break
            except ValueError:
                print('Valor incorrecto.')
                continue

    @classmethod
    def test_success_ratio(cls):
        """ Enviar un mensaje al nodo de prueba y esperar su respuesta.
        """
        # tiempo inicial en milisegundos
        t = time.time_ns() // 1000000
        last_t_msg = t
        last_t_disp = t  # + test_period

        # calcular tamaño de memoria
        total_length = (cls.test_period + cls.max_response_delay) // cls.message_period  # [ms]
        test_length = cls.test_period // cls.message_period  # [ms]
        memory_pos = 0
        memory_timestamps = [None] * total_length
        memory_response = [0] * total_length

        # create message
        msg = dict(origin="Supervisor", destiny="NodoTest001")

        # start message recording
        cls._start_recording()

        # main loop
        while not cls._close_event.is_set():
            t = time.time_ns()//1000000
            # send message
            if t - last_t_msg >= cls.message_period:
                # add timestamp to buffer
                memory_timestamps[memory_pos] = t
                memory_response[memory_pos] = 0
                # update timestamp from message
                msg['timestamp'] = t
                # send message to the test node
                cls._com.send(json.dumps(msg))
                # update loop indexes
                last_t_msg += cls.message_period
                memory_pos = (memory_pos + 1) % total_length
            # check it there are messages
            while len(cls._data) > 0:
                row = cls._data.pop(0)
                # check it the current message corresponds to the response for any stored messages
                if row.get('origin', '') == msg['destiny'] and row.get('class', '') == 'received':
                    try:
                        # marcar mensaje como recibido
                        origin_ts = row['origin_ts']
                        idx = memory_timestamps.index(origin_ts)
                        memory_timestamps[idx] = None
                        memory_response[idx] = t - origin_ts
                    except (ValueError, IndexError):
                        print('Mensaje erróneo')
                        pass
            # show results
            if t - last_t_disp >= cls.print_period:
                # process
                indexes = [j % total_length for j in range(memory_pos, memory_pos + test_length)]
                n = len(indexes)

                success = [1 if memory_timestamps[j] is None else 0 for j in indexes]
                success_count = sum(success)
                success_rate = success_count / n if n > 0 else 0
                response_sum = sum(memory_response[j] for j in indexes if memory_timestamps[j] is None)
                response_time = response_sum / success_count if success_count > 0 else 0
                print(f"Success rate: {success_rate:.2f} ({success_count} of {n}) - " +
                      f"Average response time: {response_time:.2f} ms")
                last_t_disp += cls.print_period

        # dejar de guardar mensajes
        cls._stop_recording()

    @classmethod
    def ver_mensajes(cls):
        cls._verbose = True
        while not cls._close_event.is_set():
            time.sleep(0.5)
        cls._verbose = False

    @classmethod
    def run(cls, fake=False):

        # initialize variables
        error_code = None

        # instantiate the serial port handler
        handler_class = FakeSerialHandler if fake else SerialHandler
        cls._com = handler_class(cls.serial, cls.baudrate, callback=cls._callback_serial)

        header = None
        if not os.path.isfile(cls.log_filename):
            header = ['tiempo', 'origin', 'timestamp', 'class', 'details']

        # open the file in the write mode
        f = open(cls.log_filename, 'a', encoding='UTF8', newline='\n')

        # create the csv writer
        cls._writer = csv.writer(f)

        # white file header on the first time
        if header is not None:
            cls._writer.writerow(header)

        # start the serial listener
        connect = cls._com.start()
        if connect:
            try:
                while True:
                    f_map = {
                        '1': (f'Ingresar el periodo de envio de mensajes (={cls.message_period})',
                              cls.set_message_period, False),
                        '2': (f'Ingresar el periodo usado para la prueba (={cls.test_period})',
                              cls.set_test_period, False),
                        '3': (f'Ingresar el tiempo máximo de espera (={cls.max_response_delay})',
                              cls.set_max_response_delay, False),
                        '4': (f'Iniciar envio de mensajes',
                              cls.test_success_ratio, True),
                        '5': (f'Ver todos los mensajes recibidos',
                              cls.ver_mensajes, True),
                        'X': (f'Terminar', None, False)
                    }
                    for opt, val in f_map.items():
                        print(f"{opt}: {val[0]}")
                    opt = input('Ingresar una opción: ').lower()
                    if opt == 'x':
                        break
                    try:
                        function = f_map[opt][1]
                        wait = f_map[opt][2]
                        if function is None:
                            raise IndexError
                    except IndexError:
                        print('Opción incorrecta.')
                        continue
                    if wait:
                        # ejecutar subprograma
                        cls._close_event.clear()
                        thread = threading.Thread(target=function, args=tuple())
                        thread.start()
                        input('Presionar ENTER para volver al menú...\n')
                        cls._close_event.set()
                        thread.join()
                    else:
                        function()

            except KeyboardInterrupt:
                logging.info('Closing...')
        else:
            error_code = 2

        # clear serial connection
        cls._com.close()

        # close the file
        f.close()

        # exit with error code
        return error_code
