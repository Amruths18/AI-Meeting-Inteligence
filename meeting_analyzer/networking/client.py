"""
networking/client.py
Participant client — connects to host MeetingServer.
"""

import socket
import threading
from typing import Callable, Optional

from .protocol import send_message, recv_message, MSG


class MeetingClient:
    def __init__(
        self,
        user_name: str,
        user_role: str,
        on_transcript:     Callable[[str], None]  = None,
        on_task_assign:    Callable[[dict], None] = None,
        on_task_broadcast: Callable[[dict], None] = None,
        on_participants:   Callable[[list], None] = None,
        on_meeting_end:    Callable[[str], None]  = None,
        on_welcome:        Callable[[dict], None] = None,
        on_error:          Callable[[str], None]  = None,
    ):
        self.user_name  = user_name
        self.user_role  = user_role

        self.on_transcript     = on_transcript
        self.on_task_assign    = on_task_assign
        self.on_task_broadcast = on_task_broadcast
        self.on_participants   = on_participants
        self.on_meeting_end    = on_meeting_end
        self.on_welcome        = on_welcome
        self.on_error          = on_error

        self._sock:    Optional[socket.socket] = None
        self._running: bool = False

    def connect(self, host_ip: str, port: int, timeout: float = 8.0) -> bool:
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(timeout)
            self._sock.connect((host_ip, int(port)))
            self._sock.settimeout(None)

            ok = send_message(self._sock, MSG.JOIN, {
                "name": self.user_name,
                "role": self.user_role,
            })
            if not ok:
                return False

            self._running = True
            threading.Thread(target=self._listen_loop, daemon=True).start()
            return True

        except (OSError, ConnectionRefusedError, TimeoutError) as e:
            if self.on_error:
                self.on_error(f"Could not connect: {e}")
            return False

    def disconnect(self):
        self._running = False
        if self._sock:
            try:
                send_message(self._sock, MSG.LEAVE, {})
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _listen_loop(self):
        while self._running:
            msg = recv_message(self._sock, timeout=90.0)
            if msg is None:
                if self._running and self.on_error:
                    self.on_error("Connection to host lost.")
                break
            self._dispatch(msg)

    def _dispatch(self, msg: dict):
        mtype = msg.get("type")
        if mtype == MSG.WELCOME and self.on_welcome:
            self.on_welcome(msg)
        elif mtype == MSG.TRANSCRIPT and self.on_transcript:
            self.on_transcript(msg.get("text", ""))
        elif mtype == MSG.TASK_ASSIGN and self.on_task_assign:
            self.on_task_assign(msg.get("task", {}))
        elif mtype == MSG.TASK_BROADCAST and self.on_task_broadcast:
            self.on_task_broadcast(msg)
        elif mtype == MSG.PARTICIPANTS and self.on_participants:
            self.on_participants(msg.get("participants", []))
        elif mtype == MSG.MEETING_END:
            self._running = False
            if self.on_meeting_end:
                self.on_meeting_end(msg.get("message", "Meeting ended."))

    def send_task_update(self, task_id: int, new_status: str):
        if self._sock:
            send_message(self._sock, MSG.TASK_UPDATE, {
                "task_id": task_id,
                "status":  new_status,
            })