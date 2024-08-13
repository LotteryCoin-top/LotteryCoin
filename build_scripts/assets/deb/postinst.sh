#!/usr/bin/env bash
# Post install script for the UI .deb to place symlinks in places to allow the CLI to work similarly in both versions

set -e

chown -f root:root /opt/lottery/chrome-sandbox || true
chmod -f 4755 /opt/lottery/chrome-sandbox || true
ln -s /opt/lottery/resources/app.asar.unpacked/daemon/lottery /usr/bin/lottery || true
ln -s /opt/lottery/LotteryCoin /usr/bin/LotteryCoin || true
