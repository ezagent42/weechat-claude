#!/usr/bin/env python3
# weechat-zenoh.py

"""
WeeChat Zenoh P2P 聊天插件
提供 Zenoh 消息总线上的 room/DM 基础设施
"""

import weechat
import json
import time
import uuid
import os
from collections import deque

SCRIPT_NAME = "weechat-zenoh"
SCRIPT_AUTHOR = "Allen <ezagent42>"
SCRIPT_VERSION = "0.1.0"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "P2P chat over Zenoh for WeeChat"

# --- 全局状态 ---
zenoh_session = None
msg_queue = deque()
presence_queue = deque()
subscribers = {}          # key → zenoh.Subscriber
publishers = {}           # key → zenoh.Publisher
liveliness_tokens = {}    # key → zenoh.LivelinessToken
buffers = {}              # buffer_key → weechat buffer ptr
my_nick = ""
rooms = set()             # 已加入的 room
dms = set()               # 已开启的 DM


# ============================================================
# 初始化 / 反初始化
# ============================================================

def zc_init():
    global zenoh_session, my_nick
    import zenoh

    my_nick = weechat.config_get_plugin("nick")
    if not my_nick:
        my_nick = os.environ.get("USER", "user_%s" % uuid.uuid4().hex[:6])
        weechat.config_set_plugin("nick", my_nick)

    # Zenoh peer mode, multicast scouting
    config = zenoh.Config()
    config.insert_json5("mode", '"peer"')

    connect = weechat.config_get_plugin("connect")
    if connect:
        config.insert_json5("connect/endpoints",
                            json.dumps(connect.split(",")))

    try:
        zenoh_session = zenoh.open(config)
    except Exception as e:
        weechat.prnt("", f"[zenoh] Failed to open session: {e}")
        return

    # 全局在线状态
    liveliness_tokens["_global"] = \
        zenoh_session.liveliness().declare_token(f"wc/presence/{my_nick}")

    # 队列轮询
    weechat.hook_timer(50, 0, 0, "poll_queues_cb", "")

    # 自动加入
    autojoin = weechat.config_get_plugin("autojoin")
    if autojoin:
        for target in autojoin.split(","):
            target = target.strip()
            if target:
                join(target)

    weechat.prnt("", f"[zenoh] Session opened, nick={my_nick}")


def zc_deinit():
    for token in liveliness_tokens.values():
        token.undeclare()
    for sub in subscribers.values():
        sub.undeclare()
    for pub in publishers.values():
        pub.undeclare()
    if zenoh_session:
        zenoh_session.close()
    return weechat.WEECHAT_RC_OK


# ============================================================
# Room / DM 管理
# ============================================================

def join(target):
    """加入 #room 或开启 @nick DM"""
    if target.startswith("#"):
        join_room(target.lstrip("#"))
    elif target.startswith("@"):
        join_dm(target.lstrip("@"))
    else:
        join_room(target)


