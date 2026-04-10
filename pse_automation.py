import os
import csv
import pyperclip
import random
import time
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
        # Check for CAPTCHA with improved selectors
        captcha_selectors = [
            'text=/are you a robot/i',
            'text=/i am not a robot/i',
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]',
            '.captcha',
            '#captcha',
            'text=/systems have detected unusual traffic/i',
            'text=/please try your request again later/i',
            'text=/ip address/i',
            'text=/tôi không phải là người máy/i'
        ]
        for selector in captcha_selectors:
            if page.locator(selector).count() > 0:
                raise Exception("CAPTCHA detected")

        # Try to locate and parse results info
        results_locator = page.locator('.gsc-result-info')
        if results_locator.count() > 0:
            results_text = results_locator.text_content(timeout=10000)
            # Parse number, e.g., "About 1,234 results"
            import re
            match = re.search(r'(\d+(?:,\d+)*)', results_text)
            if match:
                return int(match.group(1).replace(',', ''))

        # Check for "no results" message using locator
        no_results_text = "Nội dung tìm kiếm của bạn không khớp với bất kỳ kết quả nào"
        no_results_locator = page.locator('.gs-snippet').filter(has_text=no_results_text)
        if no_results_locator.count() > 0:
            return 0
        else:
            raise Exception("No valid result count found")
    except Exception as e:
        if "CAPTCHA" in str(e):
            raise e  # Re-raise CAPTCHA
        raise e


def wait_for_search_results(page, timeout=30000):
    """Wait until either search results or a no-results message appears."""
    no_results_text = "Nội dung tìm kiếm của bạn không khớp với bất kỳ kết quả nào"
    try:
        page.wait_for_selector('.gsc-result-info, .gs-snippet', timeout=timeout)
        if page.locator('.gsc-result-info').count() > 0:
            page.locator('.gsc-result-info').first.wait_for(state='visible', timeout=timeout)
            return

        no_results_locator = page.locator('.gs-snippet').filter(has_text=no_results_text)
        if no_results_locator.count() > 0:
            no_results_locator.first.wait_for(state='visible', timeout=timeout)
            return

        # If neither results info nor clear no-results text are present, wait a little longer for the count element.
        page.locator('.gsc-result-info').first.wait_for(state='visible', timeout=timeout)
    except Exception:
        raise Exception("Result content did not appear within timeout")


def automate_pse(KEYWORD_INVENTORY_FILE, INVENTORY_FILE, WEB_OUTPUT_FILE, PSE_URL, debug=False):
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

        failed_log_file = open("data/failed_searches.log", 'a', encoding='utf-8')

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

                        failure_reason = None
                        count = None
                        max_retries = 3
                        for attempt in range(max_retries):
                            try:
                                # New page for each query
                                page = browser.new_page()
                                page.goto(PSE_URL, wait_until='domcontentloaded', timeout=20000)

                                # Handle consent if present
                                try:
                                    page.locator('button:has-text("Accept")').click(timeout=2000)
                                except:
                                    pass

                                # Wait for search box (robust selector)
                                search_box = page.locator('input.gsc-input[name="search"], input#gsc-i-id1')
                                search_box.wait_for(state='visible', timeout=20000)
                                search_box.click()

                                # Paste from clipboard
                                page.keyboard.press('Control+v')

                                # Submit
                                page.keyboard.press('Enter')

                                # Wait for search results to render
                                wait_for_search_results(page, timeout=30000)

                                # Extract count
                                count = extract_result_count(page)
                                print(f"✅ Results: {count}")

                                if debug:
                                    user_input = input("Search completed. Press 'd' to continue in debug mode, 'n' to continue normally: ").strip().lower()
                                    if user_input == 'n':
                                        debug = False

                                # Close page
                                page.close()
                                break  # Success, exit retry loop

                            except Exception as e:
                                # Treat all errors (network, CAPTCHA, result extraction) as potential CAPTCHA
                                if attempt < max_retries - 1:
                                    # Apply escalating delays: 10s for attempts 0-1, 30s for attempt 2
                                    delay = 10 if attempt < 2 else 30
                                    print(f"⚠️  Error encountered: {e}")
                                    print(f"⏳ Retrying in {delay}s (attempt {attempt + 1}/3)...")
                                    time.sleep(delay)
                                    page.close()
                                else:
                                    # All retries exhausted - wait for manual intervention without closing page
                                    print(f"\n🚫 All automated retries exhausted. Error: {e}")
                                    print("Please manually resolve the issue (solve CAPTCHA, check network, etc.) in the browser window.")
                                    user_resolution = input("Press Enter after resolving the issue to continue...")
                                    
                                    # Try to extract count from the current page
                                    try:
                                        count = extract_result_count(page)
                                        print(f"✅ Results after manual intervention: {count}")
                                        page.close()
                                        break
                                    except Exception as retry_e:
                                        print(f"❌ Still unable to extract results after manual intervention: {retry_e}")
                                        print("Skipping this search.")
                                        failure_reason = "MANUAL_INTERVENTION_FAILED"
                                        count = 0
                                        page.close()
                                        break

                        if count is None:
                            count = 0  # Fallback

                        if failure_reason:
                            failed_log_file.write(f"{year_str},{bank_name},{kw_index},{failure_reason}\n")

                        # Write to CSV
                        writer.writerow([year_str, bank_name, kw_index, count])
                        csv_file.flush()

                        # Update completed
                        completed_searches.add(search_id)

                        # Random delay between searches (2-10 seconds)
                        delay = random.uniform(2, 10)
                        print(f"⏳ Waiting {delay:.1f}s before next search...")
                        time.sleep(delay)

            browser.close()

    failed_log_file.close()

    print("\n🎉 PSE Automation Complete! Results saved to fintech_index_web_results.csv")