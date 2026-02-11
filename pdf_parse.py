import re
import unicodedata
from collections import Counter
from pypdf import PdfReader
import os

def extract_text_from_pdf(file_path):
    """
    Opens a PDF file and extracts all text from it.
    
    Args:
        file_path (str): Path to the PDF file.
        
    Returns:
        str: The full text content of the PDF. 
             Returns an empty string if extraction fails or PDF is scanned image.
    """
    text_content = []
    
    try:
        reader = PdfReader(file_path)
        
        # Check if encrypted
        if reader.is_encrypted:
            # If you have a password, you can add: reader.decrypt('password')
            print(f"Warning: {file_path} is encrypted. Skipping.")
            return ""

        total_pages = len(reader.pages)
        print(f"Processing '{os.path.basename(file_path)}' ({total_pages} pages)...")

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                # 1. Normalize Unicode (Fixes Ligatures)
                # This splits 'ﬁ' (one char) into 'f' and 'i' (two chars)
                # NFKD form decomposes characters into their base components
                page_text = unicodedata.normalize('NFKD', page_text)

                # 2. Fix Hyphenation at Line Breaks
                # Regex: Find a hyphen followed immediately by a newline (and optional whitespace)
                # Replace it with nothing (joining the word)
                # Example: "strat- \n egy" becomes "strategy"
                page_text = re.sub(r'-\s*\n\s*', '', page_text)
                text_content.append(page_text)
            else:
                # This often happens with scanned images inside PDFs
                pass
                
        full_text = " ".join(text_content)
        
        # Simple check for scanned PDFs (image-only)
        if len(full_text.strip()) == 0 and total_pages > 0:
            print("Warning: No text extracted. This might be a scanned image PDF (OCR required).")
            
        return full_text

    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""

def clean_and_count_keywords(text, keywords):
    """
    Normalizes text and counts occurrences of specific keywords.
    
    Args:
        text (str): The raw text to analyze.
        keywords (list): A list of keywords to search for.
        
    Returns:
        dict: Dictionary mapping keywords to their counts (e.g., {'revenue': 12})
    """
    if not text:
        return {k: 0 for k in keywords}
    
    # 1. Normalize text: Lowercase everything
    text = text.lower()
    
    # 2. Tokenize: Replace non-alphanumeric chars with spaces, then split
    # This ensures "profit." or "profit," is counted as "profit"
    # \w+ matches alphanumeric characters (including underscores)
    words = re.findall(r'\b\w+\b', text)
    
    # 3. Create a frequency map of all words in the text
    word_counts = Counter(words)
    
    # 4. Extract counts for our specific keywords
    results = {}
    for k in keywords:
        # Normalize keyword to lowercase for matching
        clean_k = k.lower().strip()
        results[k] = word_counts.get(clean_k, 0)
        
    return results

def process_pdf(file_path, keywords):
    """
    Wrapper function to extract and count in one step.
    This is likely the function you will call from your main scraper.
    """
    raw_text = extract_text_from_pdf(file_path)
    counts = clean_and_count_keywords(raw_text, keywords)
    return counts

def debug_missing_words(file_path, keyword):
    """
    Scans a PDF using pypdf and prints the context around every match found.
    Use this to identify which specific instances are being missed.
    """
    # --- usage ---
    # Replace with your actual file path
    # debug_missing_words("your_annual_report.pdf", "growth")
    keyword = keyword.lower()
    total_found = 0
    
    print(f"--- Debugging matches for '{keyword}' using pypdf ---")
    
    try:
        reader = PdfReader(file_path)
        
        for i, page in enumerate(reader.pages):
            # Extract text
            text = page.extract_text()
            if not text:
                continue
                
            # Normalize to lower case for searching
            text_lower = text.lower()
            
            # Find all matches (using word boundaries \b to match exact words)
            # re.finditer gives us the position (index) of every match
            matches = list(re.finditer(r'\b' + re.escape(keyword) + r'\b', text_lower))
            
            if matches:
                print(f"\nPage {i+1}: Found {len(matches)} times")
                
                for match in matches:
                    start_index = match.start()
                    end_index = match.end()
                    
                    # Grab 40 characters before and after the match for context
                    # max/min ensures we don't crash if match is at start/end of page
                    context_start = max(0, start_index - 40)
                    context_end = min(len(text), end_index + 40)
                    
                    # Extract the snippet from the ORIGINAL text (preserves case/format)
                    snippet = text[context_start:context_end]
                    
                    # Clean up newlines/tabs in the snippet for cleaner printing
                    clean_snippet = snippet.replace('\n', ' ').replace('\r', ' ')
                    
                    print(f"   Context: ...{clean_snippet}...")
                
                total_found += len(matches)
                
    except Exception as e:
        print(f"Error reading PDF: {e}")

    print(f"\nTotal '{keyword}' found by pypdf: {total_found}")

# --- Test Block (Runs only if you execute this file directly) ---
if __name__ == "__main__":
    # Create a dummy PDF for testing if one doesn't exist
    # (Or replace 'sample.pdf' with a real path on your machine)
    test_file = "C:/Users/Tim/Downloads/20250421_vcb_250421_annual_report_2024.pdf"
    test_keywords = ["revenue", "growth", "risk", "esg", "2024"]
    
    '''
    if os.path.exists(test_file):
        print(f"--- Testing extraction on {test_file} ---")
        final_counts = process_pdf(test_file, test_keywords)
        
        print("\nResults:")
        for k, v in final_counts.items():
            print(f"  {k}: {v}")
    else:
        print(f"File {test_file} not found. Please place a PDF in this folder to test.")
    '''
    
    debug_missing_words(test_file, "growth")