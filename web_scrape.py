import requests

def fetch_bank_keyword_mentions(domain, keyword, api_key):
    """
    Queries SerpApi for the keyword on the bank's domain.
    Acts as the "Dumb Worker": takes a target and returns a number.
    
    Args:
        domain (str): The website domain to search (e.g., 'vietcombank.com.vn').
        keyword (str): The keyword to search for.
        api_key (str): Your SerpApi key.
        
    Returns:
        int: The number of total search results, or -1 if there's a hard API error.
    """
    # Note: Using the exact string passed in from handle_web_scraping
    query = f"site:{domain} {keyword}"
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": query,
        "gl": "vn", # Assuming Vietnam default; SerpApi handles this gracefully
        "num": 100, # Max results per page; we will count them if total_results is hidden
        "api_key": api_key
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() 
        data = response.json()

        # Check for API errors (e.g., out of credits)
        if "error" in data:
            print(f"   🚨 API Error: {data['error']}")
            return -1 # Return -1 to signal a hard stop

        # 1. Try to extract the official total results number safely
        total_results = data.get('search_information', {}).get('total_results')

        # 2. If Google hides the estimate, count the actual results on the page
        if total_results is None:
            organic_results = data.get('organic_results', [])
            total_results = len(organic_results)
            # Optional debug print so you can see when the fallback triggers
            print(f"      [Debug: Used fallback count: {total_results}]")

        # Convert to int just in case SerpApi returned a string
        return int(total_results)

    except Exception as e:
        print(f"   ❌ Error processing {domain} for '{keyword}': {e}")
        return 0