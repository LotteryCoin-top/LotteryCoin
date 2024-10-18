from __future__ import annotations

import json
from decimal import Decimal
from typing import Tuple, Optional, Dict, Any, List

from chia.types.blockchain_format.sized_bytes import bytes32
from chia.util.ints import uint64, uint32


MOJO_PER_LOTTERY = 10**9
ISSUE_HEIGHT_PER_LOTTERY = 1000
GUESS_PUZZLE_HASH = [
    bytes32.fromhex("f72c5b7a4f1990f2397a19d1d5b9cbf734defd3251058f431f0bede7b571afa7"),
    bytes32.fromhex("5c7ef82730a096d61194bce8d72608c6b65a71dd0b71fab5c47c3ec2ec68940e"),
    bytes32.fromhex("2d38f908764d3204f97332b9a100f4f9b7311828c024c632a12461e25e33d76c"),
    bytes32.fromhex("e5ef533650cc246bb915361f4c9263f5a38158ace9cb45e964f33af499d2d86e"),
]


def check_manage_memos(peak_height: uint32) -> bytes32:
    key = get_guess_issue(peak_height) % 1000
    return GUESS_PUZZLE_HASH[-1 if key >= len(GUESS_PUZZLE_HASH) else key]


def get_guess_height(peak_height: uint32, curr: bool = True) -> uint32:
    return uint32(get_guess_issue(peak_height, curr) * ISSUE_HEIGHT_PER_LOTTERY)


def get_guess_issue(peak_height: uint32, curr: bool = True) -> int:
    return max(peak_height - 1, 0) // ISSUE_HEIGHT_PER_LOTTERY + (1 if curr else 0)


def generate_bets(header_hash_num, position) -> List[int]:
    bets_list, bets_keys_list = [], []
    header_hash_num_len = len(header_hash_num)
    bets_keys = {4: 0, 3: 1, 2: 2}
    bets_data = [0, 0, 0]

    def dfs(n, start, combination, combination_key):
        if len(combination) == n:
            bets_list.append(combination[:])
            bets_keys_list.append(combination_key[:])
            return
        for k in range(start, header_hash_num_len):
            dfs(n, k + 1, combination + [header_hash_num[k]], combination_key + [k])

    for i in range(2, header_hash_num_len + 1):
        dfs(i, 0, [], [])

    for index, nums in enumerate(bets_list):
        bets = 1
        current_bets_keys = bets_keys_list[index]
        for p_index, pos in enumerate(position):
            if p_index in current_bets_keys:
                num_index = current_bets_keys.index(p_index)
                if nums[num_index] not in pos:
                    bets = 0
                    break
            else:
                bets *= len(pos)
        if bets > 0:
            bets_data[bets_keys[len(nums)]] += bets

    return bets_data


def check_guess_memos(amount: uint64, memo: bytes | str) -> Tuple[Optional[str], Dict[str, Any]]:
    if isinstance(memo, str):
        memo = memo.encode("utf-8")
    try:
        memo_json = json.loads(memo)
        if "v" not in memo_json:
            return "Guess info Missing 'v' field", {}
        if "m" not in memo_json:
            return "Guess info Missing 'm' field", {}

        if "t" in memo_json:
            memo_json["t"] = int(memo_json["t"])
        memo_json["m"] = Decimal(str(memo_json["m"]))
        if memo_json["m"] < 0.001 or memo_json["m"] > 100:
            raise ValueError("Guess multiple must be between 0.001 and 100")
        posNums = list(memo_json["v"])
        if len(posNums) != 4:
            raise ValueError("Guess pos len error")
        total_amount = 1
        nums_list = [[], [], [], []]
        for index, nums in enumerate(posNums):
            val = list(set(nums))
            val.sort()
            total_amount *= len(val)
            for v in val:
                n = int(v)
                if n < 1 or n > 16:
                    return f"Guess pos {index+1} numbers error", {}
                nums_list[index].append(n)
        memo_json["v"] = nums_list
        if int(memo_json["m"] * total_amount * MOJO_PER_LOTTERY) != amount:
            return f"Guess amount: {amount/MOJO_PER_LOTTERY} error, must be: {total_amount * memo_json['m']}", {}
        return None, memo_json
    except json.JSONDecodeError:
        return f"Guess info Invalid JSON string: {memo}", {}
