#!/usr/bin/env bash
# VideoPub launchd 安装脚本
# 用法: bash deploy/install.sh [watch_folder]
set -euo pipefail

PLIST_LABEL="com.videopub.watch"
PLIST_DST="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ── 检测 Python 虚拟环境 ──────────────────────────────────────────────────────
if [[ -f "$PROJECT_DIR/.venv/bin/videopub" ]]; then
    VIDEOPUB_BIN="$PROJECT_DIR/.venv/bin/videopub"
    VENV_BIN="$PROJECT_DIR/.venv/bin"
elif command -v videopub &>/dev/null; then
    VIDEOPUB_BIN="$(command -v videopub)"
    VENV_BIN="$(dirname "$VIDEOPUB_BIN")"
else
    echo "❌ 找不到 videopub 可执行文件，请先安装: pip install -e ." >&2
    exit 1
fi

# ── 读取 watch_folder ─────────────────────────────────────────────────────────
if [[ $# -ge 1 ]]; then
    WATCH_FOLDER="$(realpath "$1")"
else
    # 从 settings.yaml 读取（若存在）
    SETTINGS="$PROJECT_DIR/videopub/config/settings.yaml"
    if [[ -f "$SETTINGS" ]] && command -v python3 &>/dev/null; then
        WATCH_FOLDER="$(python3 -c "
import yaml, pathlib
with open('$SETTINGS') as f:
    cfg = yaml.safe_load(f)
print(pathlib.Path(cfg.get('watch_folder','~/videopub/watch_folder')).expanduser())
" 2>/dev/null || echo "$HOME/videopub/watch_folder")"
    else
        WATCH_FOLDER="$HOME/videopub/watch_folder"
    fi
fi

LOG_DIR="$HOME/videopub/logs"
mkdir -p "$WATCH_FOLDER" "$LOG_DIR"

echo "📌 videopub bin : $VIDEOPUB_BIN"
echo "📂 监控目录     : $WATCH_FOLDER"
echo "📋 日志目录     : $LOG_DIR"

# ── 生成 plist ────────────────────────────────────────────────────────────────
sed \
    -e "s|__VIDEOPUB_BIN__|$VIDEOPUB_BIN|g" \
    -e "s|__WATCH_FOLDER__|$WATCH_FOLDER|g" \
    -e "s|__LOG_DIR__|$LOG_DIR|g" \
    -e "s|__VENV_BIN__|$VENV_BIN|g" \
    -e "s|__HOME__|$HOME|g" \
    "$SCRIPT_DIR/com.videopub.watch.plist" > "$PLIST_DST"

# ── 加载服务 ──────────────────────────────────────────────────────────────────
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load -w "$PLIST_DST"

echo "✅ VideoPub 已安装为 launchd 服务 ($PLIST_LABEL)"
echo "   停止:    launchctl unload $PLIST_DST"
echo "   状态:    launchctl list | grep videopub"
echo "   日志:    tail -f $LOG_DIR/launchd_stderr.log"