def join_room(room_id):
    import zenoh

    if room_id in rooms:
        weechat.prnt("", f"[zenoh] Already in #{room_id}")
        return

    # Buffer
    buf = weechat.buffer_new(
        f"zenoh.#{room_id}", "buffer_input_cb", "",
        "buffer_close_cb", "")
    weechat.buffer_set(buf, "title", f"Zenoh: #{room_id}")
    weechat.buffer_set(buf, "short_name", f"#{room_id}")
    weechat.buffer_set(buf, "nicklist", "1")
    weechat.buffer_set(buf, "localvar_set_type", "room")
    weechat.buffer_set(buf, "localvar_set_target", room_id)
    weechat.nicklist_add_nick(buf, "", my_nick, "default", "", "", 1)
    buffers[f"room:{room_id}"] = buf

    # Zenoh pub/sub
    msg_key = f"wc/rooms/{room_id}/messages"
    publishers[f"room:{room_id}"] = zenoh_session.declare_publisher(msg_key)
    subscribers[f"room:{room_id}"] = zenoh_session.declare_subscriber(
        msg_key,
        lambda sample, _rid=room_id: _on_room_msg(sample, _rid),
        background=True
    )

    # Liveliness
    token_key = f"wc/rooms/{room_id}/presence/{my_nick}"
    liveliness_tokens[f"room:{room_id}"] = \
        zenoh_session.liveliness().declare_token(token_key)

    # 监听该 room 的 presence 变化
    zenoh_session.liveliness().declare_subscriber(
        f"wc/rooms/{room_id}/presence/*",
        lambda sample, _rid=room_id: _on_room_presence(sample, _rid),
        background=True
    )

    # 查询当前在线的成员
    try:
        replies = zenoh_session.liveliness().get(
            f"wc/rooms/{room_id}/presence/*")
        for reply in replies:
            nick = str(reply.ok.key_expr).rsplit("/", 1)[-1]
            _add_nick(room_id, nick)
    except Exception:
        pass

    rooms.add(room_id)

    # 广播 join
    _publish_event(f"room:{room_id}", "join", "")
    weechat.prnt(buf, f"-->\t{my_nick} joined #{room_id}")


def join_dm(target_nick):
    # DM key: 两个 nick 字母序排列
    pair = "_".join(sorted([my_nick, target_nick]))
    dm_key = f"dm:{pair}"

    if pair in dms:
        return

    buf = weechat.buffer_new(
        f"zenoh.@{target_nick}", "buffer_input_cb", "",
        "buffer_close_cb", "")
    weechat.buffer_set(buf, "title", f"DM with {target_nick}")
    weechat.buffer_set(buf, "short_name", f"@{target_nick}")
    weechat.buffer_set(buf, "nicklist", "1")
    weechat.buffer_set(buf, "localvar_set_type", "dm")
    weechat.buffer_set(buf, "localvar_set_target", target_nick)
    weechat.buffer_set(buf, "localvar_set_dm_pair", pair)
    weechat.nicklist_add_nick(buf, "", target_nick, "cyan", "", "", 1)
    weechat.nicklist_add_nick(buf, "", my_nick, "default", "", "", 1)
    buffers[dm_key] = buf

    msg_key = f"wc/dm/{pair}/messages"
    publishers[dm_key] = zenoh_session.declare_publisher(msg_key)
    subscribers[dm_key] = zenoh_session.declare_subscriber(
        msg_key,
        lambda sample, _dk=dm_key: _on_dm_msg(sample, _dk),
        background=True
    )

    dms.add(pair)


def leave(target):
    """离开 room 或关闭 DM"""
    if target.startswith("#"):
        leave_room(target.lstrip("#"))
    elif target.startswith("@"):
        leave_dm(target.lstrip("@"))


def leave_room(room_id):
    key = f"room:{room_id}"
    if room_id not in rooms:
        return
    _publish_event(key, "leave", "")
    _cleanup_key(key)
    rooms.discard(room_id)


def leave_dm(target_nick):
    pair = "_".join(sorted([my_nick, target_nick]))
    key = f"dm:{pair}"
    _cleanup_key(key)
    dms.discard(pair)


def _cleanup_key(key):
    if key in subscribers:
        subscribers.pop(key).undeclare()
    if key in publishers:
        publishers.pop(key).undeclare()
    if key in liveliness_tokens:
        liveliness_tokens.pop(key).undeclare()
    if key in buffers:
        weechat.buffer_close(buffers.pop(key))


# ============================================================
# 消息发送
# ============================================================

def _publish_event(pub_key, msg_type, body):
    pub = publishers.get(pub_key)
    if not pub:
        return
    event = json.dumps({
        "id": uuid.uuid4().hex,
        "nick": my_nick,
        "type": msg_type,
        "body": body,
        "ts": time.time()
    })
    pub.put(event)


