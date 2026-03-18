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
    query = f'site:{domain} "{keyword}"'
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": query,
        "gl": "vn", # Assuming Vietnam default; SerpApi handles this gracefully
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

        # Extract the total results number safely
        total_results = data.get('search_information', {}).get('total_results', 0)
        return total_results

    except Exception as e:
        print(f"   ❌ Error processing {domain} for '{keyword}': {e}")
        return 0