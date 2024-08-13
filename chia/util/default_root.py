from __future__ import annotations

import os
from pathlib import Path

DEFAULT_ROOT_PATH = Path(os.path.expanduser(os.getenv("LOTTERY_ROOT", "~/.lottery/mainnet"))).resolve()

DEFAULT_KEYS_ROOT_PATH = Path(os.path.expanduser(os.getenv("LOTTERY_KEYS_ROOT", "~/.lottery_keys"))).resolve()

SIMULATOR_ROOT_PATH = Path(os.path.expanduser(os.getenv("LOTTERY_SIMULATOR_ROOT", "~/.lottery/simulator"))).resolve()
