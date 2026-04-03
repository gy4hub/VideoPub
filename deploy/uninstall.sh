#!/usr/bin/env bash
# VideoPub launchd 卸载脚本
set -euo pipefail

PLIST_LABEL="com.videopub.watch"
PLIST_DST="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"

if [[ ! -f "$PLIST_DST" ]]; then
    echo "⚠️  未找到 plist 文件：$PLIST_DST（可能未安装）"
    exit 0
fi

launchctl unload -w "$PLIST_DST" 2>/dev/null || true
rm -f "$PLIST_DST"

echo "✅ VideoPub launchd 服务已卸载"
