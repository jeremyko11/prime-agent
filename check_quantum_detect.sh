#!/usr/bin/env bash
bash /mnt/d/A/PPT/prime_upgrade/deploy.sh 2>&1 | grep -cE '^OK'
~/.prime/agent/kernel-venv/bin/python -c "
from deep_research._impl import _THREAT_RE, _threat_extra_backends
for t in ('量子计算对加密体系的冲击', '可控核聚变 商业化', '后量子密码迁移 NIST'):
    print(t, '-> threat =', bool(_THREAT_RE.search(t)))
print('backends:', _threat_extra_backends())
"
