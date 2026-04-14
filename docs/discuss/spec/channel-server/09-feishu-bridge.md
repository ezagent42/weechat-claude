# Channel-Server v1.0 — 飞书 Bridge 详细设计

> 参考实现: cc-openclaw `feishu/message_parsers.py` + `sidecar/`
> 上位文档: `03-bridge-layer.md`

---

## 1. 定位

飞书 Bridge 是 channel-server 的**渠道适配器**，负责：
1. 连接飞书 WSS（接收消息事件）
2. 解析全部飞书消息类型为统一格式
3. 通过 Bridge API 转发给 channel-server
4. 接收 channel-server 回复，通过飞书 API 发送（含消息编辑、card）
5. 管理飞书群 ↔ conversation/role 的映射

**飞书 Bridge 不包含业务逻辑**——它只做协议转换。

---

## 2. 架构

```
飞书服务器 (WSS)
     │
     ▼
┌─ feishu_bridge (独立进程) ─────────────────────────────┐
│                                                         │
│  FeishuWSClient                                         │
│  ├── lark_oapi.ws.Client (WSS 长连接)                   │
│  ├── 消息事件 → message_parsers 解析                     │
│  └── 群事件 → group_manager 处理                         │
│                                                         │
│  MessageParsers (可插拔注册表)                            │
│  ├── text, post                                         │
│  ├── image, file, audio, media (下载到本地)              │
│  ├── interactive (card 解析)                             │
│  ├── merge_forward (递归解析)                            │
│  ├── sticker, location, todo, system, share_*           │
│  └── 未知类型 → 描述性 fallback                          │
│                                                         │
│  FeishuSender                                           │
│  ├── send_text(chat_id, text)                           │
│  ├── send_card(chat_id, card_json)                      │
│  ├── update_message(message_id, text)                   │
│  ├── add_reaction(message_id, emoji)                    │
│  ├── remove_reaction(message_id, reaction_id)           │
│  └── download_file(message_id, file_key) → local_path   │
│                                                         │
│  GroupManager                                           │
│  ├── 飞书群 chat_id → role 映射                          │
│  │   customer_chats: [oc_xxx, ...] → customer           │
│  │   squad_chat: oc_yyy → operator                      │
│  │   admin_chat: oc_zzz → admin                         │
│  ├── 新群（bot 被拉入）→ 自动识别角色                    │
│  └── 群成员变动 → 通知 channel-server                    │
│                                                         │
│  BridgeAPIClient (WebSocket → channel-server :9999)     │
│  ├── register(capabilities)                             │
│  ├── customer_connect / customer_message                │
│  ├── operator_join / operator_message / operator_command│
│  ├── admin_command                                      │
│  └── 接收 reply / edit / event / csat_request           │
│                                                         │
│  VisibilityRouter                                       │
│  ├── public → 发到 customer 群                           │
│  ├── side → 发到 squad 群                                │
│  ├── system → 发到 squad 群 + admin 群                   │
│  └── csat_request → 发 card 到 customer 群               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 消息类型解析器（message_parsers.py）

复刻 cc-openclaw 的可插拔注册表模式：

```python
# 注册表
_parsers: dict[str, Callable] = {}

def register_parser(*msg_types: str):
    def decorator(fn):
        for mt in msg_types:
            _parsers[mt] = fn
        return fn
    return decorator

def parse_message(msg_type, content, message, bridge) -> tuple[str, str]:
    """返回 (text, file_path)"""
    parser = _parsers.get(msg_type)
    if parser:
        return parser(content, message, bridge)
    return f"[{msg_type} 消息]", ""
