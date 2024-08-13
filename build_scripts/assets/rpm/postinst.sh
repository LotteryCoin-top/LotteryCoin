#!/usr/bin/env bash
# Post install script for the UI .rpm to place symlinks in places to allow the CLI to work similarly in both versions

set -e

ln -s /opt/lottery/resources/app.asar.unpacked/daemon/lottery /usr/bin/lottery || true
ln -s /opt/lottery/LotteryCoin /usr/bin/LotteryCoin || true