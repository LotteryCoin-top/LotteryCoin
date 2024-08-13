from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict

from chia_rs import Coin

from chia.consensus.block_rewards import MOJO_PER_LOTTERY
from chia.consensus.coinbase import create_stake_reward_coin
from chia.consensus.constants import ConsensusConstants
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.util.ints import uint16, uint64, uint32
from chia.util.streamable import Streamable, streamable

STAKE_LOCK_MIN_MOJO = 1000 * MOJO_PER_LOTTERY
MOJO_PER_FEE = int(0.1 * MOJO_PER_LOTTERY)


@streamable
@dataclass(frozen=True)
class StakeValue(Streamable):
    time_lock: uint64
    coefficient: str

    def stake_amount(self, amount: uint64) -> int:
        return int(int(amount) * float(self.coefficient) * MOJO_PER_LOTTERY)


@streamable
@dataclass(frozen=True)
class StakeRecord(Streamable):
    name: bytes32
    puzzle_hash: bytes32
    amount: uint64
    confirmed_index: uint32
    spent_index: uint32
    stake_type: uint16
    coefficient: str
    expiration: uint64


STAKE_LOCK_LIST: List[StakeValue] = [
    StakeValue(86400 * 7, "1"),
    StakeValue(86400 * 30, "1.05"),
    StakeValue(86400 * 90, "1.1"),
    StakeValue(86400 * 180, "1.2"),
    StakeValue(86400 * 365, "1.3"),
    StakeValue(86400 * 730, "1.4"),
    StakeValue(86400 * 1095, "1.5"),
    StakeValue(86400 * 1825, "1.6"),
    StakeValue(86400 * 3650, "1.7"),
    StakeValue(86400 * 5475, "1.8"),
    StakeValue(86400 * 7300, "1.9"),
    StakeValue(86400 * 10950, "2"),
]


def get_stake_value(stake_type: uint16) -> StakeValue:
    if 0 <= stake_type < len(STAKE_LOCK_LIST):
        return STAKE_LOCK_LIST[stake_type]
    return StakeValue(0, "0", None)


def create_stake_lock_rewards(
    constants: ConsensusConstants,
    records: Dict[bytes32, int],
    height: uint32,
) -> List[Coin]:
    stake_rewards: List[Coin] = []
    for puzzle_hash in records:
        stake_coin = create_stake_reward_coin(
            height,
            puzzle_hash,
            uint64(records[puzzle_hash]),
            constants.GENESIS_CHALLENGE,
        )
        stake_rewards.append(stake_coin)
    return stake_rewards