```

### 需支持的消息类型

| 优先级 | 类型 | 解析方式 | 来源 |
|--------|------|---------|------|
| P0 | text | `content.text` | cc-openclaw |
| P0 | post | title + paragraphs | cc-openclaw |
| P0 | image/file/audio/media | 下载到本地 → `[File: path]` | cc-openclaw |
| P0 | interactive (card) | 提取 header + elements 文本 | cc-openclaw |
| P0 | merge_forward | 递归获取子消息 | cc-openclaw |
| P1 | sticker | `[表情包]` | cc-openclaw |
| P1 | share_chat / share_user | `[群名片/用户名片: id]` | cc-openclaw |
| P1 | location | `[位置: name (lat, lng)]` | cc-openclaw |
| P1 | todo | `[任务: summary]` | cc-openclaw |
| P2 | system | `[系统: 成员加入/退出/...]` | cc-openclaw |
| P2 | hongbao / vote / video_chat / calendar / folder | 描述性标签 | cc-openclaw |

---

## 4. 飞书发送能力

| 操作 | API | 用途 |
|------|-----|------|
| 发文本 | `POST /im/v1/messages` msg_type=text | agent 回复 |
| 发卡片 | `POST /im/v1/messages` msg_type=interactive | CSAT 评分邀请、状态卡片、分队通知 |
| 编辑消息 | `PATCH /im/v1/messages/{id}` | 占位→续写替换 |
| 添加 reaction | `POST /im/v1/messages/{id}/reactions` | ACK 确认（OnIt） |
| 移除 reaction | `DELETE /im/v1/messages/{id}/reactions/{rid}` | 回复后移除 ACK |
| 下载文件 | `GET /im/v1/messages/{id}/resources/{key}` | 接收客户文件 |
| 读群消息 | `GET /im/v1/messages` | E2E 测试验证 |
| 查群成员 | `GET /im/v1/chats/{id}/members` | reconciler 同步 |

### Card 消息模板

**CSAT 评分卡片**:
```json
{
  "type": "template",
  "data": {
    "template_id": "csat_rating",
    "template_variable": {
      "conversation_id": "feishu_oc_xxx"
    }
  }
}
```

或直接用 elements:
```json
{
  "header": {"title": {"content": "请为本次服务评分", "tag": "plain_text"}},
  "elements": [
    {"tag": "action", "actions": [
      {"tag": "button", "text": {"content": "⭐", "tag": "plain_text"}, "value": {"score": "1"}},
      {"tag": "button", "text": {"content": "⭐⭐", "tag": "plain_text"}, "value": {"score": "2"}},
      {"tag": "button", "text": {"content": "⭐⭐⭐", "tag": "plain_text"}, "value": {"score": "3"}},
      {"tag": "button", "text": {"content": "⭐⭐⭐⭐", "tag": "plain_text"}, "value": {"score": "4"}},
      {"tag": "button", "text": {"content": "⭐⭐⭐⭐⭐", "tag": "plain_text"}, "value": {"score": "5"}}
    ]}
  ]
}
```

**分队卡片通知**:
```json
{
  "header": {"title": {"content": "[进行中] 客户 David", "tag": "plain_text"}},
  "elements": [
    {"tag": "div", "text": {"content": "询问 B 套餐 · mode: auto", "tag": "plain_text"}},
    {"tag": "action", "actions": [
      {"tag": "button", "text": {"content": "进入对话", "tag": "plain_text"}, "value": {"action": "join", "conv_id": "feishu_oc_xxx"}}
    ]}
  ]
}
```

---

## 5. 群 ↔ 角色映射（GroupManager）

### 配置

```yaml
# feishu-bridge-config.yaml
feishu:
  app_id: ${FEISHU_APP_ID}
  app_secret: ${FEISHU_APP_SECRET}

groups:
  admin_chat_id: "oc_admin_xxx"        # 管理群 → admin 角色
  squad_chats:                          # 分队群 → operator 角色
    - chat_id: "oc_squad_xiaoli"
      operator_id: "xiaoli"
    - chat_id: "oc_squad_xiaowang"
      operator_id: "xiaowang"
  # 其他群 → customer 角色（动态，bot 被拉入时自动识别）

channel_server:
  url: "ws://localhost:9999"

storage:
  upload_dir: ".feishu-bridge/uploads"
```

### 群角色自动识别

```python
class GroupManager:
    def identify_role(self, chat_id: str) -> str:
        """根据 chat_id 判断角色"""
        if chat_id == self.admin_chat_id:
            return "admin"
        for squad in self.squad_chats:
            if chat_id == squad["chat_id"]:
                return "operator"
        return "customer"  # 默认: 未配置的群当作客户群
    
    def get_operator_id(self, chat_id: str) -> str | None:
        for squad in self.squad_chats:
            if chat_id == squad["chat_id"]:
                return squad["operator_id"]
        return None
