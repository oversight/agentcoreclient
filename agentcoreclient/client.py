import asyncio
import json
import logging
import os
import platform
import socket
import sys
import time
import uuid
from typing import Optional, Callable

from .config import CONFIG_FN
from .config import get_asset_config
from .logger import setup_logger
from .protocol import Protocol

PROC_START_TS = int(time.time())
SYSTEM_ID = str(uuid.uuid1()).split('-')[-1]


class AgentCoreClient:

    def __init__(
        self,
        probe_name: str,
        version: str,
        checks: dict,
        read_asset_config: Optional[Callable] = None,
        config_fn: Optional[str] = None
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
        self._required_services = [
            c.__name__
            for c in checks.values()
            if getattr(c, 'required', False)
        ]

        config_fn = CONFIG_FN or config_fn
        config = json.load(open(config_fn)) if config_fn and \
            os.path.exists(config_fn) else {}
        self.host = os.getenv(
            'OS_AGENTCORE_IP',
            config.get('agentCoreIp', 'localhost'))
        self.port = int(os.getenv(
            'OS_AGENTCORE_PORT',
            config.get('agentCorePort', 7211)))

    @staticmethod
    def setup_logger(log_level: str = 'warning', log_colorized: bool = False):
        setup_logger(log_level, log_colorized)

    async def _connect(self):
        conn = self._loop.create_connection(
            lambda: Protocol(
                self.on_connection_made,
                self.on_connection_lost,
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
            self._announce()

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

    async def connect_loop(self):
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
        logging.warning('connected to agentcore')
        self.connected = True

    def on_connection_lost(self):
        logging.error('connection to agentcore lost')
        self.connected = False

    def send(self, msg):
        if self._protocol and self._protocol.transport:
            self._protocol.send(msg)

    def _announce(self):
        self._protocol.send({
            'type': 'probeAnnouncement',
            'hostInfo': self._get_hostinfo(),
            'platform': self._get_platform_str(),
            'versionNr': self._probe_version,
            'probeName': self._probe_name,
            'probeProperties': ['remoteProbe'],
            'availableChecks': {
                k: {
                    'defaultCheckInterval': v.interval,
                    'requiredServices': self._required_services,
                } for k, v in self._checks.items()
            },
        })

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

    @staticmethod
    def _get_framework(check, start_time: float, is_available: bool):
        framework = {
            'timestamp': start_time,
            'runtime': time.time() - start_time
        }
        if getattr(check, 'required', False):
            msg = 'OK' if is_available else 'see check error(s) for details'
            framework['serviceInfo'] = {'services': {check.__name__: {
                'available': is_available,
                'reportedBy': check.__name__,
                'serviceInfoMsg': msg,
                'hasDependingChecks': True
            }}}
        return framework

    async def on_run_check(self, data):
        try:
            asset_id = data['hostUuid']
            asset_config = data['hostConfig']
            check_name = data['checkName']
            agentcore_uuid = asset_config['parentCore']
            config = asset_config['probeConfig'][self._probe_name]
            ip4 = config.get('ip4')
            check = self._checks[check_name]
        except Exception:
            logging.error('invalid check configuration')
            return

        cred: Optional[dict] = self._on_asset_config and get_asset_config(
            asset_id, ip4, agentcore_uuid, self._on_asset_config)

        t0 = time.time()
        try:
            state_data = await check.run(data, cred)
        except Exception as e:
            logging.warning(f'on_run_check {asset_id} {check_name} {e}')
            message = str(e)
            framework = self._get_framework(check, t0, is_available=False)
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
                framework = self._get_framework(check, t0, is_available=True)
                self.send({
                    'type': 'stateData',
                    'hostUuid': asset_id,
                    'framework': framework,
                    'checkName': check_name,
                    'stateData': state_data
                })
