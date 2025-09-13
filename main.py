# main.py
import os
import logging
from fastapi import FastAPI, HTTPException, Security, Header
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import List, Optional

from terabox_handler import get_files_from_link

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Terabox Link API", description="An API to get direct download links from Terabox URLs.")

TERABOX_COOKIE = os.getenv("TERABOX_COOKIE")
API_KEY = os.getenv("API_KEY")

api_key_header_scheme = APIKeyHeader(name="X-API-Key")

def validate_api_key(x_api_key: str = Security(api_key_header_scheme)):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")

class LinkRequest(BaseModel):
    url: str

class FileResponse(BaseModel):
    file_name: str
    direct_link: str
    size_bytes: int
    thumbnail: Optional[str] = None

@app.post("/v1/get_link", response_model=List[FileResponse], dependencies=[Security(validate_api_key)])
async def get_link_endpoint(request: LinkRequest):
    if not TERABOX_COOKIE:
        raise HTTPException(status_code=500, detail="Server is not configured with TERABOX_COOKIE")
    
    file_data = await get_files_from_link(request.url, TERABOX_COOKIE)

    if file_data is None:
        raise HTTPException(status_code=404, detail="Failed to retrieve file data. Link may be invalid, private, or the cookie has expired.")
    
    return file_data

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Terabox API is running"}