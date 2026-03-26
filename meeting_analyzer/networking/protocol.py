"""
networking/protocol.py
Low-level socket message protocol.

Frame format:
    [4 bytes big-endian length][JSON payload bytes]
"""

import json
import struct
import socket
from typing import Optional


class MSG:
    JOIN           = "JOIN"
    WELCOME        = "WELCOME"
    LEAVE          = "LEAVE"
    PARTICIPANTS   = "PARTICIPANTS"
    TRANSCRIPT     = "TRANSCRIPT"
    TASK_ASSIGN    = "TASK_ASSIGN"
    TASK_UPDATE    = "TASK_UPDATE"
    TASK_BROADCAST = "TASK_BROADCAST"
    MEETING_END    = "MEETING_END"
    PING           = "PING"


def send_message(sock: socket.socket, msg_type: str, data: dict = None) -> bool:
    payload_dict = {"type": msg_type}
    if data:
        payload_dict.update(data)
    try:
        payload = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
        header  = struct.pack(">I", len(payload))
        sock.sendall(header + payload)
        return True
    except (OSError, BrokenPipeError):
        return False


def recv_message(sock: socket.socket, timeout: float = None) -> Optional[dict]:
    if timeout is not None:
        sock.settimeout(timeout)
    try:
        header = _recv_exact(sock, 4)
        if header is None:
            return None
        length = struct.unpack(">I", header)[0]
        if length == 0 or length > 10_000_000:
            return None
        payload = _recv_exact(sock, length)
        if payload is None:
            return None
        return json.loads(payload.decode("utf-8"))
    except (OSError, json.JSONDecodeError, struct.error):
        return None
    finally:
        if timeout is not None:
            sock.settimeout(None)


def _recv_exact(sock: socket.socket, n: int) -> Optional[bytes]:
    data = b""
    while len(data) < n:
        try:
            chunk = sock.recv(n - len(data))
        except OSError:
            return None
        if not chunk:
            return None
        data += chunk
    return data


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()