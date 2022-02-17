import base64
import configparser
import logging
import os
from Crypto.Cipher import AES
from hashlib import md5
from .config import CONFIG_FOLDER


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


def on_credentials(ip4, agentcore_uuid, func) -> dict:
    cred = CREDENTIALS.get(ip4)
    if cred:
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

    cred = CREDENTIALS.get(None)
    if cred:
        CREDENTIALS[ip4] = cred
        return cred

    fn = os.path.join(CONFIG_FOLDER, 'defaultCredentials.ini')
    if os.path.exists(fn):
        key = get_key(agentcore_uuid)
        config = configparser.ConfigParser()
        config.read(fn)
        try:
            CREDENTIALS[None] = cred = func(config, key, decrypt)
        except Exception as e:
            logging.error(f'Credentials [{ip4}] {e}')
        else:
            return cred

    logging.warning(f'Credentials [{ip4}] missing')
