from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class FolderBase(BaseModel):
    name: str
    parent_id: Optional[str] = None

class Folder(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    parent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    type: str = "folder"

class FileBase(BaseModel):
    name: str
    folder_id: str
    size: int
    mime_type: str

class FileItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    folder_id: str
    size: int
    mime_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    type: str = "file"

class FolderTree(BaseModel):
    id: str
    name: str
    parent_id: Optional[str] = None
    children: List['FolderTree'] = []
    type: str = "folder"

class FolderChild(BaseModel):
    id: str
    name: str
    type: str
    size: Optional[int] = None
    created_at: str

# Initialize sample data
async def init_sample_data():
    folder_count = await db.folders.count_documents({})
    if folder_count == 0:
        # Create sample folder structure
        root_folders = [
            {"id": "root-1", "name": "Documents", "parent_id": None, "created_at": datetime.now(timezone.utc).isoformat(), "type": "folder"},
            {"id": "root-2", "name": "Pictures", "parent_id": None, "created_at": datetime.now(timezone.utc).isoformat(), "type": "folder"},
            {"id": "root-3", "name": "Downloads", "parent_id": None, "created_at": datetime.now(timezone.utc).isoformat(), "type": "folder"},
            {"id": "root-4", "name": "Music", "parent_id": None, "created_at": datetime.now(timezone.utc).isoformat(), "type": "folder"},
        ]
        
        subfolders = [
            {"id": "sub-1", "name": "Work", "parent_id": "root-1", "created_at": datetime.now(timezone.utc).isoformat(), "type": "folder"},
            {"id": "sub-2", "name": "Personal", "parent_id": "root-1", "created_at": datetime.now(timezone.utc).isoformat(), "type": "folder"},
            {"id": "sub-3", "name": "Projects", "parent_id": "sub-1", "created_at": datetime.now(timezone.utc).isoformat(), "type": "folder"},
            {"id": "sub-4", "name": "Reports", "parent_id": "sub-1", "created_at": datetime.now(timezone.utc).isoformat(), "type": "folder"},
            {"id": "sub-5", "name": "Vacation", "parent_id": "root-2", "created_at": datetime.now(timezone.utc).isoformat(), "type": "folder"},
            {"id": "sub-6", "name": "Family", "parent_id": "root-2", "created_at": datetime.now(timezone.utc).isoformat(), "type": "folder"},
            {"id": "sub-7", "name": "2024", "parent_id": "sub-5", "created_at": datetime.now(timezone.utc).isoformat(), "type": "folder"},
            {"id": "sub-8", "name": "Rock", "parent_id": "root-4", "created_at": datetime.now(timezone.utc).isoformat(), "type": "folder"},
            {"id": "sub-9", "name": "Jazz", "parent_id": "root-4", "created_at": datetime.now(timezone.utc).isoformat(), "type": "folder"},
        ]
        
        sample_files = [
            {"id": "file-1", "name": "README.md", "folder_id": "sub-3", "size": 2048, "mime_type": "text/markdown", "created_at": datetime.now(timezone.utc).isoformat(), "type": "file"},
            {"id": "file-2", "name": "project-plan.docx", "folder_id": "sub-3", "size": 15360, "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "created_at": datetime.now(timezone.utc).isoformat(), "type": "file"},
            {"id": "file-3", "name": "budget.xlsx", "folder_id": "sub-4", "size": 8192, "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "created_at": datetime.now(timezone.utc).isoformat(), "type": "file"},
            {"id": "file-4", "name": "beach.jpg", "folder_id": "sub-7", "size": 2097152, "mime_type": "image/jpeg", "created_at": datetime.now(timezone.utc).isoformat(), "type": "file"},
            {"id": "file-5", "name": "sunset.png", "folder_id": "sub-7", "size": 3145728, "mime_type": "image/png", "created_at": datetime.now(timezone.utc).isoformat(), "type": "file"},
            {"id": "file-6", "name": "notes.txt", "folder_id": "sub-2", "size": 512, "mime_type": "text/plain", "created_at": datetime.now(timezone.utc).isoformat(), "type": "file"},
        ]
        
        await db.folders.insert_many(root_folders + subfolders)
        await db.files.insert_many(sample_files)
        logger.info("Sample data initialized")

# Build folder tree recursively
def build_tree(folders, parent_id=None):
    tree = []
    for folder in folders:
        if folder.get('parent_id') == parent_id:
            children = build_tree(folders, folder['id'])
            tree.append({
                'id': folder['id'],
                'name': folder['name'],
                'parent_id': folder.get('parent_id'),
                'children': children,
                'type': 'folder'
            })
    return tree

# Routes
@api_router.get("/")
async def root():
    return {"message": "Windows Explorer API"}

@api_router.get("/folders/tree", response_model=List[FolderTree])
async def get_folder_tree():
    """Get complete folder structure as tree"""
    folders = await db.folders.find({}, {"_id": 0}).to_list(10000)
    tree = build_tree(folders, None)
    return tree

@api_router.get("/folders/{folder_id}/children", response_model=List[FolderChild])
async def get_folder_children(folder_id: str):
    """Get direct children (folders and files) of a specific folder"""
    if folder_id == "root":
        folders = await db.folders.find({"parent_id": None}, {"_id": 0}).to_list(1000)
    else:
        folders = await db.folders.find({"parent_id": folder_id}, {"_id": 0}).to_list(1000)
    
    files = await db.files.find({"folder_id": folder_id}, {"_id": 0}).to_list(1000)
    
    children = []
    for folder in folders:
        children.append({
            "id": folder['id'],
            "name": folder['name'],
            "type": "folder",
            "created_at": folder['created_at']
        })
    
    for file in files:
        children.append({
            "id": file['id'],
            "name": file['name'],
            "type": "file",
            "size": file['size'],
            "created_at": file['created_at']
        })
    
    return children

@api_router.post("/folders", response_model=Folder)
async def create_folder(folder_input: FolderBase):
    """Create a new folder"""
    folder_obj = Folder(name=folder_input.name, parent_id=folder_input.parent_id)
    
    doc = folder_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.folders.insert_one(doc)
    return folder_obj

@api_router.put("/folders/{folder_id}")
async def rename_folder(folder_id: str, name: str = Query(...)):
    """Rename a folder"""
    result = await db.folders.update_one(
        {"id": folder_id},
        {"$set": {"name": name}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    return {"success": True, "message": "Folder renamed"}

@api_router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str):
    """Delete a folder and all its contents recursively"""
    async def delete_recursive(fid):
        # Find all subfolders
        subfolders = await db.folders.find({"parent_id": fid}, {"_id": 0}).to_list(1000)
        
        # Delete files in this folder
        await db.files.delete_many({"folder_id": fid})
        
        # Recursively delete subfolders
        for subfolder in subfolders:
            await delete_recursive(subfolder['id'])
        
        # Delete the folder itself
        await db.folders.delete_one({"id": fid})
    
    folder = await db.folders.find_one({"id": folder_id})
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    await delete_recursive(folder_id)
    
    return {"success": True, "message": "Folder deleted"}

@api_router.post("/files/upload")
async def upload_file(file: UploadFile = File(...), folder_id: str = Query(...)):
    """Upload a file to a folder"""
    content = await file.read()
    
    file_obj = FileItem(
        name=file.filename,
        folder_id=folder_id,
        size=len(content),
        mime_type=file.content_type or "application/octet-stream"
    )
    
    doc = file_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.files.insert_one(doc)
    
    return file_obj

@api_router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """Delete a file"""
    result = await db.files.delete_one({"id": file_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {"success": True, "message": "File deleted"}

@api_router.get("/search")
async def search(q: str = Query(..., min_length=1)):
    """Search folders and files by name"""
    folders = await db.folders.find(
        {"name": {"$regex": q, "$options": "i"}},
        {"_id": 0}
    ).to_list(100)
    
    files = await db.files.find(
        {"name": {"$regex": q, "$options": "i"}},
        {"_id": 0}
    ).to_list(100)
    
    results = []
    for folder in folders:
        results.append({
            "id": folder['id'],
            "name": folder['name'],
            "type": "folder",
            "parent_id": folder.get('parent_id'),
            "created_at": folder['created_at']
        })
    
    for file in files:
        results.append({
            "id": file['id'],
            "name": file['name'],
            "type": "file",
            "size": file['size'],
            "folder_id": file['folder_id'],
            "created_at": file['created_at']
        })
    
    return results

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    await init_sample_data()

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
