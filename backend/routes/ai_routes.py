from fastapi import APIRouter, UploadFile, File
from services.ai_service import clean_diagram
from models.diagram_models import CleanedDiagram

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/clean")
async def clean_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    return await clean_diagram(image_bytes) 
