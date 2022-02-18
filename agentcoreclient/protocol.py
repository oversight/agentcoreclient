import asyncio
import json
import logging


class Protocol(asyncio.Protocol):

    def __init__(
        self,
        on_connection_made,
        on_connection_lost,
        on_run_check,
    ):
        self._on_connection_made = on_connection_made
        self._on_connection_lost = on_connection_lost
        self._on_run_check = on_run_check
        self.transport = None
        self.buffer = None

    def connection_made(self, transport):
        self.transport = transport
        self._on_connection_made()

    def connection_lost(self, reason):
        self.transport = None
        self.buffer = None
        self._on_connection_lost()

    def on_run_check(self, data):
        asyncio.ensure_future(self._on_run_check(data))

    def data_received(self, data):
        both = self.buffer + data if self.buffer else data
        if b'\r\n' not in data:
            self.buffer = both
            return
        msgs = both.split(b'\r\n')
        last = msgs.pop()
        self.buffer = last if last else None
        for msg in msgs:
            if not msg:
                continue
            loaded = json.loads(msg, encoding='utf-8')
            tp = loaded.get('type')
            if tp is None:
                logging.warning('invalid message')

            elif tp not in self.PROTO_MAP:
                logging.warning(f'unsupported message type: {tp}')

            else:
                self.PROTO_MAP[loaded['type']](self, loaded)

    def send(self, msg):
        self.transport.write(json.dumps(msg).encode() + b'\r\n')

    PROTO_MAP = {
        'echoRequest': lambda p, _: p.send({'type': 'echoResponse'}),
        'echoResponse': lambda *args: None,
        'customerUuid': lambda *args: None,  # received when announced
        'runCheck': on_run_check,
    }
