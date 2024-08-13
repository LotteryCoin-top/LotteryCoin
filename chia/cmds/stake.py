from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Optional

import click

from chia.cmds import options


@click.group("stake", short_help="Manage your stake")
@click.pass_context
def stake_cmd(ctx: click.Context) -> None:
    pass


@stake_cmd.command("info", short_help="Query stake info")
@click.option(
    "-wp",
    "--wallet-rpc-port",
    help="Set the port where the Wallet is hosting the RPC interface. See the rpc_port under wallet in config.yaml",
    type=int,
    default=None,
)
@options.create_fingerprint()
@click.option("-i", "--id", help="Id of the wallet to use", type=int, default=1, show_default=True, required=True)
def stake_info_cmd(wallet_rpc_port: Optional[int], fingerprint: int, id: int) -> None:
    from .stake_funcs import stake_info

    asyncio.run(stake_info(wallet_rpc_port=wallet_rpc_port, fp=fingerprint, wallet_id=id))


@stake_cmd.command("send", short_help="Send lot to stake")
@click.option(
    "-wp",
    "--wallet-rpc-port",
    help="Set the port where the Wallet is hosting the RPC interface. See the rpc_port under wallet in config.yaml",
    type=int,
    default=None,
)
@options.create_fingerprint()
@click.option("-i", "--id", help="Id of the wallet to use", type=int, default=1, show_default=True, required=True)
@click.option("-a", "--amount", help="How much lot to stake, in LOT, must be a positive integer", type=int, required=True)
@click.option(
    "-m",
    "--fee",
    help="Set the fees for the stake transaction, in LOT",
    type=str,
    default="0",
    show_default=True,
    required=True,
)
@click.option("-t", "--address", help="stake address", type=str, default="", required=True)
@click.option("-s", "--stake-type", help="Set the stake type", type=int, default=None)
def stake_send_cmd(
    wallet_rpc_port: Optional[int],
    fingerprint: int,
    id: int,
    amount: int,
    fee: str,
    address: str,
    stake_type: Optional[int],
) -> None:
    from .stake_funcs import stake_send

    asyncio.run(
        stake_send(
            wallet_rpc_port=wallet_rpc_port,
            fp=fingerprint,
            wallet_id=id,
            amount=amount,
            fee=Decimal(fee),
            address=address,
            stake_type=stake_type,
        )
    )


@stake_cmd.command(
    "withdraw",
    help="withdraw stake transaction."
    " The wallet will automatically detect if you are able to revert or claim.",
)
@click.option(
    "-wp",
    "--wallet-rpc-port",
    help="Set the port where the Wallet is hosting the RPC interface. See the rpc_port under wallet in config.yaml",
    type=int,
    default=None,
)
@options.create_fingerprint()
# TODO: Remove unused wallet id option
@click.option("-i", "--id", help="Id of the wallet to use", type=int, default=1, show_default=True, required=True)
@click.option(
    "-ids",
    "--tx_ids",
    help="IDs of the stake transactions you want to withdraw. Separate multiple IDs by comma (,).",
    type=str,
    default="",
    required=True,
)
@click.option(
    "-m", "--fee", help="A fee to add to the offer when it gets taken, in LOT", default="0.1", show_default=True
)
@click.option(
    "--force",
    help="Force to push the spend bundle even it may be a double spend",
    is_flag=True,
    default=False,
)
def withdraw(
    wallet_rpc_port: Optional[int],
    fingerprint: int,
    id: int,
    tx_ids: str,
    fee: str,
    force: bool
) -> None:  # pragma: no cover
    from .stake_funcs import stake_withdraw

    asyncio.run(
        stake_withdraw(
            wallet_rpc_port=wallet_rpc_port,
            fp=fingerprint,
            fee=Decimal(fee),
            tx_ids_str=tx_ids,
            force=force,
        )
    )
