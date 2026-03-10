import os
import time
import requests
import csv
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "fintech_index_website_raw_data.csv")

def fetch_bank_keyword_mentions(domain, keyword, api_key):
    """Queries SerpApi for the keyword on the bank's domain."""
    query = f'site:{domain} "{keyword}"'
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": query,
        "gl": "vn",
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

        total_results = data.get('search_information', {}).get('total_results', 0)
        return total_results

    except Exception as e:
        print(f"   ❌ Error processing {domain}: {e}")
        return 0

def get_completed_searches(csv_filename):
    """Reads the CSV to find which Bank+Keyword combos are already done."""
    os.makedirs(DATA_DIR, exist_ok=True)
    completed = set()
    if os.path.exists(csv_filename):
        with open(csv_filename, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None) # Skip header
            for row in reader:
                if len(row) >= 2:
                    bank, keyword = row[0], row[1]
                    completed.add(f"{bank}_{keyword}")
    return completed

def main():
    API_KEY = os.environ.get("SERPAPI_KEY")
    if not API_KEY:
        print("🚨 ERROR: Missing SERPAPI_KEY! Please check your .env file.")
        return
    
    # 1. Check what we have already completed to save API credits
    completed_searches = get_completed_searches(OUTPUT_FILE)

    # 2. Open the CSV file in 'append' mode ('a'). 
    # This ensures we add to the end of the file instead of overwriting it.
    file_exists = os.path.exists(OUTPUT_FILE)
    
    with open(OUTPUT_FILE, mode='a', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        
        # Write headers if it's a brand new file
        if not file_exists:
            writer.writerow(['Bank', 'Keyword', 'TotalResults'])

        banks = {
            'Vietcombank': 'vietcombank.com.vn',
            #'Techcombank': 'techcombank.com',
            #'MB Bank': 'mbbank.com.vn',
            # Add your full list of banks here
        }

        keywords = [
            'Blockchain', 
            'fintech', 
            #'BaaS'
            # Add your full list of keywords here
        ]

        print(f"🚀 Starting Data Extraction (Saving to {OUTPUT_FILE})...\n")

        for bank_name, domain in banks.items():
            for kw in keywords:
                # Create a unique ID for this search to check against our completed list
                search_id = f"{bank_name}_{kw}"
                
                if search_id in completed_searches:
                    print(f"   ⏭️ Skipping '{bank_name} + {kw}' (Already in CSV)")
                    continue

                print(f"🏦 Fetching: {bank_name} -> '{kw}'...")
                
                total_hits = fetch_bank_keyword_mentions(domain, kw, API_KEY)
                
                # If we hit an API limit/error, safely exit the script
                if total_hits == -1:
                    print("\n🛑 Stopping execution due to API error. Progress has been saved.")
                    return

                # Save the result immediately to the CSV
                writer.writerow([bank_name, kw, total_hits])
                
                # Flush forces Python to write to the hard drive immediately 
                # instead of holding it in memory
                csv_file.flush() 

                print(f"   ✅ Found {total_hits} results. Saved.")
                
                # Polite delay for the API
                time.sleep(1.5) 
                
            print("-" * 40)
            
    print(f"\n🎉 Extraction Complete! Data is ready in {OUTPUT_FILE}")

if __name__ == "__main__":
    main()