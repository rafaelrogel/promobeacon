#!/usr/bin/env python3
"""
Test and validate the high-capacity 2.7MB storage partition table layout for PromoBeacon.
"""
import subprocess
import os

NEW_PARTITIONS = """# Name,   Type, SubType, Offset,  Size, Flags
nvs,      data, nvs,     0x9000,  0x10000,
phy_init, data, phy,     0x1f000, 0x1000,
factory,  app,  factory, 0x20000, 0x140000,
storage,  data, spiffs,  0x160000,0x2A0000,
"""

def test_partition_generation():
    test_csv = "firmware/partitions_bigstorage.csv"
    test_bin = "firmware/partitions_bigstorage.bin"
    with open(test_csv, "w", encoding="utf-8") as f:
        f.write(NEW_PARTITIONS)

    tool = r"C:\Users\rafae\.platformio\packages\framework-espidf\components\partition_table\gen_esp32part.py"
    cmd = ["python", tool, "--verify", "--offset", "0x8000", test_csv, test_bin]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("Exit code:", result.returncode)

    if result.returncode == 0:
        bin_size = os.path.getsize(test_bin)
        print(f"SUCCESS: Generated {test_bin} ({bin_size} bytes)")
        
        # Parse back binary to verify
        verify_cmd = ["python", tool, test_bin]
        v_res = subprocess.run(verify_cmd, capture_output=True, text=True)
        print("Verified Table Output:\n", v_res.stdout)
    else:
        print("FAILED to generate partition binary")

if __name__ == "__main__":
    test_partition_generation()
