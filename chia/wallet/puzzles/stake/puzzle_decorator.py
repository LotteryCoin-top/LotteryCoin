from __future__ import annotations

from typing import Any, Dict, List, Tuple

from chia.types.blockchain_format.program import Program
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.types.condition_opcodes import ConditionOpcode
from chia.types.stake_record import get_stake_value
from chia.util.ints import uint16
from chia.util.streamable import VersionedBlob
from chia.wallet.payment import Payment
from chia.wallet.puzzles.stake.drivers import create_stake_merkle_puzzle
from chia.wallet.puzzles.stake.metadata import StakeMetadata, StakeVersion
from chia.wallet.util.wallet_types import RemarkDataType


class StakePuzzleDecorator:
    """
    This class is a wrapper for clawback puzzles. It allows us to add Stake characteristics to the inner puzzle.
    """

    stake_type: uint16
    recipient_ph: bytes32

    @staticmethod
    def create(config: Dict[str, Any]) -> StakePuzzleDecorator:
        self = StakePuzzleDecorator()
        self.stake_type = config.get("stake_type", 0)
        self.recipient_ph = bytes32(config.get("recipient_ph"))
        return self

    def decorate(self, inner_puzzle: Program) -> Program:
        # We don't wrap anything for the Stake
        return inner_puzzle

    def decorate_target_puzzle_hash(
        self,
        inner_puzzle: Program,
        target_puzzle_hash: bytes32,
    ) -> Tuple[Program, bytes32]:
        return (
            self.decorate(inner_puzzle),
            create_stake_merkle_puzzle(get_stake_value(self.stake_type).time_lock, self.recipient_ph).get_tree_hash(),
        )

    def solve(
        self, inner_puzzle: Program, primaries: List[Payment], inner_solution: Program
    ) -> Tuple[Program, Program]:
        # Append REMARK condition [1, "CLAWBACK", TIME_LOCK, SENDER_PUZHSAH, RECIPIENT_PUZHSAH]
        if len(primaries) == 1:
            metadata = StakeMetadata(self.stake_type, self.recipient_ph)
            remark_condition = Program.to(
                [
                    ConditionOpcode.REMARK.value,
                    RemarkDataType.STAKE,
                    bytes(VersionedBlob(StakeVersion.V1.value, bytes(metadata))),
                ]
            )
            # Insert the REMARK condition into the condition list
            conditions = remark_condition.cons(inner_solution.rest().first().rest())
            conditions = inner_solution.rest().first().first().cons(conditions)
            inner_solution = inner_solution.replace(rf=conditions)
        return self.decorate(inner_puzzle), inner_solution

    def decorate_memos(
        self, inner_puzzle: Program, target_puzzle_hash: bytes32, memos: List[bytes]
    ) -> Tuple[Program, List[bytes]]:
        memos.insert(0, target_puzzle_hash)
        return self.decorate(inner_puzzle), memos
