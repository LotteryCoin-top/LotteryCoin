from __future__ import annotations

from chia.util.guess import ISSUE_HEIGHT_PER_LOTTERY
from chia.util.ints import uint32, uint64

# 1 Lottery coin = 1,000,000,000 = 1 billion mojo.
MOJO_PER_LOTTERY = 10**9
_plus_bonus = {
    3: 5,
    4: 10,
    5: 30,
    6: 60,
    7: 100,
}
_reward_per = [
    (6000000, 1),
    (12000000, 0.5),
    (18000000, 0.25),
    (24000000, 0.125),
    (50000000, 0.0625),
]


def calculate_reward(height: uint32, index: int = -1) -> float:
    _height, _reward = _reward_per[index]
    if height >= _height if index == -1 else height < _height:
        return _reward
    else:
        index += 1
        return calculate_reward(height, index)


def calculate_pool_reward(height: uint32) -> uint64:
    """
    Returns the pool reward at a certain block height. The pool earns 7/8 of the reward in each block. If the farmer
    is solo farming, they act as the pool, and therefore earn the entire block reward.
    These halving events will not be hit at the exact times
    (3 years, etc), due to fluctuations in difficulty. They will likely come early, if the network space and VDF
    rates increase continuously.
    """

    if height == 0:
        return uint64(int((7 / 8) * 50000000 * MOJO_PER_LOTTERY))
    return uint64(int((7 / 8) * calculate_reward(height, 0) * MOJO_PER_LOTTERY))


def calculate_base_farmer_reward(height: uint32) -> uint64:
    """
    Returns the base farmer reward at a certain block height.
    The base fee reward is 1/8 of total block reward

    Returns the coinbase reward at a certain block height. These halving events will not be hit at the exact times
    (3 years, etc), due to fluctuations in difficulty. They will likely come early, if the network space and VDF
    rates increase continuously.
    """

    if height == 0:
        return uint64(int((1 / 8) * 50000000 * MOJO_PER_LOTTERY))
    return uint64(int((1 / 8) * calculate_reward(height, 0) * MOJO_PER_LOTTERY))


def calculate_lottery_bonus(height: uint32) -> uint64:
    if height == 0:
        return uint64(30000000 * MOJO_PER_LOTTERY)
    reward = _plus_bonus.get(len(str(height)) - len(str(height).rstrip("0")), 0)
    return uint64(int(calculate_reward(height) * reward * ISSUE_HEIGHT_PER_LOTTERY * MOJO_PER_LOTTERY))


def calculate_stake_lock_reward(height: uint32, scale: float) -> int:
    return int(calculate_reward(height) * 4 * 4608 * scale * MOJO_PER_LOTTERY)
