import re
import unicodedata
import pdfplumber
from collections import Counter
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

    print(f"Processing '{os.path.basename(file_path)}' with pdfplumber...")

    try:
        # pdfplumber.open() is the context manager (like open())
        with pdfplumber.open(file_path) as pdf:
            
            # Check if encrypted (pdfplumber wraps pypdf, so this might raise an error directly)
            # usually handled by passing password to open() if known.
            
            total_pages = len(pdf.pages)
            
            for i, page in enumerate(pdf.pages):
                # --- THE MAGIC HAPPENS HERE ---
                # x_tolerance=2: If two chars are < 2px apart, they are one word.
                #                If they are > 2px, insert a space. 
                #                This FIXES your "RevenueGrowth" -> "Revenue Growth" issue.
                # y_tolerance=3: Groups lines that are close together.
                # layout=True forces a complex analysis of rows/cols
                # dedupe=True attempts to remove overlapping chars (Shadow Text)
                raw_text = page.extract_text(layout=True, dedupe=True, x_tolerance=2, y_tolerance=3)
                
                if raw_text:
                    # 1. Normalize Unicode (Fixes Ligatures like 'ﬁ' -> 'fi')
                    # NFKD decomposes characters into base components
                    norm_text = unicodedata.normalize('NFKD', raw_text)

                    # 2. Fix Hyphenation at Line Breaks
                    # "strat- \n egy" -> "strategy"
                    # We use strict regex to avoid merging "Strategy - Execution"
                    clean_text = re.sub(r'-\s*\n\s*', '', norm_text)
                    
                    text_content.append(clean_text)
                else:
                    # Page exists but no text found (likely image/scanned)
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
    # \b\w+\b would match whole words (star to end), but it can miss words with apostrophes or hyphens.
    #words = re.findall(r'\b\w+\b', text)

    # 3. Create a frequency map of all words in the text
    #word_counts = Counter(words)
    
    # 4. Extract counts for our specific keywords
    # Currently, this is matching substrings, meaning "growth" will match "growth" and "growths". 
    # If want exact matches, use word_counts directly.
    results = {}
    for k in keywords:
        # Normalize keyword to lowercase for matching
        clean_k = k.lower().strip()
        
        # Un-comment the line below if you want to count exact matches only (not substrings)
        #results[k] = word_counts.get(clean_k, 0)

        if clean_k: 
            results[k] = text.count(clean_k)
        else: 
            results[k] = 0
        
    return results

def process_pdf(file_path, keywords):
    """
    Wrapper function to extract and count in one step.
    This is likely the function you will call from your main scraper.
    """
    raw_text = extract_text_from_pdf(file_path)
    counts = clean_and_count_keywords(raw_text, keywords)
    return counts