# terabox_handler.py (Master Diagnostic Version)
import httpx
import re
import json
import logging
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.terabox.com/'
}

async def get_files_from_link(terabox_url: str, cookies: str) -> tuple[list | None, dict]:
    """
    Tries to get the link via the API.
    On failure, returns a dictionary with detailed debug information.
    """
    debug_info = {}
    try:
        cookie_dict = {item.split('=')[0].strip(): '='.join(item.split('=')[1:]) for item in cookies.split('; ')}
        
        async with httpx.AsyncClient(headers=HEADERS, cookies=cookie_dict, follow_redirects=True, timeout=30.0) as client:
            initial_response = await client.get(terabox_url)
            initial_response.raise_for_status()
            
            final_url = str(initial_response.url)
            debug_info['final_redirected_url'] = final_url
            
            surl = parse_qs(urlparse(final_url).query).get('surl', [None])[0]
            debug_info['extracted_surl'] = surl

            if not surl:
                debug_info['error'] = "Could not find 'surl' in the final URL."
                return None, debug_info

            api_url = f"https://www.terabox.com/api/shorturl?surl={surl}"
            debug_info['constructed_api_url'] = api_url
            
            api_response = await client.get(api_url)
            api_response.raise_for_status()
            
            try:
                api_data = api_response.json()
            except json.JSONDecodeError:
                debug_info['error'] = "Failed to decode JSON. Terabox API did not return valid JSON. This is the classic sign of an invalid/expired cookie."
                debug_info['raw_response_from_api'] = api_response.text[:500] + "..." # Get a snippet of the HTML
                return None, debug_info

            if api_data.get("errno") != 0 or not api_data.get("list"):
                debug_info['error'] = "Terabox API returned a valid JSON but with an error."
                debug_info['api_json_response'] = api_data
                return None, debug_info
            
            # If we reach here, it's a success!
            formatted_files = [{
                "file_name": item.get("server_filename"),
                "direct_link": item.get("dlink"),
                "size_bytes": int(item.get("size", 0)),
                "thumbnail": item.get("thumbs", {}).get("url3")
            } for item in api_data["list"]]
            
            return formatted_files, {"status": "Success"}

    except Exception as e:
        debug_info['error'] = f"An unexpected exception occurred: {str(e)}"
        logger.error(f"An error occurred in get_files_from_link: {e}", exc_info=True)
        return None, debug_info