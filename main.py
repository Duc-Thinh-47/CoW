import os
import csv
import time
import re 
from dotenv import load_dotenv
import numpy as np

from pdf_parse import process_pdf 
from web_scrape import fetch_bank_keyword_mentions
from entropy import proportion_normalization, calculate_entropy_weights, calculate_final_scores
from manual_helper import run_manual_web_helper

def get_completed_searches(csv_filename):
    """Reads the CSV to find which Year+Bank+Keyword combos are already done."""
    completed = set()
    if os.path.exists(csv_filename):
        with open(csv_filename, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None) # Skip header
            for row in reader:
                # Check for at least 3 columns to include the Year
                if len(row) >= 3:
                    year = row[0].strip()
                    bank = row[1].strip()
                    # Force the keyword from the CSV to lowercase to match our master list!
                    keyword = row[2].strip().lower() 
                    # The signature is now 3D (Year_Bank_Keyword)
                    completed.add(f"{year}_{bank}_{keyword}")
    return completed

def handle_pdfs(banks_data, PDF_OUTPUT_FILE, KEYWORDS_DICT):
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
            # Added 'Year' to the start of the headers
            writer.writerow(['Year', 'Bank', 'KeywordIndex', 'TotalResults'])
        
        for bank_row in banks_data:
            bank_name = bank_row['Bank_Name'].strip()
            raw_pdf_string = bank_row['PDF_Files']
            pdf_files = [pdf.strip() for pdf in raw_pdf_string.split('|') if pdf.strip()]
            
            print(f"🏦 Processing PDFs for {bank_name} ({len(pdf_files)} PDFs found)...")
            
            for pdf_name in pdf_files:
                # Extract the 4-digit year from the filename (e.g., 'uob_2025.pdf' -> '2025')
                match = re.search(r'(\d{4})', pdf_name)
                if not match:
                    print(f"  ⚠️ Skipping {pdf_name}: Could not find a year in the filename.")
                    continue
                year = match.group(1)

                # If the first KeywordIndex for this bank AND year is in our completed list, skip it!
                first_kw_index = list(KEYWORDS_DICT.keys())[0] if KEYWORDS_DICT else None
                if first_kw_index and f"{year}_{bank_name}_{first_kw_index.lower()}" in completed_searches:
                    print(f"  ⏭️ Skipping '{bank_name}' PDFs for {year} (Already in CSV)")
                    continue

                pdf_path = os.path.join("data/raw_pdfs", pdf_name) # Ensure your path is correct here
                
                if not os.path.exists(pdf_path):
                    print(f"  ❌ Missing file: {pdf_path}. Skipping this file.")
                    continue
                
                # Initialize buckets for Kw1, Kw2, etc.
                total_bank_counts = {kw_index: 0 for kw_index in KEYWORDS_DICT.keys()}
                
                # Flatten the dictionary into a single massive list of all secondary words
                # so the PDF parser knows exactly what individual strings to look for.
                all_words_to_find = [word for sublist in KEYWORDS_DICT.values() for word in sublist]
                
                # Get the raw counts for every individual word found in the PDF
                pdf_counts = process_pdf(pdf_path, all_words_to_find)
                
                # Pool the raw counts back into their main KeywordIndex buckets
                for kw_index, kw_list in KEYWORDS_DICT.items():
                    for word in kw_list:
                        total_bank_counts[kw_index] += pdf_counts.get(word, 0)
            
                # Save the pooled counts using the Kw Index so it perfectly matches the Web Scraper output
                # NEW: Including the extracted year in the row writer
                for kw_index in KEYWORDS_DICT.keys():
                    writer.writerow([year, bank_name, kw_index, total_bank_counts[kw_index]])
                
                out_f.flush()
                total_hits = sum(total_bank_counts.values())
                print(f"  ✅ Finished {bank_name} ({year}). Total PDF keyword hits: {total_hits}")
            
            print("-" * 40)

    print(f"🎉 PDF Pipeline Complete! Saved to {PDF_OUTPUT_FILE}\n")

