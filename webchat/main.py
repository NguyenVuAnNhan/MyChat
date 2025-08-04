from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
from collections import defaultdict

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

class ConnectionManager:
    def __init__(self):
        # Keep track of the pool of connections to this room
        self.rooms: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, room: str, websocket: WebSocket):
        # Await for the connection to be accepted
        await websocket.accept()
        # Add to connection pool
        self.rooms[room].append(websocket)

    def disconnect(self, room:str,  websocket: WebSocket):
        # Remove from connection pool
        self.rooms[room].remove(websocket)
        # Clean up empty room
        if not self.rooms[room]:
            del self.rooms[room]

    async def broadcast(self, room:str, message: str):
        # broadcase the message to all connections in this pool
        for connection in self.rooms.get(room, []):
            await connection.send_text(message)

manager = ConnectionManager()

# Home endpoint
@app.get("/")
async def get():
    return HTMLResponse(open("static/index.html").read())

# Websocket endpoint
@app.websocket("/ws/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str):
    # Connect the client to the pool
    await manager.connect(room_name, websocket)
    # Event loop
    try:
        while True:
            # Receive input
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                username = payload.get("username", "Anonymous")
                message = payload.get("message", "")
                if message:
                    # Broadcast input
                    await manager.broadcast(room_name, f"{username}: {message}")
            except json.JSONDecodeError:
                await manager.broadcast(room_name, "Invalid message format")
    # Handle disconnection
    except WebSocketDisconnect:
        # Disconnect this connection
        manager.disconnect(room_name, websocket)
        # Announce disconnection
        await manager.broadcast(room_name, "A user disconnected")