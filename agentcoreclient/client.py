import asyncio
import json
import logging
import os
import platform
import socket
import sys
import time

from .config import CONFIG_FN
from .config import get_asset_config
from .logger import setup_logger
from .protocol import Protocol

PROC_START_TS = int(time.time())


class AgentCoreClient:

    def __init__(
        self,
        probe_name: str,
        version: str,
        checks: list,
        read_asset_config=None,
        config_fn=None
    ):
        self._loop = asyncio.get_event_loop()
        self.connecting = False
        self.connected = False
        self._protocol = None
        self._keepalive = None
        self._on_asset_config = read_asset_config
        self._probe_name = probe_name
        self._probe_version = version
        self._checks = checks
        self._announce_fut = None

        config_fn = CONFIG_FN or config_fn
        config = json.load(open(config_fn)) if config_fn and \
            os.path.exists(config_fn) else {}
        self.host = os.getenv(
            'OS_AGENTCORE_IP',
            config.get('agentcoreIp', 'localhost'))
        self.port = int(os.getenv(
            'OS_AGENTCORE_PORT',
            config.get('agentcorePort', 7211)))

    @staticmethod
    def setup_logger(args):
        setup_logger(args)

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
        self._announce_fut.set_result(None)

    def send(self, msg):
        if self._protocol and self._protocol.transport:
            self._protocol.send(msg)

    def connect(self):
        return self._connect()

    def announce(self):
        assert self.connected, 'not connected'
        assert self._announce_fut is None, 'already announced'
        self._announce_fut = fut = asyncio.Future()
        self._protocol.send({
            'type': 'probeAnnouncement',
            'hostInfo': self._get_hostinfo(),
            'platform': self._get_platform_str(),
            'versionNr': self._probe_version,
            'probeName': self._probe_name,
            'probeProperties': ['remoteProbe'],
            'availableChecks': {
                k: {'defaultCheckInterval': v.interval}
                for k, v in self._checks.items()
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
            'processStartTs': PROC_START_TS
        }

    @staticmethod
    def _get_platform_str():
        platform_bits = 'x64' if sys.maxsize > 2 ** 32 else 'x32'
        return f'{platform.system()}_{platform_bits}_{platform.release()}'

    async def on_run_check(self, data):
        try:
            asset_id = data['hostUuid']
            check_name = data['checkName']
            agentcore_uuid = data['hostConfig']['parentCore']
            config = data['hostConfig']['probeConfig'][self._probe_name]
            ip4 = config['ip4']
            check_func = self._checks[check_name].run
        except Exception:
            logging.error('invalid check configuration')
            return

        cred = self._on_asset_config and get_asset_config(
            asset_id, ip4, agentcore_uuid, self._on_asset_config)

        t0 = time.time()
        try:
            state_data = await check_func(data, cred)
        except Exception as e:
            logging.warning(f'on_run_check {asset_id} {check_name} {e}')
            message = str(e)
            framework = {'timestamp': t0, 'runtime': time.time() - t0}
            self.send({
                'type': 'checkError',
                'hostUuid': asset_id,
                'checkName': check_name,
                'message': message,
                'framework': framework,
            })
        else:
            if state_data:
                logging.debug(f'on_run_check {asset_id} {check_name} ok!')
                framework = {'timestamp': t0, 'runtime': time.time() - t0}
                self.send({
                    'type': 'stateData',
                    'hostUuid': asset_id,
                    'framework': framework,
                    'checkName': check_name,
                    'stateData': state_data
                })
