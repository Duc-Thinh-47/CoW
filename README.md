# Collect and Weight - CoW

**Collect and Weight (CoW)** is an automated data pipeline designed to collect unstructured financial data and apply the entropy weighting method to construct a robust Fintech Index. By scraping bank websites and parsing financial reports, CoW quantifies qualitative text into measurable data points for index calculation.

## Architecture & Execution Pipeline

![Execution Pipeline](assets/execution_pipeline.png)

### How It Works

The system is built on a modular architecture, coordinated by a central script:

* **`main.py`**: Serves as the primary connector and control center. It routes the incoming data sources to the appropriate processing engines to ensure nothing gets bottlenecked.
    1. **Reading Inventory:** It reads the master `bank_inventory.csv` (PDF paths, domains) and `keyword_inventory.csv`.

    2. **Orchestrating Iteration:** It coordinates iterative looping over the banks.

    3. **State Management & Resume Logic:** For web scraping, it performs a resume check against `fintech_index_web_results.csv`. If a bank+keyword combination is already completed, it skips the call, preserving API credits.

    4. **Data Transformation:** Once worker loops are complete, it merges the distinct PDF and Web counts from their respective CSVs and pivots the data from long-format into the necessary wide-format matrix ( numpy array) for the entropy module.

* **Data Extraction (PDF & Web)**: When `main.py` needs data for a specific bank and keyword, it calls a specialized worker module, passing only the necessary task details:

    1. Module `web_scrape.py`: This module uses SerpApi (via requests) to perform targeted search result counts (site:domain "keyword"). It is designed to be case-insensitive, efficient, and stateless. It returns a single total result number or an error.

    2. Module `pdf_parse.py`: This module processes specified PDF files (e.g., Annual Reports) associated with a bank. It extracts unstructured text, counts all keyword frequencies, and returns the aggregated counts to main.py.

* **Intermediate Results Storage:** Intermediate results from the workers are written iteratively to disk as structured CSV files: `fintech_index_pdf_results.csv`, `fintech_index_web_results.csv` (used for state/resume logic)

* **`entropy.py`:** Finally, the standardized, wide-format matrix is fed into the sequential post-processing and mathematical engine. It executes three refined functions:

    1. `proportion_normalization`: Standardizes raw data using sum normalization.

    2. `calculate_entropy_weights`: Determines the entropy value (E) and subsequent weight (W) for each objective data point.

    3. `calculate_final_scores`: Multiplies weights by normalized values to generate final index scores for each bank.

* **Index Construction:** The pipeline culminates in the ranked index of banks, from highest score to lowest, outputting to `fintech_index_final_scores.csv`

## Installation

This project uses Git for version control and requires a Python virtual environment to manage its dependencies safely. 

**1. Clone the repository**
```bash
git clone https://github.com/Duc-Thinh-47/CoW.git
cd ./CoW/
```

**2. Activate virtual environment**
```bash
venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up environment variables**
```
# In .env file, write 
SERPAPI_KEY=YOUR_SERPAPI_KEY
```