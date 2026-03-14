import os
import csv
import time
from dotenv import load_dotenv

# Import our two "Dumb Workers"
from pdf_parse import process_pdf 
from web_scrape import fetch_bank_keyword_mentions

def get_completed_searches(csv_filename):
    """Reads the CSV to find which Bank+Keyword combos are already done."""
    completed = set()
    if os.path.exists(csv_filename):
        with open(csv_filename, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None) # Skip header
            for row in reader:
                if len(row) >= 2:
                    bank = row[0]
                    # Force the keyword from the CSV to lowercase to match our master list!
                    keyword = row[1].lower() 
                    completed.add(f"{bank}_{keyword}")
    return completed

def handle_pdfs(banks_data, PDF_OUTPUT_FILE, KEYWORDS):
    """Processes all PDFs for the banks in our inventory."""
    print(f"\n🚀 [MODULE 1] Starting PDF Extraction for {len(banks_data)} banks...\n")
    
    # 1. Check what we have already completed 
    completed_searches = get_completed_searches(PDF_OUTPUT_FILE)
    file_exists = os.path.exists(PDF_OUTPUT_FILE)
    
    # 2. Changed mode='w' to mode='a' so we don't overwrite
    with open(PDF_OUTPUT_FILE, mode='a', newline='', encoding='utf-8') as out_f:
        writer = csv.writer(out_f)
        
        # Write headers only if it's a new file
        if not file_exists:
            writer.writerow(['Bank', 'Keyword', 'TotalResults'])
        
        for bank_row in banks_data:
            bank_name = bank_row['Bank_Name'].strip()
            
            # NEW: If the first keyword for this bank is in our completed list, 
            # we know this entire bank has already been processed. Skip it!
            if KEYWORDS and f"{bank_name}_{KEYWORDS[0]}" in completed_searches:
                print(f"   ⏭️ Skipping '{bank_name}' PDFs (Already in CSV)")
                continue
            
            raw_pdf_string = bank_row['PDF_Files']
            pdf_files = [pdf.strip() for pdf in raw_pdf_string.split('|') if pdf.strip()]
            
            print(f"🏦 Processing PDFs for {bank_name} ({len(pdf_files)} PDFs found)...")
            total_bank_counts = {kw: 0 for kw in KEYWORDS}
            
            for pdf_name in pdf_files:
                pdf_path = os.path.join("data", pdf_name) # Ensure your path is correct here
                
                if not os.path.exists(pdf_path):
                    print(f"   ❌ Missing file: {pdf_path}. Skipping this file.")
                    continue
                    
                pdf_counts = process_pdf(pdf_path, KEYWORDS)
                
                for kw in KEYWORDS:
                    total_bank_counts[kw] += pdf_counts.get(kw, 0)
            
            for kw in KEYWORDS:
                writer.writerow([bank_name, kw, total_bank_counts[kw]])
            
            out_f.flush()
            total_hits = sum(total_bank_counts.values())
            print(f"   ✅ Finished {bank_name}. Total PDF keyword hits: {total_hits}")
            print("-" * 40)

    print(f"🎉 PDF Pipeline Complete! Saved to {PDF_OUTPUT_FILE}\n")

def handle_web_scraping(banks_data, WEB_OUTPUT_FILE, KEYWORDS, API_KEY):
    """Processes SerpApi web scraping for all banks in our inventory."""
    print(f"🚀 [MODULE 2] Starting Web Scraper for {len(banks_data)} banks...\n")
    
    # 1. Check what we have already completed to save API credits
    completed_searches = get_completed_searches(WEB_OUTPUT_FILE)
    file_exists = os.path.exists(WEB_OUTPUT_FILE)
    
    # 2. Open the CSV file in 'append' mode ('a')
    with open(WEB_OUTPUT_FILE, mode='a', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        
        if not file_exists:
            writer.writerow(['Bank', 'Keyword', 'TotalResults'])

        for bank_row in banks_data:
            bank_name = bank_row['Bank_Name'].strip()
            domain = bank_row['Domain'].strip()
            
            # Skip if the bank doesn't have a valid domain
            if not domain:
                print(f"   ⚠️ No domain found for {bank_name}. Skipping web scrape.")
                continue

            for kw in KEYWORDS:
                search_id = f"{bank_name}_{kw}"
                
                if search_id in completed_searches:
                    print(f"   ⏭️ Skipping '{bank_name} + {kw}' (Already in CSV)")
                    continue

                print(f"🌐 Fetching: {bank_name} -> '{kw}'...")
                
                # Hand the task to the Dumb Worker
                total_hits = fetch_bank_keyword_mentions(domain, kw, API_KEY)
                
                # If we hit an API limit/error, safely exit the scraper module
                if total_hits == -1:
                    print("\n🛑 Stopping Web Scraper due to API error. Progress saved.")
                    return

                # Save the result immediately and flush
                writer.writerow([bank_name, kw, total_hits])
                csv_file.flush() 

                print(f"   ✅ Found {total_hits} results.")
                
                # Polite delay for the API
                time.sleep(1.5) 
                
            print("-" * 40)
            
    print(f"🎉 Web Extraction Complete! Saved to {WEB_OUTPUT_FILE}\n")

def main():
    # Load environment variables (for SerpApi key)
    load_dotenv()
    API_KEY = os.environ.get("SERPAPI_KEY")
    
    # --- CONFIGURATION ---
    INVENTORY_FILE = "data/bank_inventory.csv"
    KEYWORD_INVENTORY_FILE = "data/keyword_inventory.csv" 
    PDF_OUTPUT_FILE = "data/fintech_index_pdf_results.csv"
    WEB_OUTPUT_FILE = "data/fintech_index_web_results.csv"

    os.makedirs("data", exist_ok=True)

    # --- STEP 1: LOAD KEYWORDS ---
    print(f"🔑 Loading keywords from {KEYWORD_INVENTORY_FILE}...")
    loaded_keywords = set()
    try:
        with open(KEYWORD_INVENTORY_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                keyword = row['Keyword'].strip().lower() 
                if keyword:
                    loaded_keywords.add(keyword)
    except FileNotFoundError:
        print(f"🚨 ERROR: {KEYWORD_INVENTORY_FILE} not found!")
        return 
    
    KEYWORDS = list(loaded_keywords)
    print(f"   ✅ Successfully loaded {len(KEYWORDS)} unique keywords.\n")

    # --- STEP 2: LOAD MASTER INVENTORY ONCE ---
    print(f"📖 Reading master inventory from {INVENTORY_FILE}...")
    banks_data = []
    try:
        with open(INVENTORY_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                banks_data.append(row)
    except FileNotFoundError:
        print(f"🚨 ERROR: {INVENTORY_FILE} not found!")
        return
    print(f"   ✅ Successfully loaded {len(banks_data)} banks.\n")

    # --- STEP 3: EXECUTE PIPELINES ---
    # Pass the exact same data to both modules
    handle_pdfs(banks_data, PDF_OUTPUT_FILE, KEYWORDS)
    
    if not API_KEY:
        print("🚨 WARNING: Missing SERPAPI_KEY in .env file! Skipping Web Scraper module.")
    else:
        handle_web_scraping(banks_data, WEB_OUTPUT_FILE, KEYWORDS, API_KEY)

    print("🏁 ALL PIPELINES COMPLETE! You are ready for the Entropy Calculator.")

if __name__ == "__main__":
    main()