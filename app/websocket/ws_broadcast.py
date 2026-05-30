# backend/ws_broadcast.py
import json
from typing import List
from fastapi import WebSocket

class WSManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        try:
            self.active.remove(ws)
        except ValueError:
            pass

    async def broadcast(self, message):
        """
        message: python dict or list -> will be JSON-dumped
        """
        if isinstance(message, (dict, list)):
            payload = json.dumps(message)
        else:
            payload = str(message)

        to_remove = []
        for ws in list(self.active):
            try:
                await ws.send_text(payload)
            except Exception:
                to_remove.append(ws)

        for r in to_remove:
            self.disconnect(r)

# single manager instance imported by main and mqtt handler
manager = WSManager()
