import asyncio
import logging
import os
import platform
import socket
import sys
import time
import uuid

from .protocol import Protocol

PROC_START_TS = int(time.time())
SYSTEM_ID = str(uuid.uuid1()).split('-')[-1]


class AgentCoreClient:

    def __init__(self):
        self._loop = asyncio.get_event_loop()
        self.host = None
        self.port = None
        self.connecting = False
        self.connected = False
        self._protocol = None
        self._keepalive = None
        self._checks = None
        self._on_announced = None
        self._announce_fut = None

    async def _connect(self):
        conn = self._loop.create_connection(
            lambda: Protocol(
                self.on_connection_made,
                self.on_connection_lost,
                self.on_customer_uuid,
                self.on_run_check,
            ),
            self.host,
            self.port
        )

        self.connecting = True
        try:
            _, self._protocol = await asyncio.wait_for(conn, timeout=10)
        except Exception as e:
            logging.error(f'connecting to agentcore failed: {e}')
        else:
            if self._keepalive is None or self._keepalive.done():
                self._keepalive = asyncio.ensure_future(self._keepalive_loop())

        self.connecting = False

    async def _keepalive_loop(self):
        step = 30
        while self.connected:
            await asyncio.sleep(step)
            try:
                self._protocol.send({'type': 'echoRequest'})
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(e)
                self.close()
                break

    async def _connect_loop(self):
        initial_step = 2
        step = 2
        max_step = 2 ** 7

        while 1:
            if not self.connected and not self.connecting:
                await self._connect()
                step = min(step * 2, max_step)
            else:
                step = initial_step
            await asyncio.sleep(step)

    def close(self):
        if self._keepalive is not None:
            self._keepalive.cancel()
            self._keepalive = None
        if self._protocol is not None:
            self._protocol.transport.close()
            self._protocol = None

    def on_connection_made(self):
        logging.warn('connected to agentcore')
        self.connected = True

    def on_connection_lost(self):
        logging.error('connection to agentcore lost')
        self.connected = False
        asyncio.ensure_future(self._connect_loop())

    def on_customer_uuid(self, data):
        logging.warn('announced')
        customer_uuid = data['customerUuid']
        agentcore_uuid = f'{customer_uuid}-{SYSTEM_ID}'
        if self._on_announced:
            self._on_announced(agentcore_uuid)
        self._announce_fut.set_result(agentcore_uuid)

    def send(self, msg):
        if self._protocol and self._protocol.transport:
            self._protocol.send(msg)

    def connect(self, host, port):
        self.host = host
        self.port = port
        return self._connect()

    def announce(self, probe_name, version, checks, on_announced=None):
        assert self.connected, 'not connected'
        assert self._announce_fut is None, 'already announced'
        self._checks = checks
        self._on_announced = on_announced
        self._announce_fut = fut = asyncio.Future()
        self._protocol.send({
            'type': 'probeAnnouncement',
            'hostInfo': self._get_hostinfo(),
            'platform': self._get_platform_str(),
            'versionNr': version,
            'probeName': probe_name,
            'probeProperties': ['remoteProbe'],
            'availableChecks': {
                k: {'defaultCheckInterval': v.interval} 
                for k, v in checks.items()
            },
        })
        return fut

    @staticmethod
    def _get_hostinfo():
        return {
            'timestamp': int(time.time()),
            'hostName': socket.getfqdn(),
            'osFamily': os.name,
            'platform': platform.system(),
            'ip4': socket.gethostbyname(socket.gethostname()),
            'release': platform.release(),
            'systemId': SYSTEM_ID,
            'processStartTs': PROC_START_TS
        }

    @staticmethod
    def _get_platform_str():
        platform_bits = 'x64' if sys.maxsize > 2 ** 32 else 'x32'
        return f'{platform.system()}_{platform_bits}_{platform.release()}'

    async def on_run_check(self, data):
        try:
            host_uuid = data['hostUuid']
            check_name = data['checkName']
            check_func = self._checks[check_name].run
        except Exception:
            logging.error('invalid check configuration')
            return

        t0 = time.time()
        try:
            state_data = await check_func(data)
        except Exception as e:
            logging.warning(f'on_run_check {host_uuid} {check_name} {e}')
            message = str(e)
            framework = {'timestamp': t0, 'runtime': time.time() - t0}
            self.send({
                'type': 'checkError',
                'hostUuid': host_uuid,
                'checkName': check_name,
                'message': message,
                'framework': framework,
            })
        else:
            if state_data:
                logging.debug(f'on_run_check {host_uuid} {check_name} ok!')
                framework = {'timestamp': t0, 'runtime': time.time() - t0}
                self.send({
                    'type': 'stateData',
                    'hostUuid': host_uuid,
                    'framework': framework,
                    'checkName': check_name,
                    'stateData': state_data
                })
