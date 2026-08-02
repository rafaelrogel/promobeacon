#!/usr/bin/env bash
# raw_hci_adv.sh - Legacy BLE advertising via raw HCI commands.
# Why: on this Qualcomm USB controller (13d3:3491), bless D-Bus advertising fails
# with "Invalid Parameters (0x0d)" and btmgmt add-adv reports success but never
# activates (ActiveInstances: 0x00). Raw HCI works.
#
# Usage: sudo ./raw_hci_adv.sh [on|off]
set -euo pipefail

# PromoBeacon service UUID: 12345678-1234-1234-1234-123456789ABC
# adv data: flags (02 01 06) + complete 128-bit UUID (11 07 <LE bytes>)
ADV_HEX="02 01 06 11 07 bc 9a 78 56 34 12 34 12 34 12 34 12 78 56 34 12"
# scan rsp: complete local name "PromoBeacon"
RSP_HEX="0c 09 50 72 6f 6d 6f 42 65 61 63 6f 6e"

hex_to_args() { echo "$1" | tr ' ' '\n' | grep -v '^$'; }

adv_len() { hex_to_args "$1" | wc -l; }

case "${1:-on}" in
  on)
    # disable advertising first (status may be stale)
    hcitool cmd 0x08 0x000a 00 >/dev/null 2>&1 || true
    # LE Set Advertising Parameters: interval 0x0800=1.28s, connectable undirected,
    # all channels, no filter
    hcitool cmd 0x08 0x0006 00 08 00 08 00 00 00 00 00 00 00 00 07 00
    hcitool cmd 0x08 0x0008 "$(adv_len "$ADV_HEX")" $ADV_HEX
    hcitool cmd 0x08 0x0009 "$(adv_len "$RSP_HEX")" $RSP_HEX
    hcitool cmd 0x08 0x000a 01
    echo "Advertising ON (raw HCI, $(adv_len "$ADV_HEX") bytes adv, $(adv_len "$RSP_HEX") bytes scan rsp)"
    ;;
  off)
    hcitool cmd 0x08 0x000a 00
    echo "Advertising OFF"
    ;;
  *)
    echo "Usage: $0 [on|off]" >&2
    exit 1
    ;;
esac
