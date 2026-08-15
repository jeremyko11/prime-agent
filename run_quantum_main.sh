#!/usr/bin/env bash
cp /mnt/d/A/PPT/prime_upgrade/quantum_main.py /mnt/d/A/PPT/prime_upgrade/quantum_supp.py /root/work/
cd /root/work
timeout 890 ~/.prime/agent/kernel-venv/bin/python quantum_main.py 2>&1
