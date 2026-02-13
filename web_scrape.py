import time
import random
from playwright.sync_api import sync_playwright
import trafilatura

def mimic_human_scroll(page):
    """
    Solves 'Lazy Loading' and 'Infinite Scroll'.
    Scrolls down the page in increments to trigger JS loading events.
    """
    last_height = page.evaluate("document.body.scrollHeight")
    
    while True:
        # Scroll down by a random amount to look human
        page.mouse.wheel(0, random.randint(500, 1000))
        page.wait_for_timeout(random.randint(500, 1500)) # Wait for content to load
        
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            # If height hasn't changed after scrolling, we reached the bottom
            break
        last_height = new_height
        
def get_clean_text_from_html(html_content):
    """
    Uses Trafilatura to extract ONLY the main text and tables.
    This removes 'noise' like generic footers/navbars that would
    inflate your keyword counts (e.g. 'Contact Us' on every page).
    """
    # include_tables=True is CRITICAL for financial data
    return trafilatura.extract(html_content, include_tables=True, include_comments=False)

def count_keywords_ctrl_f(text, keywords, debug=False, window=50):
    """
    Counts keywords using substring matching.
    
    Args:
        text (str): The content to search.
        keywords (list): List of terms to count.
        debug (bool): If True, prints the context around found words.
        window (int): Number of characters to show before/after match.
        
    Returns:
        dict: {keyword: count}
    """
    if not text:
        return {k: 0 for k in keywords}
    
    text_lower = text.lower()
    results = {}
    
    if debug:
        print(f"\n🔎 --- DEBUGGING CONTEXT ---")

    for k in keywords:
        k_lower = k.lower()
        
        # 1. Initialize count and search position
        count = 0
        start_index = 0
        
        # 2. Loop to find ALL occurrences (simulates .count() but keeps indices)
        while True:
            # Find next occurrence of the keyword
            idx = text_lower.find(k_lower, start_index)
            
            # If not found, stop looking for this keyword
            if idx == -1:
                break
            
            # Found one! Increment count
            count += 1
            
            # 3. If Debugging is ON, print the context immediately
            if debug:
                # Calculate start/end of the context window
                # max/min prevents crashing if we are at the very start/end of text
                left = max(0, idx - window)
                right = min(len(text), idx + len(k) + window)
                
                # Extract the snippet
                snippet = text[left:right]
                
                # Clean up newlines for cleaner printing
                clean_snippet = snippet.replace('\n', ' ').replace('\r', '')
                
                print(f"   ['{k}'] Found: \"...{clean_snippet}...\"")

            # Move start_index forward to find the NEXT one
            start_index = idx + 1
            
        results[k] = count

    if debug:
        print(f"---------------------------\n")

    return results

def universal_ctrl_f_scraper(url, keywords):
    print(f"🕵️‍♂️ Starting Universal Ctrl+F on: {url}")
    
    with sync_playwright() as p:
        # --- 1. ANTI-DETECTION SETUP ---
        # Launch browser with specific flags to hide automation
        browser = p.chromium.launch(headless=True)
        
        # Context mimics a real device (London, UK example)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='Asia/Ho_Chi_Minh'
        )
        
        page = context.new_page()
        
        # Block unnecessary resources to speed up loading (Images/Fonts)
        # We only need text!
        page.route("**/*.{png,jpg,jpeg,svg,css,woff,woff2}", lambda route: route.abort())
        
        try:
            # --- 2. NAVIGATION & ACCESS ---
            # 'domcontentloaded' is faster than 'networkidle'
            # We rely on our scroll logic to catch the rest.
            page.goto(url, wait_until='domcontentloaded', timeout=45000)
            
            # --- 3. DYNAMIC CONTENT HANDLING ---
            # Solve "Lazy Loading" by scrolling to the bottom
            print("   ↳ Scrolling to trigger lazy loads...")
            mimic_human_scroll(page)
            
            # --- 4. IFRAME HANDLING (Advanced) ---
            # Some banks put data inside iframes. We grab the main frame
            # AND any visible child frames.
            full_html = page.content()
            
            # (Optional) Iterate iframes if you suspect hidden data
            for frame in page.frames:
                try:
                    # Append iframe content to main content
                    full_html += "\n" + frame.content()
                except:
                    pass # Security cross-origin might block some, ignore.

            # --- 5. EXTRACTION & CLEANING ---
            page.screenshot(path=f"..\\Data\\Web\\{url.replace('https://', '').replace('/', '_')}_scroll.png", full_page=True)
            print("   ↳ Extracting and Cleaning text...")
            clean_text = get_clean_text_from_html(full_html)
            
            if not clean_text:
                print("   ❌ Warning: No readable text found.")
                return None

            # --- 6. COUNTING ---
            print("   ↳ Counting keywords...")
            counts = count_keywords_ctrl_f(clean_text, keywords, debug=True, window=20)
            
            # Metrics for your entropy analysis later
            return {
                "url": url,
                "status": "success",
                "keyword_counts": counts,
                "total_word_count": len(clean_text.split()),
                "extracted_text_sample": clean_text[:200] # For debugging
            }

        except Exception as e:
            print(f"   🔥 Critical Error: {e}")
            return {"url": url, "status": "failed", "error": str(e)}
        
        finally:
            browser.close()

# --- USAGE ---
target_urls = [
    #"https://www.jpmorganchase.com/",
    #"https://www.citi.com/"
    "https://www.bankofamerica.com/",
    # Add more URLs
]

search_terms = ["revenue", "growth", "risk", "sustainable", "esg", "profit", "bank"]

for url in target_urls:
    data = universal_ctrl_f_scraper(url, search_terms)
    if data and data["status"] == "success":
        print(f"   ✅ RESULT: {data['keyword_counts']}")
    else:
        print("   ❌ FAILED")