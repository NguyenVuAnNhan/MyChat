from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

class ConnectionManager:
    def __init__(self):
        # Keep track of the pool of connections to this room
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        # Await for the connection to be accepted
        await websocket.accept()
        # Add to connection pool
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        # Remove from connection pool
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        # broadcase the message to all connections in this pool
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Home endpoint
@app.get("/")
async def get():
    return HTMLResponse(open("static/index.html").read())

# Websocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Connect the client to the pool
    await manager.connect(websocket)
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
                    await manager.broadcast(f"{username}: {message}")
            except json.JSONDecodeError:
                await manager.broadcast("Invalid message format")
    # Handle disconnection
    except WebSocketDisconnect:
        # Disconnect this connection
        manager.disconnect(websocket)
        # Announce disconnection
        await manager.broadcast("A user disconnected")