import json
import os


CONFIG_FOLDER = os.getenv('OS_CONFIG_FOLDER', '/etc')
CONFIG_FN = os.path.join(CONFIG_FOLDER, 'wmiProbe-config.json')
CONFIG = json.load(open(CONFIG_FN)) if os.path.exists(CONFIG_FN) else {}
