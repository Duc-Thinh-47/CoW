import os
import csv
import pyperclip

def get_completed_searches(csv_filename):
    """Reads the CSV to find which Year+Bank+Keyword combos are already done."""
    completed = set()
    if os.path.exists(csv_filename):
        with open(csv_filename, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None) # Skip header
            for row in reader:
                if len(row) >= 3:
                    year = row[0].strip()
                    bank = row[1].strip()
                    keyword = row[2].strip().lower() 
                    completed.add(f"{year}_{bank}_{keyword}")
    return completed

def run_manual_web_helper(banks_data, WEB_OUTPUT_FILE, KEYWORDS_DICT):
    """
    Interactive terminal helper to manually fill in missing Web Scraper data.
    Copies the exact Google search string to your clipboard and waits for input.
    """
    print(f"\n🙋 [MANUAL HELPER] Starting Interactive Web Scraper Fallback...\n")
    
    # 1. Load progress so we only prompt for missing data
    completed_searches = get_completed_searches(WEB_OUTPUT_FILE)
    file_exists = os.path.exists(WEB_OUTPUT_FILE)
    
    # 2. Open CSV in append mode so every entry saves instantly
    with open(WEB_OUTPUT_FILE, mode='a', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        
        # Write headers if file is completely new
        if not file_exists:
            writer.writerow(['Year', 'Bank', 'KeywordIndex', 'TotalResults'])

        # 3. Loop through the exact same 3D structure (Years -> Banks -> Keywords)
        for year in range(2025, 2014, -1):
            year_str = str(year)
            
            for bank_row in banks_data:
                bank_name = bank_row['Bank_Name'].strip()
                domain = bank_row['Domain'].strip()
                
                if not domain:
                    continue # Skip if the bank has no valid domain in the inventory

                for kw_index, kw_list in KEYWORDS_DICT.items():
                    search_id = f"{year_str}_{bank_name}_{kw_index.lower()}"
                    
                    # Skip if we already have a number for this exact combo
                    if search_id in completed_searches:
                        continue
                        
                    # Build the OR query string
                    or_query = "(" + " OR ".join([f'"{kw}"' for kw in kw_list]) + ")"
                    
                    # Build the exact Google Search text with the date operators
                    search_text = f"site:{domain} {or_query} after:{year_str}-01-01 before:{year_str}-12-31"
                    
                    # Push to the operating system's clipboard
                    pyperclip.copy(search_text)
                    
                    # Prompt the user in the terminal
                    print(f"📋 Copied to clipboard: {search_text}")
                    print(f"🏦 Bank: {bank_name} | 🔑 Keyword: {kw_index} | 📅 Year: {year_str}")
                    
                    # Wait for a valid input
                    while True:
                        user_input = input("👉 Enter total results (or 's' to skip, 'q' to quit): ").strip().lower()
                        
                        if user_input == 'q':
                            print("\n🛑 Exiting Manual Helper. All previous entries are safely saved.")
                            return
                        elif user_input == 's':
                            print("   ⏭️ Skipped.\n")
                            break
                        elif user_input.isdigit():
                            # Save the valid number immediately to the hard drive
                            writer.writerow([year_str, bank_name, kw_index, user_input])
                            csv_file.flush()
                            
                            # Add to our memory set so we don't duplicate it if the script restarts
                            completed_searches.add(search_id)
                            print("   ✅ Saved!\n")
                            break
                        else:
                            print("   ⚠️ Invalid input. Please enter a whole number, 's', or 'q'.")

    print("\n🎉 Excellent work! All missing data points have been filled!")