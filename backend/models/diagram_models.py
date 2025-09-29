from pydantic import BaseModel, Field
from typing import List, Optional, Tuple

class Shape(BaseModel):
    type: str
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    start: Optional[Tuple[int, int]] = None
    end: Optional[Tuple[int, int]] = None

class CleanedDiagram(BaseModel):
    shapes: List[Shape]
