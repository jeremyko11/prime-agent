#!/usr/bin/env bash
cd /root/work
timeout 300 ~/.prime/agent/kernel-venv/bin/python quantum_supp.py 2>&1
