import os
import csv
import pyperclip
from playwright.sync_api import sync_playwright

def get_completed_searches(csv_filename):
    """Reads the CSV to find which Year+Bank+Keyword combos are already done."""
    completed = set()
    if os.path.exists(csv_filename):
        with open(csv_filename, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) >= 3:
                    year = row[0].strip()
                    bank = row[1].strip()
                    keyword = row[2].strip().lower()
                    completed.add(f"{year}_{bank}_{keyword}")
    return completed

def load_keywords(keyword_file):
    """Load keywords from CSV into dict."""
    keywords_dict = {}
    with open(keyword_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            kw_index = row['KeywordIndex']
            kw = row['Keyword']
            if kw_index not in keywords_dict:
                keywords_dict[kw_index] = []
            keywords_dict[kw_index].append(kw)
    return keywords_dict

def load_banks(inventory_file):
    """Load banks from CSV."""
    banks_data = []
    with open(inventory_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            banks_data.append(row)
    return banks_data

def extract_result_count(page):
    """Extract total results count from PSE results page."""
    try:
        # Wait for results info
        results_locator = page.locator('.gsc-result-info')
        results_text = results_locator.text_content(timeout=10000)
        # Parse number, e.g., "About 1,234 results"
        import re
        match = re.search(r'(\d+(?:,\d+)*)', results_text)
        if match:
            return int(match.group(1).replace(',', ''))
        else:
            return 0
    except Exception as e:
        print(f"Error extracting results: {e}")
        return 0

def automate_pse(KEYWORD_INVENTORY_FILE, INVENTORY_FILE, WEB_OUTPUT_FILE, PSE_URL):
    print("🚀 Starting PSE Automation with Playwright...\n")

    # Load data
    KEYWORDS_DICT = load_keywords(KEYWORD_INVENTORY_FILE)
    banks_data = load_banks(INVENTORY_FILE)
    completed_searches = get_completed_searches(WEB_OUTPUT_FILE)
    file_exists = os.path.exists(WEB_OUTPUT_FILE)

    # Open CSV for appending
    with open(WEB_OUTPUT_FILE, mode='a', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)

        # Write header if new file
        if not file_exists:
            writer.writerow(['Year', 'Bank', 'KeywordIndex', 'TotalResults'])

        # Playwright setup
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # Set to True for headless

            # Main loop
            for year in range(2025, 2014, -1):
                year_str = str(year)

                for bank_row in banks_data:
                    bank_name = bank_row['Bank_Name'].strip()
                    domain = bank_row['Domain'].strip()

                    if not domain:
                        continue

                    for kw_index, kw_list in KEYWORDS_DICT.items():
                        search_id = f"{year_str}_{bank_name}_{kw_index.lower()}"

                        if search_id in completed_searches:
                            continue

                        # Build query
                        or_query = "(" + " OR ".join([f'"{kw}"' for kw in kw_list]) + ")"
                        search_text = f"site:{domain} {or_query} after:{year_str}-01-01 before:{year_str}-12-31"

                        # Copy to clipboard
                        pyperclip.copy(search_text)
                        print(f"📋 Copied to clipboard: {search_text}")

                        # New page for each query
                        page = browser.new_page()
                        page.goto(PSE_URL)

                        # Handle consent if present
                        try:
                            page.locator('button:has-text("Accept")').click(timeout=2000)
                        except:
                            pass

                        # Wait for search box (robust selector)
                        search_box = page.locator('input.gsc-input[name="search"], input#gsc-i-id1')
                        search_box.wait_for(state='visible', timeout=10000)
                        search_box.click()

                        # Paste from clipboard
                        page.keyboard.press('Control+v')

                        # Submit
                        page.keyboard.press('Enter')

                        # Wait for results
                        page.wait_for_load_state('networkidle', timeout=15000)

                        # Extract count
                        count = extract_result_count(page)
                        print(f"✅ Results: {count}")

                        # Write to CSV
                        writer.writerow([year_str, bank_name, kw_index, count])
                        csv_file.flush()

                        # Update completed
                        completed_searches.add(search_id)

                        # Close page
                        page.close()

            browser.close()

    print("\n🎉 PSE Automation Complete! Results saved to fintech_index_web_results.csv")

if __name__ == "__main__":
    main()