def send_message(target, body):
    """公共 API: 发送消息到指定 target"""
    if target.startswith("#"):
        room_id = target.lstrip("#")
        key = f"room:{room_id}"
        _publish_event(key, "msg", body)
        buf = buffers.get(key)
        if buf:
            weechat.prnt(buf, f"{my_nick}\t{body}")
    elif target.startswith("@"):
        nick = target.lstrip("@")
        pair = "_".join(sorted([my_nick, nick]))
        key = f"dm:{pair}"
        if pair not in dms:
            join_dm(nick)
        _publish_event(key, "msg", body)
        buf = buffers.get(key)
        if buf:
            weechat.prnt(buf, f"{my_nick}\t{body}")


def buffer_input_cb(data, buffer, input_data):
    buf_type = weechat.buffer_get_string(buffer, "localvar_type")
    target = weechat.buffer_get_string(buffer, "localvar_target")

    if buf_type == "room":
        _publish_event(f"room:{target}", "msg", input_data)
        weechat.prnt(buffer, f"{my_nick}\t{input_data}")
        weechat.hook_signal_send("zenoh_message_sent",
            weechat.WEECHAT_HOOK_SIGNAL_STRING,
            json.dumps({"room": f"#{target}", "nick": my_nick,
                        "body": input_data}))
    elif buf_type == "dm":
        pair = weechat.buffer_get_string(buffer, "localvar_dm_pair")
        _publish_event(f"dm:{pair}", "msg", input_data)
        weechat.prnt(buffer, f"{my_nick}\t{input_data}")

    return weechat.WEECHAT_RC_OK


def buffer_close_cb(data, buffer):
    buf_type = weechat.buffer_get_string(buffer, "localvar_type")
    target = weechat.buffer_get_string(buffer, "localvar_target")
    if buf_type == "room":
        leave_room(target)
    elif buf_type == "dm":
        leave_dm(target)
    return weechat.WEECHAT_RC_OK


# ============================================================
# 消息接收 (Zenoh callback → deque → hook_timer)
# ============================================================

def _on_room_msg(sample, room_id):
    try:
        msg = json.loads(sample.payload.to_string())
        if msg.get("nick") != my_nick:
            msg["_target"] = f"room:{room_id}"
            msg_queue.append(msg)
    except Exception:
        pass


def _on_dm_msg(sample, dm_key):
    try:
        msg = json.loads(sample.payload.to_string())
        if msg.get("nick") != my_nick:
            msg["_target"] = dm_key
            msg_queue.append(msg)
    except Exception:
        pass


def _on_room_presence(sample, room_id):
    nick = str(sample.key_expr).rsplit("/", 1)[-1]
    kind = str(sample.kind)
    presence_queue.append({
        "room_id": room_id,
        "nick": nick,
        "online": "PUT" in kind
    })


def poll_queues_cb(data, remaining_calls):
    # 消息
    for _ in range(200):
        try:
            msg = msg_queue.popleft()
        except IndexError:
            break
        target = msg.get("_target", "")
        buf = buffers.get(target)
        if not buf:
            continue
        nick = msg.get("nick", "???")
        body = msg.get("body", "")
        msg_type = msg.get("type", "msg")

        if msg_type == "msg":
            weechat.prnt(buf, f"{nick}\t{body}")
        elif msg_type == "action":
            weechat.prnt(buf, f" *\t{nick} {body}")
        elif msg_type == "join":
            weechat.prnt(buf, f"-->\t{nick} joined")
            room_id = target.replace("room:", "")
            _add_nick(room_id, nick)
        elif msg_type == "leave":
            weechat.prnt(buf, f"<--\t{nick} left")
            room_id = target.replace("room:", "")
            _remove_nick(room_id, nick)

        # Signal 供其他脚本消费
        weechat.hook_signal_send("zenoh_message_received",
            weechat.WEECHAT_HOOK_SIGNAL_STRING,
            json.dumps({"target": target, "nick": nick,
                        "body": body, "type": msg_type}))

    # Presence
    for _ in range(100):
        try:
            ev = presence_queue.popleft()
        except IndexError:
            break
        room_id = ev["room_id"]
        nick = ev["nick"]
        if ev["online"]:
            _add_nick(room_id, nick)
        else:
            _remove_nick(room_id, nick)
            buf = buffers.get(f"room:{room_id}")
            if buf:
                weechat.prnt(buf, f"<--\t{nick} went offline")
        weechat.hook_signal_send("zenoh_presence_changed",
            weechat.WEECHAT_HOOK_SIGNAL_STRING,
            json.dumps(ev))

    return weechat.WEECHAT_RC_OK


