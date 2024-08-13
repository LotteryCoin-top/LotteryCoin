from __future__ import annotations

import dataclasses
import logging
from typing import List, Optional, Tuple

import typing_extensions

from chia.types.blockchain_format.sized_bytes import bytes32, bytes48
from chia.types.stake_record import StakeRecord
from chia.util.db_wrapper import SQLITE_MAX_VARIABLE_NUMBER, DBWrapper2
from chia.util.ints import uint32, uint64, uint128
from chia.util.lru_cache import LRUCache
from chia.util.batches import to_batches

log = logging.getLogger(__name__)


@typing_extensions.final
@dataclasses.dataclass
class StakeStore:
    """
    This object handles CoinRecords in DB.
    """

    db_wrapper: DBWrapper2
    stake_farm_cache: LRUCache[bytes48, List[StakeRecord]]
    stake_lock_cache: LRUCache[bytes32, List[StakeRecord]]

    @classmethod
    async def create(cls, db_wrapper: DBWrapper2) -> StakeStore:
        self = cls(db_wrapper, LRUCache(104), LRUCache(104))
        async with self.db_wrapper.writer_maybe_transaction() as conn:
            log.info("DB: Creating coin store tables and indexes.")
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS stake_record("
                "coin_name blob PRIMARY KEY,"
                " puzzle_hash blob,"
                " amount int,"
                " confirmed_index bigint,"
                " spent_index bigint,"  # if this is zero, it means the coin has not been spent
                " stake_type tinyint,"
                " coefficient float,"
                " expiration bigint)"
            )

            # Useful for reorg lookups
            log.info("DB: Creating index stake confirmed_index")
            await conn.execute("CREATE INDEX IF NOT EXISTS stake_confirmed_index on stake_record(confirmed_index)")

            log.info("DB: Creating index stake spent_index")
            await conn.execute("CREATE INDEX IF NOT EXISTS stake_spent_index on stake_record(spent_index)")

            log.info("DB: Creating index stake stake_type")
            await conn.execute("CREATE INDEX IF NOT EXISTS stake_stake_type on stake_record(stake_type)")

            log.info("DB: Creating index stake puzzle_hash")
            await conn.execute("CREATE INDEX IF NOT EXISTS puzzle_hash on stake_record(puzzle_hash)")

            log.info("DB: Creating index stake expiration")
            await conn.execute("CREATE INDEX IF NOT EXISTS stake_expiration on stake_record(expiration)")

        return self

    # Store StakeRecord in DB
    async def _add_records(self, records: List[StakeRecord]) -> None:
        values2 = []
        for record in records:
            values2.append(
                (
                    record.name,
                    record.puzzle_hash,
                    int(record.amount),
                    record.confirmed_index,
                    record.spent_index,
                    record.stake_type,
                    float(record.coefficient),
                    record.expiration,
                )
            )
        if len(values2) > 0:
            async with self.db_wrapper.writer_maybe_transaction() as conn:
                await conn.executemany(
                    "INSERT INTO stake_record VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                    values2,
                )

    # Update stake_record to be spent in DB
    async def _set_spent(self, coin_names: List[bytes32], index: uint32) -> None:
        assert len(coin_names) == 0 or index > 0

        if len(coin_names) == 0:
            return None

        async with self.db_wrapper.writer_maybe_transaction() as conn:
            for batch in to_batches(coin_names, SQLITE_MAX_VARIABLE_NUMBER):
                name_params = ",".join(["?"] * len(batch.entries))
                await conn.execute(
                    f"UPDATE stake_record INDEXED BY sqlite_autoindex_stake_record_1 "
                    f"SET spent_index={index} "
                    f"WHERE spent_index=0 "
                    f"AND coin_name IN ({name_params})",
                    batch.entries,
                )

    async def new_stake(
            self,
            height: uint32,
            tx_additions: List[StakeRecord],
            tx_removals: List[bytes32],
    ) -> None:
        if len(tx_additions) > 0:
            await self._add_records(tx_additions)
        await self._set_spent(tx_removals, height)

    async def rollback_to_block(self, block_index: int):
        """
        Note that block_index can be negative, in which case everything is rolled back
        Returns the list of coin records that have been modified
        """
        # Add coins that are confirmed in the reverted blocks to the list of updated coins.
        async with self.db_wrapper.writer_maybe_transaction() as conn:
            # Delete reverted blocks from storage
            await conn.execute("DELETE FROM stake_record WHERE confirmed_index>?", (block_index,))
            await conn.execute("UPDATE stake_record SET spent_index=0 WHERE spent_index>?", (block_index,))

        self.stake_farm_cache = LRUCache(self.stake_farm_cache.capacity)
        self.stake_lock_cache = LRUCache(self.stake_lock_cache.capacity)

    async def get_stake_amount_total(self, timestamp: uint64) -> Tuple[int, float]:
        async with self.db_wrapper.reader_no_transaction() as conn:
            async with conn.execute(
                "SELECT SUM(amount),SUM(amount*coefficient) FROM stake_record WHERE expiration>?",
                (timestamp,),
            ) as cursor:
                stake_lock, stake_lock_calc = 0, 0.0,
                rows = await cursor.fetchall()
                if len(rows) > 0 and rows[0] is not None and rows[0][0] is not None:
                    for row in rows:
                        stake_lock = int(row[0])
                        stake_lock_calc = float(row[1])
        return stake_lock, stake_lock_calc

    async def get_stake_lock_records(
            self, start: uint64, end: uint64
    ) -> List[StakeRecord]:
        stake_key = bytes32(start.to_bytes(16, "big") + end.to_bytes(16, "big"))
        stake_list: Optional[List[StakeRecord]] = self.stake_lock_cache.get(stake_key)
        if stake_list is not None:
            return stake_list

        async with self.db_wrapper.reader_no_transaction() as conn:
            async with conn.execute(
                "SELECT coin_name,puzzle_hash,amount,confirmed_index,spent_index,stake_type,coefficient,expiration"
                " FROM stake_record INDEXED BY stake_expiration WHERE expiration>? "
                "AND expiration%86400>=? AND expiration%86400<?",
                (end, start % 86400 + 300, end % 86400 + 300,),
            ) as cursor:
                records: List[StakeRecord] = []
                rows = await cursor.fetchall()
                if len(rows) > 0 and rows[0] is not None and rows[0][0] is not None:
                    for row in rows:
                        records.append(StakeRecord(
                            bytes32(row[0]),
                            bytes32(row[1]),
                            uint64(int(row[2])),
                            int(row[3]),
                            int(row[4]),
                            int(row[5]),
                            float(row[4]),
                            uint64(int(row[5])),
                        ))
                self.stake_lock_cache.put(stake_key, records)
                return records

    async def get_stake_lock_amount_total(self, timestamp: uint64) -> float:
        async with self.db_wrapper.reader_no_transaction() as conn:
            async with conn.execute(
                "SELECT SUM(amount*coefficient) FROM stake_record WHERE expiration>?",
                (timestamp,),
            ) as cursor:
                row = await cursor.fetchone()
                if row is not None and row[0] is not None:
                    return float(row[0])
            return 0.0

    async def get_stake_records(
            self, confirmed_index: uint32
    ) -> List[StakeRecord]:
        async with self.db_wrapper.reader_no_transaction() as conn:
            async with conn.execute(
                "SELECT coin_name,puzzle_hash,amount,confirmed_index,spent_index,stake_type,coefficient,expiration"
                " FROM stake_record INDEXED BY stake_confirmed_index WHERE confirmed_index=?",
                (confirmed_index,),
            ) as cursor:
                records: List[StakeRecord] = []
                rows = await cursor.fetchall()
                if len(rows) > 0 and rows[0] is not None and rows[0][0] is not None:
                    for row in rows:
                        records.append(StakeRecord(
                            bytes32(row[0]),
                            bytes32(row[1]),
                            uint64(int(row[2])),
                            int(row[3]),
                            int(row[4]),
                            int(row[5]),
                            float(row[6]),
                            int(row[7]),
                        ))
                return records
