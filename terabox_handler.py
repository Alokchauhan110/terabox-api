# terabox_handler.py (Final Proof Version)
import httpx
import re
import json
import logging
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
}

async def get_files_from_link(terabox_url: str, cookies: str) -> tuple[list | None, str]:
    """
    Tries to get the link via the API.
    On JSONDecodeError, returns the raw response text for debugging.
    Returns: (file_list_or_none, debug_text_or_empty_string)
    """
    try:
        cookie_dict = {item.split('=')[0].strip(): '='.join(item.split('=')[1:]) for item in cookies.split('; ')}
        
        async with httpx.AsyncClient(headers=HEADERS, cookies=cookie_dict, follow_redirects=True, timeout=30.0) as client:
            initial_response = await client.get(terabox_url)
            initial_response.raise_for_status()
            
            final_url = str(initial_response.url)
            surl = parse_qs(urlparse(final_url).query).get('surl', [None])[0]

            if not surl: return None, "Could not find 'surl' in the final URL."

            api_url = f"https://www.terabox.com/api/shorturl?surl={surl}"
            api_headers = HEADERS.copy()
            api_headers['Referer'] = 'https://www.terabox.com/'
            
            api_response = await client.get(api_url, headers=api_headers)
            api_response.raise_for_status()

            try:
                # This is the line that is failing
                api_data = api_response.json()
            except json.JSONDecodeError:
                logger.error("Failed to decode JSON. The response is likely an HTML page (bad cookie).")
                # THIS IS THE CRITICAL DEBUGGING STEP: RETURN THE HTML
                return None, api_response.text

            if api_data.get("errno") != 0 or not api_data.get("list"):
                return None, f"API returned an error or empty list: {api_data}"
            
            formatted_files = [{
                "file_name": item.get("server_filename"),
                "direct_link": item.get("dlink"),
                "size_bytes": int(item.get("size", 0)),
                "thumbnail": item.get("thumbs", {}).get("url3")
            } for item in api_data["list"]]
            
            return formatted_files, "" # Success!

    except Exception as e:
        logger.error(f"An error occurred in get_files_from_link: {e}", exc_info=True)
        return None, f"An unexpected exception occurred: {str(e)}"