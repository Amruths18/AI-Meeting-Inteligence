"""
networking/server.py
Host-side TCP server. Broadcasts transcript and tasks to all participants.
"""

import socket
import threading
from typing import Callable

from .protocol import send_message, recv_message, MSG, get_local_ip


class MeetingServer:
    def __init__(
        self,
        host_name: str,
        meeting_title: str,
        on_participant_change: Callable[[list], None] = None,
        on_task_update: Callable[[dict], None] = None,
    ):
        self.host_name     = host_name
        self.meeting_title = meeting_title
        self.on_participant_change = on_participant_change
        self.on_task_update        = on_task_update

        self._clients: dict[socket.socket, dict] = {}
        self._lock    = threading.Lock()
        self._running = False
        self._transcript: str  = ""
        self._tasks: list[dict] = []

        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind(("0.0.0.0", 0))
        self._server_sock.listen(20)

        self.port = self._server_sock.getsockname()[1]
        self.ip   = get_local_ip()

    def start(self):
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self):
        self._running = False
        self.broadcast(MSG.MEETING_END, {"message": "The host has ended the meeting."})
        try:
            self._server_sock.close()
        except OSError:
            pass

    def _accept_loop(self):
        while self._running:
            try:
                client_sock, addr = self._server_sock.accept()
            except OSError:
                break
            threading.Thread(
                target=self._handle_client,
                args=(client_sock, addr),
                daemon=True
            ).start()

    def _handle_client(self, sock: socket.socket, addr):
        msg = recv_message(sock, timeout=10.0)
        if not msg or msg.get("type") != MSG.JOIN:
            sock.close()
            return

        info = {"name": msg.get("name", "Unknown"), "role": msg.get("role", "employee")}
        with self._lock:
            self._clients[sock] = info

        send_message(sock, MSG.WELCOME, {
            "meeting_title": self.meeting_title,
            "transcript":    self._transcript,
            "tasks":         self._tasks,
        })
        self._broadcast_participants()

        while self._running:
            msg = recv_message(sock, timeout=60.0)
            if msg is None:
                break
            self._dispatch_from_client(sock, msg)

        with self._lock:
            self._clients.pop(sock, None)
        try:
            sock.close()
        except OSError:
            pass
        self._broadcast_participants()

    def _dispatch_from_client(self, sock: socket.socket, msg: dict):
        if msg.get("type") == MSG.TASK_UPDATE:
            self.broadcast(MSG.TASK_BROADCAST, {
                "task_id":    msg.get("task_id"),
                "status":     msg.get("status"),
                "updated_by": self._clients.get(sock, {}).get("name", "?"),
            })
            if self.on_task_update:
                self.on_task_update(msg)

    def broadcast(self, msg_type: str, data: dict = None):
        with self._lock:
            dead = []
            for sock in list(self._clients):
                ok = send_message(sock, msg_type, data or {})
                if not ok:
                    dead.append(sock)
            for sock in dead:
                self._clients.pop(sock, None)

    def broadcast_transcript(self, text: str):
        self._transcript += text + "\n"
        self.broadcast(MSG.TRANSCRIPT, {"text": text})

    def broadcast_task(self, task: dict):
        self._tasks.append(task)
        self.broadcast(MSG.TASK_ASSIGN, {"task": task})

    def _broadcast_participants(self):
        with self._lock:
            participants = [
                {"name": v["name"], "role": v["role"]}
                for v in self._clients.values()
            ]
        self.broadcast(MSG.PARTICIPANTS, {"participants": participants})
        if self.on_participant_change:
            self.on_participant_change(participants)

    @property
    def participant_count(self) -> int:
        with self._lock:
            return len(self._clients)

    @property
    def connection_string(self) -> str:
        return f"{self.ip}:{self.port}"