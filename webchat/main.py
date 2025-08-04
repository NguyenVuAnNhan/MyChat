from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

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
            await connection.send_test(message)

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
            # Broadcast input
            await manager.broadcase(f"msg: {data}")
    # Handle disconnection
    except WebSocketDisconnect:
        # Disconnect this connection
        manager.disconnect(websocket)
        # Announce disconnection
        await manager.broadcast("A user disconnected")