# ============================================================
# Nicklist helpers
# ============================================================

def _add_nick(room_id, nick):
    buf = buffers.get(f"room:{room_id}")
    if buf and not weechat.nicklist_search_nick(buf, "", nick):
        weechat.nicklist_add_nick(buf, "", nick, "cyan", "", "", 1)

def _remove_nick(room_id, nick):
    buf = buffers.get(f"room:{room_id}")
    if buf:
        ptr = weechat.nicklist_search_nick(buf, "", nick)
        if ptr:
            weechat.nicklist_remove_nick(buf, ptr)


# ============================================================
# /zenoh 命令
# ============================================================

def zenoh_cmd_cb(data, buffer, args):
    argv = args.split()
    cmd = argv[0] if argv else "help"

    if cmd == "join" and len(argv) >= 2:
        join(argv[1])

    elif cmd == "leave":
        if len(argv) >= 2:
            leave(argv[1])
        else:
            target = weechat.buffer_get_string(buffer, "localvar_target")
            buf_type = weechat.buffer_get_string(buffer, "localvar_type")
            if target:
                leave(f"{'#' if buf_type == 'room' else '@'}{target}")

    elif cmd == "nick" and len(argv) >= 2:
        global my_nick
        old = my_nick
        my_nick = argv[1]
        weechat.config_set_plugin("nick", my_nick)
        weechat.prnt("", f"[zenoh] Nick changed: {old} → {my_nick}")

    elif cmd == "list":
        weechat.prnt(buffer, "[zenoh] Rooms:")
        for r in sorted(rooms):
            weechat.prnt(buffer, f"  #{r}")
        weechat.prnt(buffer, "[zenoh] DMs:")
        for d in sorted(dms):
            weechat.prnt(buffer, f"  {d}")

    elif cmd == "send" and len(argv) >= 3:
        target = argv[1]
        body = " ".join(argv[2:])
        send_message(target, body)

    elif cmd == "status":
        weechat.prnt(buffer,
            f"[zenoh] nick={my_nick} rooms={len(rooms)} "
            f"dms={len(dms)} session={'open' if zenoh_session else 'closed'}")

    else:
        weechat.prnt(buffer,
            "[zenoh] Usage: /zenoh <join|leave|nick|list|send|status>")

    return weechat.WEECHAT_RC_OK


# ============================================================
# 插件注册
# ============================================================

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                    SCRIPT_LICENSE, SCRIPT_DESC, "zc_deinit", ""):
    for key, val in {
        "nick": "",
        "autojoin": "#general",
        "connect": "",
    }.items():
        if not weechat.config_is_set_plugin(key):
            weechat.config_set_plugin(key, val)

    weechat.hook_command("zenoh",
        "Zenoh P2P chat",
        "join <#room|@nick> || leave [target] || nick <n> || "
        "list || send <target> <msg> || status",
        "  join: Join room or open DM\n"
        " leave: Leave room or close DM\n"
        "  nick: Change nickname\n"
        "  list: List joined rooms and DMs\n"
        "  send: Send message programmatically\n"
        "status: Show connection status",
        "join || leave || nick || list || send || status",
        "zenoh_cmd_cb", "")

    zc_init()
