import re
import requests

def fetch_bank_keyword_mentions(domain, keyword, api_key):
    """
    Queries SerpApi for the keyword on the bank's domain.
    Implements a 4-step fallback to capture missing Total Results 
    while bypassing Google's estimate blocks.
    """
    query = f"site:{domain} {keyword}"
    url = "https://serpapi.com/search"
    
    # Base parameters (num=100 per your spec, no filter=0)
    params = {
        "engine": "google",
        "q": query,
        "gl": "vn", 
        "num": "100",   
        "filter": "0",
        "api_key": api_key
    }

    try:
        # ==========================================
        # ATTEMPT 1: Get total results from the initial API call
        # ==========================================
        response = requests.get(url, params=params)
        response.raise_for_status() 
        data = response.json()

        if "error" in data:
            print(f"   🚨 API Error: {data['error']}")
            return -1 

        # 1. Look for the official estimate
        total_results = data.get('search_information', {}).get('total_results')
        if total_results is not None:
            return int(total_results)

        # ==========================================
        # PAGINATION CHECK & ORGANIC FALLBACK
        # ==========================================
        organic_results = data.get('organic_results', [])
        pagination = data.get('serpapi_pagination', {})
        other_pages = pagination.get('other_pages', {})

        # If there is no pagination at all, everything fits on this single page
        if not other_pages:
            return len(organic_results)

        # Find the highest page number available in the pagination dict (e.g., "10")
        highest_page_key = str(max([int(k) for k in other_pages.keys()]))
        last_page_url = other_pages[highest_page_key]
        
        # Extract the 'start' parameter from that URL using Regex
        start_match = re.search(r'start=(\d+)', last_page_url)
        if not start_match:
            # Failsafe: If Google gave a weird URL, just use the organic count from Page 1
            return len(organic_results)
            
        jump_start = int(start_match.group(1))

        # ==========================================
        # THE JUMP: Attempt 2 & Final Fallback (Page N)
        # ==========================================
        # Add the start parameter to our payload and make the 2nd API call
        params['start'] = jump_start
        response2 = requests.get(url, params=params)
        response2.raise_for_status()
        data2 = response2.json()
        
        # Check for the hidden Vietnamese footer text
        dmca_block = data2.get("dmca_messages", {})
        if "messages" in dmca_block:
            for msg in dmca_block["messages"]:
                content = msg.get("content", "")
                # Hunt for the specific string "giống với [number] kết quả"
                match = re.search(r'giống với ([\d\.,]+) kết quả', content)
                if match:
                    clean_num = match.group(1).replace('.', '').replace(',', '')
                    # print(f"      [Debug: Extracted {clean_num} from footer!]")
                    return int(clean_num)

        # Final Fallback: The Math (Total = Offset + Remainder)
        # We check search_parameters to see where Google *actually* landed us
        actual_start = data2.get("search_parameters", {}).get("start", jump_start)
        last_page_organic_count = len(data2.get("organic_results", []))
        
        final_calculated_total = int(actual_start) + last_page_organic_count
        print(f"      [Debug: Calculated Total: {actual_start} (Offset) + {last_page_organic_count} (Remainder) = {final_calculated_total}]")
        
        return final_calculated_total

    except Exception as e:
        print(f"   ❌ Error processing {domain} for '{keyword}': {e}")
        return 0