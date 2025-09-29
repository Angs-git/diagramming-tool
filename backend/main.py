from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from typing import List
from services.ai_service import clean_diagram  # Absolute import
from fastapi.staticfiles import StaticFiles
from routes.ai_routes import router as ai_router

app = FastAPI()

app.include_router(ai_router)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Keep track of all connected clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.get("/")
async def get_root():
    return {"message": "WebSocket Server is Running 🚀"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/analyze-diagram")
async def analyze_diagram(file: UploadFile = File(...)):
    # Verify file is a PNG
    if file.content_type != "image/png":
        return {"error": "File must be a PNG"}
    # Read file bytes
    image_bytes = await file.read()
    # Call clean_diagram
    result = await clean_diagram(image_bytes)
    return result
