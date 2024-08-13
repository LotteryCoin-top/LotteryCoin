from __future__ import annotations

import logging
from typing import Any, List, Optional, Set, Union, Tuple

from chia.consensus.default_constants import DEFAULT_CONSTANTS
from chia.types.blockchain_format.coin import Coin
from chia.types.blockchain_format.program import Program
from chia.types.blockchain_format.serialized_program import SerializedProgram
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.types.coin_spend import CoinSpend, make_spend
from chia.types.condition_opcodes import ConditionOpcode
from chia.util.condition_tools import conditions_for_solution
from chia.util.ints import uint64
from chia.util.streamable import VersionedBlob
from chia.wallet.puzzles.clawback.drivers import (
    create_augmented_cond_puzzle_hash,
    P2_1_OF_N,
    create_merkle_proof,create_augmented_cond_puzzle,
    create_augmented_cond_solution,
)
from chia.wallet.puzzles.stake.metadata import StakeMetadata
from chia.wallet.puzzles.p2_delegated_puzzle_or_hidden_puzzle import MOD
from chia.wallet.uncurried_puzzle import UncurriedPuzzle, uncurry_puzzle
from chia.wallet.util.merkle_tree import MerkleTree
from chia.wallet.util.wallet_types import RemarkDataType

log = logging.getLogger(__name__)


def create_stake_merkle_tree(timelock: uint64, sender_ph: bytes32) -> MerkleTree:
    """
    Returns a merkle tree object
    For clawbacks there are only 2 puzzles in the merkle tree, claim puzzle and clawback puzzle
    """
    if timelock < 1:
        raise ValueError("Timelock must be at least 1 second")
    timelock_condition = [ConditionOpcode.ASSERT_SECONDS_RELATIVE, timelock]
    augmented_cond_puz_hash = create_augmented_cond_puzzle_hash(timelock_condition, sender_ph)
    merkle_tree = MerkleTree([augmented_cond_puz_hash])
    return merkle_tree


def create_stake_merkle_puzzle(timelock: uint64, recipient_ph: bytes32) -> Program:
    merkle_tree = create_stake_merkle_tree(timelock, recipient_ph)
    puzzle: Program = P2_1_OF_N.curry(merkle_tree.calculate_root())
    return puzzle


def create_stake_merkle_solution(
    timelock: uint64,
    recipient_ph: bytes32,
    inner_puzzle: Program,
    inner_solution: Program,
) -> Program:
    """
    Recreates the full merkle tree of a p2_1_of_n clawback coin. It uses the timelock and each party's
    puzhash to create the tree.
    The provided inner puzzle must hash to match either the sender or recipient puzhash
    If it's the sender, then create the clawback solution. If it's the recipient then create the claim
    solution.
    Returns a program which is the solution to a p2_1_of_n clawback.
    """
    merkle_tree = create_stake_merkle_tree(timelock, recipient_ph)
    inner_puzzle_hash = inner_puzzle.get_tree_hash()
    if inner_puzzle_hash == recipient_ph:
        condition = [80, timelock]
        cb_inner_puz = create_augmented_cond_puzzle(condition, inner_puzzle)
        merkle_proof = create_merkle_proof(merkle_tree, cb_inner_puz.get_tree_hash())
        cb_inner_solution = create_augmented_cond_solution(inner_solution)
    else:
        raise ValueError("Invalid Stake inner puzzle.")
    solution: Program = Program.to([merkle_proof, cb_inner_puz, cb_inner_solution])
    return solution


def get_stake_puzzle_metadata_and_new_puzhash(
    uncurried: UncurriedPuzzle, inner_puzzle: Program, inner_solution: Program
) -> Tuple[Optional[StakeMetadata], Set[bytes32]]:
    # Check if the inner puzzle is a P2 puzzle
    new_puzhash: Set[bytes32] = set()
    if MOD != uncurried.mod:
        return None, new_puzhash
    # Fetch Remark condition
    conditions = conditions_for_solution(inner_puzzle, inner_solution, DEFAULT_CONSTANTS.MAX_BLOCK_COST_CLVM // 8)
    metadata: Optional[StakeMetadata] = None
    if conditions is not None:
        for condition in conditions:
            if (
                condition.opcode == ConditionOpcode.REMARK
                and len(condition.vars) == 2
                and int.from_bytes(condition.vars[0], "big") == RemarkDataType.STAKE
            ):
                try:
                    metadata = StakeMetadata.from_bytes(VersionedBlob.from_bytes(condition.vars[1]).blob)
                except Exception:
                    # Invalid Stake metadata
                    log.error(f"Invalid Stake metadata {condition.vars[1].hex()}")
                    return None, new_puzhash
            if condition.opcode == ConditionOpcode.CREATE_COIN:
                new_puzhash.add(bytes32.from_bytes(condition.vars[0]))
    # Check if the inner puzzle matches the coin puzzle hash
    return metadata, new_puzhash


def match_stake_puzzle(
    uncurried: UncurriedPuzzle,
    inner_puzzle: Union[Program, SerializedProgram],
    inner_solution: Union[Program, SerializedProgram],
) -> Optional[StakeMetadata]:

    metadata, new_puzhash = get_stake_puzzle_metadata_and_new_puzhash(uncurried, inner_puzzle, inner_solution)
    # Check if the inner puzzle is a P2 puzzle
    if metadata is None:
        return None
    puzzle: Program = create_stake_merkle_puzzle(
        metadata.time_lock, metadata.recipient_puzzle_hash
    )

    if puzzle.get_tree_hash() not in new_puzhash:
        # The metadata doesn't match the inner puzzle, ignore it
        log.error(
            f"Stake metadata {metadata} doesn't match inner puzzle {inner_puzzle.get_tree_hash().hex()}"
        )  # pragma: no cover
        return None  # pragma: no cover
    return metadata


def match_stake_puzzle_by_coin_spend(
    coin_spend: CoinSpend
) -> Tuple[Optional[StakeMetadata], Optional[bytes32]]:
    puzzle = Program.from_bytes(bytes(coin_spend.puzzle_reveal))
    metadata, new_puzhash = get_stake_puzzle_metadata_and_new_puzhash(
        uncurry_puzzle(puzzle), puzzle, coin_spend.solution.to_program()
    )
    # Check if the inner puzzle is a P2 puzzle
    if metadata is None:
        return metadata, None
    puzzle_ph: bytes32 = create_stake_merkle_puzzle(metadata.time_lock, metadata.recipient_puzzle_hash).get_tree_hash()
    if puzzle_ph not in new_puzhash:
        # The metadata doesn't match the inner puzzle, ignore it
        log.error(
            f"Stake height metadata {metadata} doesn't match inner puzzle {puzzle_ph.hex()}"
        )  # pragma: no cover
        return None, None   # pragma: no cover
    return metadata, puzzle_ph


def generate_stake_spend_bundle(
    coin: Coin, metadata: StakeMetadata, inner_puzzle: Program, inner_solution: Program
) -> CoinSpend:
    time_lock: uint64 = metadata.time_lock
    puzzle: Program = create_stake_merkle_puzzle(time_lock, metadata.recipient_puzzle_hash)
    if puzzle.get_tree_hash() != coin.puzzle_hash:
        raise ValueError(
            f"Cannot spend merkle coin {coin.name()}, "
            f"recreate puzzle hash {puzzle.get_tree_hash().hex()}, actual puzzle hash {coin.puzzle_hash.hex()}"
        )

    solution: Program = create_stake_merkle_solution(
        time_lock, metadata.recipient_puzzle_hash, inner_puzzle, inner_solution
    )
    return make_spend(coin, puzzle, solution)