```

### 群事件处理

| 飞书事件 | 处理 |
|---------|------|
| bot 被拉入新群 | 自动识别为 customer 群 → 注册到 channel-server |
| 群解散 | 清理 conversation 映射 |
| 成员加入管理群 | 注册为 admin |
| 成员加入分队群 | 注册为 operator |

---

## 6. Visibility 路由

Bridge 从 channel-server 收到带 `visibility` 的消息后：

```python
class VisibilityRouter:
    def route(self, conversation_id: str, message: dict):
        visibility = message.get("visibility", "public")
        text = message.get("text", "")
        
        customer_chat = self.group_manager.get_customer_chat(conversation_id)
        squad_chat = self.group_manager.get_squad_chat(conversation_id)
        
        if visibility == "public":
            # 客户群 + 分队群都收到
            self.sender.send_text(customer_chat, text)
            if squad_chat:
                self.sender.send_text(squad_chat, f"[→客户] {text}")
        
        elif visibility == "side":
            # 只发到分队群
            if squad_chat:
                self.sender.send_text(squad_chat, f"[侧栏] {text}")
        
        elif visibility == "system":
            # 分队群 + 管理群
            if squad_chat:
                self.sender.send_text(squad_chat, f"[系统] {text}")
            self.sender.send_text(self.admin_chat_id, f"[系统] {text}")
        
        if message.get("type") == "csat_request":
            self.sender.send_card(customer_chat, self.csat_card(conversation_id))
```

---

## 7. E2E 测试辅助工具（feishu_test_client.py）

```python
class FeishuTestClient:
    """飞书 API 封装，用于 E2E 自动化测试"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.client = lark.Client.builder().app_id(app_id).app_secret(app_secret).build()
    
    def send_message(self, chat_id: str, text: str) -> str:
        """发文本消息，返回 message_id"""
        ...
    
    def send_card(self, chat_id: str, card: dict) -> str:
        """发卡片消息"""
        ...
    
    def list_messages(self, chat_id: str, start_time: str, page_size: int = 50) -> list:
        """拉取群内指定时间后的消息"""
        ...
    
    def get_message(self, message_id: str) -> dict:
        """获取单条消息详情（含 update_time，用于验证消息编辑）"""
        ...
    
    def assert_message_appears(self, chat_id: str, contains: str, timeout: int = 30):
        """轮询直到群内出现包含指定文本的消息"""
        start = time.time()
        while time.time() - start < timeout:
            messages = self.list_messages(chat_id, start_time=...)
            for m in messages:
                if contains in m.get("content", ""):
                    return m
            time.sleep(2)
        raise AssertionError(f"Message containing '{contains}' not found in {chat_id} within {timeout}s")
    
    def assert_message_absent(self, chat_id: str, contains: str, wait: int = 10):
        """等待一段时间，确认群内没有包含指定文本的消息（Gate 验证）"""
        time.sleep(wait)
        messages = self.list_messages(chat_id, start_time=...)
        for m in messages:
            if contains in m.get("content", ""):
                raise AssertionError(f"Message containing '{contains}' should NOT appear in {chat_id}")
    
    def get_chat_members(self, chat_id: str) -> list:
        """获取群成员列表"""
        ...
```

---

## 8. 文件结构

```
feishu_bridge/                    # 可以放在 channel-server submodule 内或独立仓库
├── __init__.py
├── bridge.py                     # FeishuBridge 主类（WSS + Bridge API client）
├── message_parsers.py            # 可插拔消息解析器（从 cc-openclaw 移植）
├── sender.py                     # FeishuSender（发消息/card/编辑/reaction）
├── group_manager.py              # 群角色映射 + 事件处理
├── visibility_router.py          # visibility → 飞书群 路由
├── config.py                     # 配置加载（YAML + env var）
├── test_client.py                # E2E 测试辅助工具
└── tests/
    ├── test_message_parsers.py   # 解析器单元测试
    ├── test_group_manager.py     # 群映射测试
    ├── test_visibility_router.py # visibility 路由测试
    └── test_sender.py            # 发送 mock 测试
```

---

*End of Feishu Bridge Design v1.0*
