# terabox_handler.py (Final Production Version with Link Resolution)
import httpx
import re
import json
import logging
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Referer': 'https://www.terabox.com/'
}

async def get_files_from_link(terabox_url: str, cookies: str) -> list | None:
    try:
        cookie_dict = {item.split('=')[0].strip(): '='.join(item.split('=')[1:]) for item in cookies.split('; ')}
        
        async with httpx.AsyncClient(headers=HEADERS, cookies=cookie_dict, follow_redirects=True, timeout=30.0) as client:
            
            # Step 1: Get the initial page to find the 'surl'
            initial_response = await client.get(terabox_url)
            initial_response.raise_for_status()
            
            final_url = str(initial_response.url)
            surl = parse_qs(urlparse(final_url).query).get('surl', [None])[0]

            if not surl:
                logger.error("Could not find 'surl' in the final URL.")
                return None

            # Step 2: Call the API with the 'surl' to get the initial file list
            api_url = f"https://www.terabox.com/api/shorturl?surl={surl}"
            api_response = await client.get(api_url)
            api_response.raise_for_status()
            
            try:
                api_data = api_response.json()
            except json.JSONDecodeError:
                logger.error("Failed to decode JSON. The response is likely an HTML page (bad cookie).")
                return None

            if api_data.get("errno") != 0 or not api_data.get("list"):
                logger.error(f"Terabox API returned an error or empty list: {api_data}")
                return None
            
            file_list_data = api_data["list"]
            
            # Step 3: Process each file to resolve the final download link
            formatted_files = []
            for item in file_list_data:
                initial_dlink = item.get("dlink")
                if not initial_dlink:
                    continue

                # NEW LOGIC: Resolve the dlink to get the final, high-speed URL
                try:
                    # Make a HEAD request to the initial dlink to find the redirect location
                    head_response = await client.head(initial_dlink, follow_redirects=False)
                    if 300 <= head_response.status_code < 400:
                        final_download_url = head_response.headers.get('location')
                    else:
                        final_download_url = initial_dlink # Fallback if no redirect
                except Exception as e:
                    logger.warning(f"Could not resolve dlink, falling back. Error: {e}")
                    final_download_url = initial_dlink

                formatted_files.append({
                    "file_name": item.get("server_filename"),
                    "direct_link": final_download_url, # We now use the fast link as the main link
                    "size_bytes": int(item.get("size", 0)),
                    "thumbnail": item.get("thumbs", {}).get("url3")
                })
            
            logger.info(f"SUCCESS! Extracted and resolved {len(formatted_files)} file(s).")
            return formatted_files

    except Exception as e:
        logger.error(f"An error occurred in get_files_from_link: {e}", exc_info=True)
        return None