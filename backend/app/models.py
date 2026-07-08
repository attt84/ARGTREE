from pydantic import BaseModel, Field
from typing import List, Optional

class SearchRequest(BaseModel):
    query: str = Field(..., description="The search keyword, e.g., '少子化対策'")

class ArgumentNode(BaseModel):
    id: str
    label: str
    type: str # 'theme', 'pro', 'con', 'neutral', 'solution'
    source: Optional[str] = None # Speaker name or meeting info

class ArgumentEdge(BaseModel):
    id: str
    source: str
    target: str

class ArgumentTree(BaseModel):
    nodes: List[ArgumentNode]
    edges: List[ArgumentEdge]

class ArgumentResponse(BaseModel):
    query: str
    tree: ArgumentTree
