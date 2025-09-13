# main.py (Temporary Version for Direct Browser Testing)
import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# We don't need Security or Header for this simple test
# from fastapi import Security, Header
# from fastapi.security import APIKeyHeader
# from dotenv import load_dotenv # Not needed on Koyeb, but good practice

from terabox_handler import get_files_from_link

# load_dotenv() # Not needed on Koyeb
logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Terabox Link API", description="An API to get direct download links from Terabox URLs.")

# --- Environment Variables ---
TERABOX_COOKIE = os.getenv("TERABOX_COOKIE")
API_KEY = os.getenv("API_KEY")

# --- Pydantic Models for Data Structure ---
class FileResponse(BaseModel):
    file_name: str
    direct_link: str
    size_bytes: int
    thumbnail: Optional[str] = None

# ====================================================================
# THIS IS THE NEW, TEMPORARY ENDPOINT FOR BROWSER TESTING
# ====================================================================
@app.get("/v1/get_link_test", response_model=List[FileResponse])
async def get_link_test_endpoint(url: str, api_key: str):
    """
    A temporary GET endpoint for easy browser testing.
    Accepts url and api_key as query parameters.
    Example: /v1/get_link_test?api_key=YOUR_KEY&url=YOUR_URL
    """
    # 1. Manually check the API key from the URL
    if not API_KEY or api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key provided in URL")
    
    # 2. Check for the cookie on the server
    if not TERABOX_COOKIE:
        raise HTTPException(status_code=500, detail="Server is not configured with TERABOX_COOKIE")

    # 3. Call the scraper function
    logging.info(f"Processing URL via test endpoint: {url}")
    file_data = await get_files_from_link(url, TERABOX_COOKIE)

    # 4. Handle the result
    if file_data is None:
        raise HTTPException(
            status_code=404,
            detail="Failed to retrieve file data. Link may be invalid, private, or the cookie has expired."
        )
    
    return file_data
# ====================================================================

@app.get("/")
def read_root():
    """Root endpoint for health checks."""
    return {"status": "ok", "message": "Terabox API is running"}