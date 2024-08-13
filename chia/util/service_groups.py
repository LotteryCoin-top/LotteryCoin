from __future__ import annotations

from typing import Dict, Generator, Iterable, KeysView

SERVICES_FOR_GROUP: Dict[str, list[str]] = {
    "all": [
        "lottery_harvester",
        "lottery_timelord_launcher",
        "lottery_timelord",
        "lottery_farmer",
        "lottery_full_node",
        "lottery_wallet",
        "lottery_data_layer",
        "lottery_data_layer_http",
    ],
    "daemon": [],
    # TODO: should this be `data_layer`?
    "data": ["lottery_wallet", "lottery_data_layer"],
    "data_layer_http": ["lottery_data_layer_http"],
    "node": ["lottery_full_node"],
    "harvester": ["lottery_harvester"],
    "farmer": ["lottery_harvester", "lottery_farmer", "lottery_full_node", "lottery_wallet"],
    "farmer-no-wallet": ["lottery_harvester", "lottery_farmer", "lottery_full_node"],
    "farmer-only": ["lottery_farmer"],
    "timelord": ["lottery_timelord_launcher", "lottery_timelord", "lottery_full_node"],
    "timelord-only": ["lottery_timelord"],
    "timelord-launcher-only": ["lottery_timelord_launcher"],
    "wallet": ["lottery_wallet"],
    "introducer": ["lottery_introducer"],
    "simulator": ["lottery_full_node_simulator"],
    "crawler": ["lottery_crawler"],
    "seeder": ["lottery_crawler", "lottery_seeder"],
    "seeder-only": ["lottery_seeder"],
}


def all_groups() -> KeysView[str]:
    return SERVICES_FOR_GROUP.keys()


def services_for_groups(groups: Iterable[str]) -> Generator[str, None, None]:
    for group in groups:
        yield from SERVICES_FOR_GROUP[group]


def validate_service(service: str) -> bool:
    return any(service in _ for _ in SERVICES_FOR_GROUP.values())
