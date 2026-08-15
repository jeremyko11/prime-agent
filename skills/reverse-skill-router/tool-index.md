# Tool Index

- Generated at: 2026-08-12 02:02:19 +0800
- Platform: linux (Linux 5.15.167.4-microsoft-standard-WSL2)
- Script: `skills/scripts/refresh-tool-index.sh`
- Note: This script detects tools only. It does not install tools.

| Tool | Skill | Purpose | Available | Path | Version | Source | Install hint |
|---|---|---|---|---|---|---|---|
| java | core-runtime | Java runtime for jadx/apktool/Burp/Ghidra | no | — | — | — | apt: sudo apt install openjdk-17-jdk |
| python3 | core-runtime | Python runtime for helper scripts and pipx tools | yes | /usr/bin/python3 | Python 3.12.3 | command | apt: sudo apt install python3 python3-venv python3-pip pipx |
| pipx | core-runtime | Isolated Python CLI installer | no | — | — | — | see PLATFORMS.md and docs/platforms/linux.md |
| node | core-runtime | Node.js runtime for MCP bridges | yes | /usr/local/bin/node | v22.20.0 | command | apt/nvm: sudo apt install nodejs npm; prefer NodeSource or nvm for newer Node |
| npm | core-runtime | Node package manager | yes | /usr/local/bin/npm | 10.9.3 | command | see PLATFORMS.md and docs/platforms/linux.md |
| npx | core-runtime | Run npm MCP packages | yes | /usr/local/bin/npx | 10.9.3 | command | see PLATFORMS.md and docs/platforms/linux.md |
| jadx | apk-reverse | APK Java/Kotlin decompiler | no | — | — | — | GitHub release: download jadx ZIP to ~/tools/jadx |
| apktool | apk-reverse | APK decode and rebuild | no | — | — | — | apt or jar: sudo apt install apktool; or official apktool.jar |
| adb | apk-reverse | Android device bridge | no | — | — | — | apt or Android platform-tools: sudo apt install adb |
| frida | reverse-engineering | Dynamic instrumentation CLI | no | — | — | — | pipx: pipx install frida-tools |
| frida-ps | reverse-engineering | Frida process listing | no | — | — | — | see PLATFORMS.md and docs/platforms/linux.md |
| r2 | radare2 | radare2 CLI analysis | no | — | — | — | GitHub/source preferred; apt if available |
| rabin2 | radare2 | Binary metadata extraction | no | — | — | — | see PLATFORMS.md and docs/platforms/linux.md |
| ghidra | reverse-engineering | Ghidra reverse-engineering suite | no | — | — | — | GitHub release ZIP or Flatpak; Java required |
| idapro | ida-reverse | IDA Pro commercial reverse-engineering suite | no | — | — | — | see PLATFORMS.md and docs/platforms/linux.md |
| burpsuite | burp-mcp | BurpSuite desktop application | no | — | — | — | manual installer/jar; then load burp-mcp-full jar |
| graphviz | diagram-generator | Graphviz diagram rendering | no | — | — | — | see PLATFORMS.md and docs/platforms/linux.md |
| plantuml | diagram-generator | PlantUML diagram rendering | no | — | — | — | see PLATFORMS.md and docs/platforms/linux.md |
| nmap | pentest-tools | Network scanner | no | — | — | — | see PLATFORMS.md and docs/platforms/linux.md |
| sqlmap | pentest-tools | SQL injection testing tool | no | — | — | — | see PLATFORMS.md and docs/platforms/linux.md |
| ffuf | pentest-tools | Web fuzzer | no | — | — | — | see PLATFORMS.md and docs/platforms/linux.md |
| hashcat | pentest-tools | Password recovery | no | — | — | — | see PLATFORMS.md and docs/platforms/linux.md |
| nuclei | pentest-tools | Template-based vulnerability scanner | no | — | — | — | GitHub release or go install; apt may be unavailable |
| binwalk | firmware-pentest | Firmware extraction and analysis | no | — | — | — | apt: sudo apt install binwalk |
| seclists | pentest-tools | Security wordlists | no | — | — | — | git clone https://github.com/danielmiessler/SecLists ~/tools/SecLists |
| jshookmcp | js-reverse | JS/CDP/Hook MCP runtime via npx | yes | /usr/local/bin/npx | 10.9.3 | command | npx: npx -y @jshookmcp/jshook@0.3.4 |
| reqable-mcp | pentest-tools | Reqable desktop MCP runtime via npx | yes | /usr/local/bin/npx | 10.9.3 | command | npx: npx -y reqable-mcp-server@1.0.1; install Reqable desktop separately |
| jeb-pro | apk-reverse | Commercial Android/ARM decompiler (manual licensed install) | no | — | — | — | manual licensed install: https://www.pnfsoftware.com/jeb/ |
| anything-analyzer | browser-automation | Browser/HTTP analyzer MCP project | no | — | — | — | git clone + pnpm install + pnpm dev |
| burp-mcp-full | burp-mcp | Local Burp MCP extension and stdio bridge | no | — | — | — | see PLATFORMS.md and docs/platforms/linux.md |
| binwalk | firmware-pentest | Firmware extraction and analysis | no | — | — | — | apt: sudo apt install binwalk |
| yara | malware-analysis | Malware rule matching engine | no | — | — | — | apt: sudo apt install yara |
| pwntools | reverse-engineering | CTF pwn exploit development framework | no | — | — | — | pipx: pipx install pwntools |

