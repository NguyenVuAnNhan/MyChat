from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
from collections import defaultdict
from models.message import Message
from db.session import engine, Base, get_db, SessionLocal
from sqlalchemy.orm import Session


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

class ConnectionManager:
    def __init__(self):
        # Keep track of the pool of connections to this room
        self.rooms: dict[str, list[WebSocket]] = defaultdict(list)
        self.usernames: dict[WebSocket, str] = {}

    async def connect(self, room: str, websocket: WebSocket, username: str):
        # Add to connection pool
        self.rooms[room].append(websocket)
        self.usernames[websocket] = username

    def disconnect(self, room:str,  websocket: WebSocket):
        # Remove from connection pool
        if websocket in self.rooms[room]:
            self.rooms[room].remove(websocket)
        if websocket in self.usernames:
            del self.usernames[websocket]
        # Clean up empty room
        if not self.rooms[room]:
            del self.rooms[room]

    async def broadcast(self, room: str, username: str, message: str, db: Session):
        # broadcase the message to all connections in this pool
        db_msg = Message(room=room, username=username, message=message)
        db.add(db_msg)
        db.commit()

        for connection in self.rooms.get(room, []):
            await connection.send_text(message)

Base.metadata.create_all(bind=engine)

manager = ConnectionManager()

# Home endpoint
@app.get("/")
async def get():
    return HTMLResponse(open("static/index.html").read())

@app.get("/api/{room_name}/history")
async def get_history(room_name: str, db: Session = Depends(get_db)):
    messages = (
        db.query(Message)
        .filter(Message.room == room_name)
        .order_by(Message.timestamp.asc())
        .limit(50)
        .all()
    )
    return [
        {"username": m.username, "message": m.message, "timestamp": m.timestamp.isoformat()}
        for m in messages
    ]

@app.get("/rooms")
async def list_active_rooms():
    return HTMLResponse(open("static/rooms.html").read())

@app.get("/rooms_data")
async def retrieve_rooms():
    return {
        "rooms": [
            {"name": room, "users": len(users)}
            for room, users in manager.rooms.items()
        ]
    }

# Websocket endpoint
@app.websocket("/ws/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str):
    # Connect the client to the pool
    await websocket.accept()
    username = None
    # Event loop
    try:
        join_data = await websocket.receive_text()
        payload = json.loads(join_data)
        if payload.get("type") != "join":
            await websocket.close(code=4000)
            return
        
        username = payload.get("username", "Anonymous")
        await manager.connect(room_name, websocket, username)
        with SessionLocal() as db:
            await manager.broadcast(room_name, username, f"{username} joined the room.", db)
            db.close()

        while True:
            # Receive input
            data = await websocket.receive_text()
            payload = json.loads(data)
            if payload.get("type") == "chat":
                message = payload.get("message", "")
                if message:
                    with SessionLocal() as db:
                        await manager.broadcast(room_name, username, f"{username}: {message}", db)
                        db.close()

    # Handle disconnection
    except WebSocketDisconnect:
        # Disconnect this connection
        manager.disconnect(room_name, websocket)
        # Announce disconnection
        await manager.broadcast(room_name, "A user disconnected")