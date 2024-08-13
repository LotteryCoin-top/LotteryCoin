from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from chia.types.blockchain_format.sized_bytes import bytes32
from chia.types.stake_record import get_stake_value
from chia.util.ints import uint16, uint64
from chia.util.streamable import Streamable, streamable


@streamable
@dataclass(frozen=True)
class StakeMetadata(Streamable):
    stake_type: uint16
    recipient_puzzle_hash: bytes32

    @property
    def time_lock(self) -> uint64:
        return get_stake_value(self.stake_type).time_lock


class StakeVersion(IntEnum):
    V1 = uint16(1)


@streamable
@dataclass(frozen=True)
class AutoWithdrawStakeSettings(Streamable):
    enabled: bool = False
    tx_fee: uint64 = uint64(0)
    batch_size: uint16 = uint16(50)