def handle_web_scraping(banks_data, WEB_OUTPUT_FILE, KEYWORDS_DICT, API_KEY):
    """Processes SerpApi web scraping for all banks in our inventory."""
    print(f"🚀 [MODULE 2] Starting Web Scraper for {len(banks_data)} banks...\n")
    
    # 1. Check what we have already completed to save API credits
    completed_searches = get_completed_searches(WEB_OUTPUT_FILE)
    file_exists = os.path.exists(WEB_OUTPUT_FILE)
    
    # 2. Open the CSV file in 'append' mode ('a')
    with open(WEB_OUTPUT_FILE, mode='a', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        
        if not file_exists:
            # Note: Changed 'Keyword' to 'KeywordIndex' and added 'Year'
            writer.writerow(['Year', 'Bank', 'KeywordIndex', 'TotalResults'])

        for bank_row in banks_data:
            bank_name = bank_row['Bank_Name'].strip()
            domain = bank_row['Domain'].strip()
            
            # Skip if the bank doesn't have a valid domain
            if not domain:
                print(f"  ⚠️ No domain found for {bank_name}. Skipping web scrape.")
                continue

            # Loop through 10 fiscal years backward from 2025
            for year in range(2025, 2014, -1):
                year_str = str(year)

                # Loop through the Dictionary keys (Kw1, Kw2, etc.) and their lists of words
                for kw_index, kw_list in KEYWORDS_DICT.items():
                    # 3D search ID tracking
                    search_id = f"{year_str}_{bank_name}_{kw_index.lower()}"
                    main_keyword = kw_list[0] # The first word in the list is our display name
                    
                    if search_id in completed_searches:
                        print(f"  ⏭️ Skipping '{bank_name} + {kw_index}' for {year_str} (Already in CSV)")
                        continue

                    print(f"🌐 Fetching: {bank_name} -> {kw_index} ({main_keyword}) [{year_str}]...")
                    
                    # Build the OR query string
                    # This turns ["FinTech", "E-finance"] into: '("FinTech" OR "E-finance")'
                    or_query = "(" + " OR ".join([f'"{kw}"' for kw in kw_list]) + ")"
                    
                    # Hand the task to the Dumb Worker, passing the massive OR string instead of one word
                    # NEW: Passing year_str as the 4th argument so the scraper can filter by date
                    total_hits = fetch_bank_keyword_mentions(domain, or_query, API_KEY, year_str)
                    
                    # If we hit an API limit/error, safely exit the scraper module
                    if total_hits == -1:
                        print("\n🛑 Stopping Web Scraper due to API error. Progress saved.")
                        return

                    # Save the result immediately using the kw_index (Kw1) and flush
                    writer.writerow([year_str, bank_name, kw_index, total_hits])
                    csv_file.flush() 

                    print(f"  ✅ Found {total_hits} results.")
                    
                    # Polite delay for the API
                    time.sleep(2.0) 
                    
            print("-" * 40)
            
    print(f"🎉 Web Extraction Complete! Saved to {WEB_OUTPUT_FILE}\n")

def calculate_fintech_index(PDF_FILE, WEB_FILE, FINAL_OUTPUT_FILE, KEYWORDS, banks_data):
    """Combines CSV data, executes the entropy math, and outputs final rankings per year."""
    print(f"🧮 [MODULE 3] Starting Time-Series Entropy Math & Index Calculation...\n")
    
    bank_names = [row['Bank_Name'].strip() for row in banks_data]
    
    # 1. Initialize data structure to hold the combined sums
    # 3D dictionary structure (Year -> Bank -> Keyword)
    combined_data = {str(y): {b: {kw: 0.0 for kw in KEYWORDS} for b in bank_names} for y in range(2025, 2014, -1)}

    # Helper function to read a CSV and add its numbers to our combined dictionary
    def load_and_add_results(filename):
        if not os.path.exists(filename):
            print(f"  ⚠️ Could not find {filename}. Assuming 0 for this source.")
            return
        with open(filename, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  
            for row in reader:
                # NEW: Checking for 4 columns (Year, Bank, Kw, Count)
                if len(row) >= 4:
                    year, bank, kw, count = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
                    try:
                        count = float(count)
                        # Ensure we only track banks/keywords/years from our master lists
                        if year in combined_data and bank in combined_data[year] and kw in combined_data[year][bank]:
                            combined_data[year][bank][kw] += count
                    except ValueError:
                        pass

    # 2. Add PDF hits and Web hits together
    print("  📥 Consolidating PDF and Web footprint data across all years...")
    load_and_add_results(PDF_FILE)
    load_and_add_results(WEB_FILE)

    # 6. Save the final report (Moved to wrap the year loop)
    # Open in 'w' mode to overwrite old runs with fresh calculations
    with open(FINAL_OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Year", "Rank", "Bank", "Fintech_Index_Score"])

        # Execute math for every year individually
        for year in range(2025, 2014, -1):
            year_str = str(year)
            print(f"\n  ⚙️ Processing data for {year_str}...")

            # 3. Pivot the data into a 2D Matrix (Rows=Banks, Cols=Keywords) for THIS year
            raw_data_matrix = []
            for bank in bank_names:
                row_values = [combined_data[year_str][bank][kw] for kw in KEYWORDS]
                raw_data_matrix.append(row_values)

            raw_data_matrix = np.array(raw_data_matrix, dtype=float)
            
            # Skip if matrix is entirely zeroes (no data collected for this year yet)
            if np.sum(raw_data_matrix) == 0:
                print(f"  ⚠️ No data found for {year_str}. Skipping.")
                continue
                
            print(f"  ✅ Built {raw_data_matrix.shape[0]}x{raw_data_matrix.shape[1]} raw data matrix.")

            # 4. Pass the Matrix into the Entropy Engine
            print("  ⚙️ Running Entropy Weight Method...")
            
            # Step 1: Normalize down the columns
            P_matrix = proportion_normalization(raw_data_matrix, axis=0)
            
            # Step 2: Calculate the weights of each keyword
            E, W = calculate_entropy_weights(P_matrix)
            
            # Step 3: Multiply and calculate final scores
            final_scores = calculate_final_scores(P_matrix, W)

            # 5. Zip the scores back to the bank names and sort them from highest to lowest
            ranked_banks = list(zip(bank_names, final_scores))
            ranked_banks.sort(key=lambda x: x[1], reverse=True)

            # Save scores to CSV
            for rank, (bank, score) in enumerate(ranked_banks, start=1):
                writer.writerow([year_str, rank, bank, round(score, 6)])

    print(f"\n🎉 SUCCESS! Final Time-Series Fintech Index saved to: {FINAL_OUTPUT_FILE}")


def main():
    load_dotenv()
    API_KEY = os.environ.get("SERPAPI_KEY")
    
    # === 🎛️ MASTER COMMAND CENTER ===
    # Set these to True or False to run specific parts of the pipeline
    RUN_PDF_MODULE = True
    RUN_WEB_MODULE = False
    RUN_INDEX_CALCULATION = True
    RUN_MANUAL_WEB_HELPER = True
    # ===============================================

    # --- CONFIGURATION ---
    INVENTORY_FILE = "data/bank_inventory.csv"
    # KEYWORD_INVENTORY_FILE = "data/keyword_inventory.csv" 
    KEYWORD_INVENTORY_FILE = "data/test_kw_inventory.csv" # shorten list for testing
    PDF_OUTPUT_FILE = "data/fintech_index_pdf_results.csv"
    WEB_OUTPUT_FILE = "data/fintech_index_web_results.csv"
    FINAL_OUTPUT_FILE = "data/fintech_index_final_scores.csv"

    os.makedirs("data", exist_ok=True)

    # --- STEP 1: LOAD KEYWORDS ---
    keywords_dict = {}
    try:
        with open(KEYWORD_INVENTORY_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                kw_index = row['KeywordIndex'].strip()
                keyword = row['Keyword'].strip().lower()
                
                if kw_index not in keywords_dict:
                    keywords_dict[kw_index] = []
                keywords_dict[kw_index].append(keyword)
    except FileNotFoundError:
        print(f"🚨 ERROR: {KEYWORD_INVENTORY_FILE} not found!")
        return
    
    KEYWORDS = keywords_dict

    # --- STEP 2: LOAD MASTER INVENTORY ---
    banks_data = []
    try:
        with open(INVENTORY_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                banks_data.append(row)
    except FileNotFoundError:
        print(f"🚨 ERROR: {INVENTORY_FILE} not found!")
        return

    # --- STEP 3 & 4: EXECUTE PIPELINE VIA TOGGLES ---
    if RUN_PDF_MODULE:
        handle_pdfs(banks_data, PDF_OUTPUT_FILE, KEYWORDS)
    else:
        print("⏸️  Skipping PDF Module (Toggle is Off)")
        
    if RUN_WEB_MODULE:
        if not API_KEY:
            print("🚨 WARNING: Missing SERPAPI_KEY in .env file! Skipping Web Scraper module.")
        else:
            handle_web_scraping(banks_data, WEB_OUTPUT_FILE, KEYWORDS, API_KEY)
    else:
        print("⏸️  Skipping Web Module (Toggle is Off)")
    
    if RUN_MANUAL_WEB_HELPER:
        run_manual_web_helper(banks_data, WEB_OUTPUT_FILE, KEYWORDS)
    else:
        print("⏸️  Skipping Manual Web Helper (Toggle is Off)")

    if RUN_INDEX_CALCULATION:
        calculate_fintech_index(PDF_OUTPUT_FILE, WEB_OUTPUT_FILE, FINAL_OUTPUT_FILE, KEYWORDS, banks_data)
    else:
        print("⏸️  Skipping Index Calculation (Toggle is Off)")

if __name__ == "__main__":
    main()