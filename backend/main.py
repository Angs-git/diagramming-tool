from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, Depends
from typing import List
from services.ai_service import clean_diagram  # Absolute import
from fastapi.staticfiles import StaticFiles
from routes.ai_routes import router as ai_router
from database import engine, Base, get_db
from services.auth_service import get_current_user
from models.models import User, Diagram
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Create database tables
Base.metadata.create_all(bind=engine)

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

# Schema for diagram data
class DiagramCreate(BaseModel):
    name: str
    diagram_data: str

@app.get("/")
async def get_root():
    return {"message": "WebSocket Server is Running 🚀"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, current_user: User = Depends(get_current_user)):
    if not current_user:
        await websocket.close(code=1008, reason="Authentication required")
        return
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/analyze-diagram")
async def analyze_diagram(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify file is a PNG
    if file.content_type != "image/png":
        return {"error": "File must be a PNG"}
    # Read file bytes
    image_bytes = await file.read()
    # Call clean_diagram
    result = await clean_diagram(image_bytes)
    
    # Save the cleaned diagram to the database
    diagram = Diagram(
        user_id=current_user.id,
        name=file.filename.replace(".png", "_cleaned"),
        diagram_data=result.get("cleaned_data", "{}")  # Assuming clean_diagram returns a dict with cleaned_data
    )
    db.add(diagram)
    db.commit()
    db.refresh(diagram)
    
    return {"message": "Diagram analyzed and saved", "diagram_id": diagram.id, "data": result}

# Example protected endpoint to save a diagram manually
@app.post("/save-diagram")
async def save_diagram(
    diagram: DiagramCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_diagram = Diagram(user_id=current_user.id, name=diagram.name, diagram_data=diagram.diagram_data)
    db.add(db_diagram)
    db.commit()
    db.refresh(db_diagram)
    return {"message": "Diagram saved", "diagram_id": db_diagram.id}
