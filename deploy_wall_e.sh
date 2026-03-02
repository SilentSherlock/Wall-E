#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

log() {
  echo "[deploy] $1"
}

log "开始发布 Wall-E 进程"

if ! command -v git >/dev/null 2>&1; then
  echo "git 未安装，退出。"
  exit 1
fi

if ! command -v nohup >/dev/null 2>&1; then
  echo "nohup 不可用，退出。"
  exit 1
fi

if [[ ! -d ".git" ]]; then
  echo "当前目录不是 git 仓库：$ROOT_DIR"
  exit 1
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ -z "$CURRENT_BRANCH" || "$CURRENT_BRANCH" == "HEAD" ]]; then
  echo "无法识别当前分支，退出。"
  exit 1
fi

log "更新代码：git pull ($CURRENT_BRANCH)"
git fetch --all --prune
git pull --ff-only origin "$CURRENT_BRANCH"

log "检查并停止旧的 Wall-E 进程"
PIDS="$(pgrep -f "wall_e.py" || true)"
if [[ -n "$PIDS" ]]; then
  echo "$PIDS" | xargs -r kill -15
  sleep 2
  REMAINING="$(pgrep -f "wall_e.py" || true)"
  if [[ -n "$REMAINING" ]]; then
    log "仍有残留进程，强制 kill"
    echo "$REMAINING" | xargs -r kill -9
  fi
else
  log "未发现运行中的 Wall-E 进程"
fi

if [[ ! -f "env_earth/bin/activate" ]]; then
  echo "虚拟环境不存在或 activate 文件缺失：env_earth/bin/activate"
  exit 1
fi

log "激活虚拟环境：source env_earth/bin/activate"
source env_earth/bin/activate

log "启动新进程（nohup，输出重定向到 /dev/null）"
nohup python wall_e.py >/dev/null 2>&1 &

NEW_PID="$!"
sleep 1
if ps -p "$NEW_PID" >/dev/null 2>&1; then
  log "启动成功，PID=$NEW_PID"
else
  echo "进程启动失败，请手动检查。"
  exit 1
fi

log "发布完成"