---

## Next steps

- Read `docs/platforms/linux.md` for ordinary Linux setup.
- If the host is Kali, read `kali/README-kali.md` instead.
- Register MCP servers in your Agent client; tool availability does not imply MCP registration.

---

## 能力状态视图 (Capability Status)

| 能力 | 工具可用 | Ready | MCP 已注册 | 服务在线 | MCP HTTP | 可自动安装 | 安装方式 |
|------|---------|-------|-----------|---------|----------|-----------|---------|
| jadx | ✗ | ✗ | — | — | — | ✓ | github-release-zip |
| apktool | ✗ | ✗ | — | — | — | ✓ | github-release-jar-wrapper |
| jeb-pro | ✗ | ✗ | — | — | — | ✗ | manual |
| frida | ✗ | ✗ | — | — | — | ✓ | pip-package |
| frida-ps | ✗ | ✗ | — | — | — | ✓ | pip-package |
| idalib-mcp | ✗ | ✗ | — | — | — | ✓ | pip-package |
| reqable-mcp | ✓ | ✗ | — | — | — | ✓ | npm-mcp |
| jshookmcp | ✓ | ✗ | — | — | — | ✓ | npm-mcp |
| anything-analyzer | ✗ | ✗ | — | — | — | ✓ | local-http-mcp |
| idapro | ✗ | ✗ | — | — | — | ✓ | local-http-mcp |
| r2 | ✗ | ✗ | — | — | — | ✓ | github-release-zip |
| rabin2 | ✗ | ✗ | — | — | — | ✓ | github-release-zip |
| adb | ✗ | ✗ | — | — | — | ✓ | winget-package |
| agent-browser | ✗ | ✗ | — | — | — | ✓ | npm-global |
| ghidra-mcp | ✗ | ✗ | — | — | — | ✓ | github-release-zip |
| seclists | ✗ | ✗ | — | — | — | ✓ | git-clone |
| proxycat | ✗ | ✗ | — | — | — | ✓ | git-clone |
| burpsuite-mcp | ✗ | ✗ | — | — | — | ✗ | local-http-mcp |
| nmap | ✗ | ✗ | — | — | — | ✓ | winget-package |
| pentestswarm | ✗ | ✗ | — | — | — | ✓ | go-install |
| binwalk | ✗ | ✗ | — | — | — | ✓ | winget-package |
| yara | ✗ | ✗ | — | — | — | ✓ | winget-package |
| pwntools | ✗ | ✗ | — | — | — | ✓ | pip-package |
| bkcrack | ✗ | ✗ | — | — | — | ✓ | github-release-zip |

> ✓ = 是 | ✗ = 否 | — = 不适用或未检测

