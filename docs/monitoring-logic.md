# Wall-E 监控逻辑说明

## 1. 监控目标

Wall-E 机器人用于监控 Telegram 群组中的疑似广告行为，当前核心策略是：

- 同一用户在短时间内重复发送相同内容；
- 同一用户在短时间内重复发送相同链接；
- 命中后执行删除、警告、禁言、累计违规，达到阈值后踢出。

实现位置：`src/walle_bot/services/moderation.py`、`src/walle_bot/services/state.py`。

## 2. 处理范围与过滤条件

机器人仅在满足以下条件时处理消息：

1. Update 中存在有效 `message`、`user`、`chat`；
2. 聊天类型是 `group` 或 `supergroup`；
3. 如果配置了监控群列表（`MONITORED_CHAT_IDS`），只处理列表内 chat；
4. 发送者不在白名单（`WHITELIST_USER_IDS`）；
5. 发送者不是机器人账号。

说明：当前仅处理文本/带 caption 的消息（`text` 或 `caption`）。

## 3. 广告识别规则

### 3.1 时间窗口

使用 `duplicate_window_seconds` 作为窗口（默认 10 秒）：

- 对每个 `(chat_id, user_id)` 维护近期消息历史；
- 进入新消息时会先清理窗口外历史；
- 只对窗口内历史做重复比对。

### 3.2 重复内容判定

对消息文本做标准化后比较：

- 转小写；
- 压缩连续空白为单空格；
- 去掉首尾空格。

若标准化后与窗口内历史消息一致，判定为 `duplicate_content`。

### 3.3 重复链接判定

从文本中提取 URL（支持 `http(s)://` 和 `www.`），并做标准化：

- 转小写；
- 去除结尾标点（如 `.,!?` 和右括号等）。

若当前消息链接集合与窗口内任一历史消息有交集，判定为 `duplicate_link`。

## 4. 违规处置流程

当命中重复规则后，流程如下：

1. 删除本次消息 + 命中的历史重复消息；
2. 该用户在该群的违规次数 `+1`；
3. 若违规次数 `>= max_violations`（默认 3）：
   - 执行 `ban_chat_member` 踢出；
   - 在群内发送移除通知；
4. 否则：
   - 执行 `restrict_chat_member` 禁言；
   - 禁言时长为 `mute_duration_seconds`（默认 3600 秒，即 1 小时）；
   - 在群内发送警告（包含当前违规次数）。

## 5. 配置项来源

### 5.1 YAML 配置（`config/settings.yaml`）

- `env.file`：env 文件名（默认 `.env`）；
- `env.bot_token_key`：Token 的环境变量名；
- `env.monitored_chat_ids_key`：监控群 ID 环境变量名；
- `env.whitelist_user_ids_key`：白名单用户 ID 环境变量名；
- `moderation.duplicate_window_seconds`：重复检测窗口秒数；
- `moderation.mute_duration_seconds`：禁言秒数；
- `moderation.max_violations`：达到多少次违规后踢出；
- `storage.sqlite_db_path`：SQLite 文件路径（默认 `data/walle.db`）。

### 5.2 Env 配置（示例）

```env
BOT_TOKEN=xxxx
MONITORED_CHAT_IDS=-1001234567890,-1009876543210
WHITELIST_USER_IDS=12345678,87654321
```

说明：

- `MONITORED_CHAT_IDS` 为空时表示“监控所有群”；
- 白名单用户不会进入广告检测；
- 以上敏感信息建议仅保存在本地 env 文件，不提交到仓库。

## 6. 状态存储与重启行为

当前状态为 **SQLite 持久化**：

- 消息历史存储在 `message_events` 表；
- 违规计数存储在 `violations` 表；
- 重启后数据仍保留（除非手动删除数据库文件）；
- 每次新消息处理时会清理该用户窗口外的历史消息记录。

## 7. 当前能力边界

1. 仅按“同一用户短时重复内容/链接”识别，不含 NLP 语义分析；
2. 未覆盖图片 OCR、文件内容、二维码等高级广告识别；
3. 未实现管理员命令（如查询违规记录、手动清零等）；
4. 默认依赖机器人在群内具备删除消息、禁言、踢人权限。

## 8. 关键代码入口

- 初始化与消息路由：`src/walle_bot/bot.py`
- 监控主逻辑：`src/walle_bot/services/moderation.py`
- 重复检测与违规计数：`src/walle_bot/services/state.py`
- 配置加载：`src/walle_bot/config.py`

## 9. 管理群组与整点报时

- 在群组中触发 `/start` 时，只有 owner/admin 可注册当前 `chat_id` 到 `managed_chats` 表；
- 机器人启动时，会向 `managed_chats` 里的所有群发送“Wall-E机器人已重启 + 当前时间”通知；
- 机器人每隔 1 小时遍历 `managed_chats`，向每个群发送当前 UTC 时间；
- 支持 `/list` 命令查看全部命令与权限；
- 关键实现：`src/walle_bot/handlers/commands.py`、`src/walle_bot/services/scheduler.py`。
