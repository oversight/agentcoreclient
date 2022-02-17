import base64
import configparser
import logging
import os
from Crypto.Cipher import AES
from hashlib import md5
from .config import CONFIG_FOLDER


CREDENTIALS_FB_KEY = None
CREDENTIALS = {}


def get_key(agentcore_uuid):
    flipped = 'tt{0}'.format(agentcore_uuid[::-1]).encode('utf-8')
    return md5(flipped).hexdigest().encode('utf-8')


def unpad(s):
    return s[0:-bytearray(s)[-1]]


def decrypt(key, data):
    enc = base64.b64decode(data)
    iv = enc[:AES.block_size]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    dec = cipher.decrypt(enc[AES.block_size:])
    return unpad(dec).decode('utf-8')


def on_credentials(host_uuid, ip4, agentcore_uuid, func) -> dict:
    cred = CREDENTIALS.get(host_uuid)
    if cred:
        return cred
    fn = os.path.join(CONFIG_FOLDER, f'{host_uuid}.ini')
    if os.path.exists(fn):
        key = get_key(agentcore_uuid)
        config = configparser.ConfigParser()
        config.read(fn)
        try:
            CREDENTIALS[host_uuid] = cred = func(config, key, decrypt)
        except Exception as e:
            logging.error(f'Credentials [{ip4}] {e}')
        return cred

    cred = CREDENTIALS.get(ip4)
    if cred:
        # make sure next time this will be found for host_uuid
        CREDENTIALS[host_uuid] = cred
        return cred
    fn = os.path.join(CONFIG_FOLDER, f'{ip4}.ini')
    if os.path.exists(fn):
        key = get_key(agentcore_uuid)
        config = configparser.ConfigParser()
        config.read(fn)
        try:
            CREDENTIALS[ip4] = cred = func(config, key, decrypt)
        except Exception as e:
            logging.error(f'Credentials [{ip4}] {e}')
        return cred

    cred = CREDENTIALS.get(CREDENTIALS_FB_KEY)
    if cred:
        # make sure next time this will be found for host_uuid
        CREDENTIALS[host_uuid] = cred
        return cred

    fn = os.path.join(CONFIG_FOLDER, 'defaultCredentials.ini')
    if os.path.exists(fn):
        key = get_key(agentcore_uuid)
        config = configparser.ConfigParser()
        config.read(fn)
        try:
            CREDENTIALS[CREDENTIALS_FB_KEY] = cred = func(config, key, decrypt)
        except Exception as e:
            logging.error(f'Credentials [{ip4}] {e}')
        else:
            return cred

    logging.warning(f'Credentials [{ip4}] missing')
