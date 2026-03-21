# Collect and Weight - CoW

**Collect and Weight (CoW)** is an automated data pipeline designed to collect unstructured financial data and apply the entropy weighting method to construct a robust Fintech Index. By scraping bank websites and parsing financial reports, CoW quantifies qualitative text into measurable data points for index calculation.

## Architecture & Execution Pipeline

![Execution Pipeline](assets/execution_pipeline.png)

## How It Works

The system is built on a modular architecture, coordinated by a central script:

* **`main.py`**: Serves as the primary connector and control center. It routes the incoming data sources to the appropriate processing engines to ensure nothing gets bottlenecked.
    1. **Reading Inventory:** It reads the master `bank_inventory.csv` (PDF paths, domains) and `keyword_inventory.csv`.

    2. **Orchestrating Iteration:** It coordinates iterative looping over the banks and specifically iterates backward through 10 fiscal years (2025 to 2015) to build a time-series index.

    3. **State Management & Resume Logic:** For web scraping, it performs a resume check against `fintech_index_web_results.csv`. If a bank+keyword combination is already completed, it skips the call, preserving API credits.

    4. **Data Transformation:** Once worker loops are complete, it merges the distinct PDF and Web counts from their respective CSVs and pivots the data from long-format into the necessary wide-format matrix (numpy array) for the entropy module.

* **Data Extraction (PDF & Web)**: When `main.py` needs data for a specific bank, keyword, and year, it calls a specialized worker module, passing only the necessary task details:

    1. Module `web_scrape.py`: This module uses SerpApi (via requests) to perform targeted search result counts (site:domain "keyword"). It incorporates time-based search parameters (`tbs`) to filter results by specific years. It returns a single total result number or an error.

    2. Module `pdf_parse.py`: This module processes specified PDF files (e.g., Annual Reports) associated with a bank. It extracts unstructured text, counts all keyword frequencies, and returns the aggregated counts to `main.py`.

* **Interactive Fallback Module (`manual_helper.py`)**: A dedicated terminal-based helper to bypass financial constraints and scraping roadblocks.
    * **Why it exists:** Querying a decade of data across multiple keywords and banks requires hundreds of thousands of API calls, which is financially unviable. Furthermore, Google frequently obfuscates the true "Total Results" count behind pagination limits, DMCA blocks, and estimate features. 
    * **How it works:** This module acts as a bridge. It reads your current CSV progress, identifies missing data points, and automatically constructs the precise Google search query (including `after:YYYY-01-01 before:YYYY-12-31` time operators). It copies this directly to your operating system's clipboard using the `pyperclip` library and prompts you in the terminal. You simply paste the query into your browser, find the result, type it into the terminal, and the script instantly appends it to your CSV dataset.

* **Intermediate Results Storage:** Intermediate results from the workers are written iteratively to disk as structured CSV files: `fintech_index_pdf_results.csv`, `fintech_index_web_results.csv` (used for state/resume logic).

* **`entropy.py`:** Finally, the standardized, wide-format matrix is fed into the sequential post-processing and mathematical engine. It executes three refined functions:

    1. `proportion_normalization`: Standardizes raw data using sum normalization.

    2. `calculate_entropy_weights`: Determines the entropy value (E) and subsequent weight (W) for each objective data point.

    3. `calculate_final_scores`: Multiplies weights by normalized values to generate final index scores for each bank.

* **Index Construction:** The pipeline culminates in the ranked index of banks, year by year, outputting to `fintech_index_final_scores.csv`.

## Installation

This project uses Git for version control and requires a Python virtual environment to manage its dependencies safely. 

**1. Clone the repository**
``` bash   
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

## How to Use

Currently, the data preparation phase requires a few manual steps before the pipeline can take over and do the heavy lifting.

### 1. Configure Your Inventories
You need to tell the pipeline what to look for and where to look. 
* **`data/keyword_inventory.csv`**: Add your master list of Fintech keywords (e.g., Blockchain, AI, Mobile Banking).
* **`data/bank_inventory.csv`**: Add your target banks. You must include the bank's name, their primary domain (for the web scraper), and the exact filenames of their PDF reports. If a bank has multiple PDFs, separate the filenames with a pipe (`|`). Ensure your PDF filenames include the 4-digit year (e.g., `uob_2024.pdf`).

### 2. Prepare the PDF Data
* Manually download the Annual Reports (or other financial PDFs) for the banks you want to analyze.
* Place these PDF files into your `data/raw_pdfs/` folder. 

### 3. Set Up Your Environment
The web scraper module requires a SerpApi key. Create a file named `.env` in the root directory of the project and add your key:
    SERPAPI_KEY=your_actual_api_key_here

### 4. Execute the Pipeline
Inside `main.py`, there is a Master Command Center with boolean toggles (True/False). 
* Enable `RUN_PDF_MODULE` or `RUN_WEB_MODULE` to automate data collection.
* Enable `RUN_MANUAL_WEB_HELPER` to use the interactive terminal tool to fill in missing web data points. 
* Enable `RUN_INDEX_CALCULATION` when your datasets are complete to generate the final scores.

*NOTE: Keep in mind that the manual helper and the web module were designed to work seperately, if you plan on using the web module to automate part of the data collecttion and the manual helper to fill in the rest, do so at you own risk*


Run the main script:
```bash
python main.py
```

### 5. Review the Results
The script will print its progress and output intermediate results to the `data/` folder so it can resume if interrupted. Once all modules finish, it will generate `data/fintech_index_final_scores.csv`, containing your fully weighted and ranked Time-Series Fintech Index.

## Mathematics details: Entropy Weight Method (EWM)

CoW uses the **Entropy Weight Method (EWM)** to objectively calculate the Fintech Index. Unlike subjective scoring systems where a human guesses which keywords are most important, EWM lets the data decide. It is rooted in Information Theory: if every bank mentions a keyword equally, that keyword provides zero differentiating information and gets a low weight. If only one bank dominates a keyword, it provides high information and gets a heavy weight.

The mathematical pipeline executes in strict steps, including safeguards for computational edge cases:

### 1. Proportion Normalization
Before calculating entropy, the raw count matrix (Banks as rows, Keywords as columns) must be normalized. We use **Proportion Normalization** along the **columns** (`axis=0`).

$$p_{ij} = \frac{x_{ij}}{\sum_{i=1}^{n} x_{ij}}$$

**Why Proportion Normalization?**
The entropy formula requires a true probability distribution where all values are between 0 and 1, and the total sum is exactly 1. 

**Handling the Zero-Division Error:** If no banks mention a specific keyword in a given year, the column sum is $0$. Dividing by zero causes a fatal `ZeroDivisionError` (NaN) in Python. To bypass this, the code implements a safeguard: `sums[sums == 0] = 1`. This safely bypasses the error while keeping the normalized column values at $0$.

### 2. Calculating Information Entropy ($E_j$)
Once we have our probabilities, we calculate the entropy for each keyword column:

$$E_j = -k \sum_{i=1}^{n} p_{ij} \ln(p_{ij})$$

*(Note: $k$ is a constant defined as $\frac{1}{\ln(n)}$, where $n$ is the number of banks, ensuring the entropy value stays between 0 and 1).*

**Handling the Log of Zero Error:**
Because $\ln(0)$ is mathematically undefined, evaluating it crashes the pipeline with a `RuntimeWarning`. However, the limit $\lim_{p \to 0} p \ln(p) = 0$. We implement this mathematically sound workaround using NumPy: `np.where(P > 0, np.log(P), 0)`.

### 3. Calculating Final Objective Weights ($w_j$)
Finally, we convert the entropy of each keyword into its final weight. First, we calculate the degree of divergence ($d_j = 1 - E_j$), and then divide it by the sum of all divergences:

$$w_j = \frac{1 - E_j}{\sum_{j=1}^{m} (1 - E_j)}$$

The resulting weights ($w_j$) will always sum to exactly 1. 

### 4. Calculating the Final Fintech Index Score
Finally, we generate the actual Fintech Index score for each bank. We take the normalized proportion matrix ($p_{ij}$) and multiply each column by its corresponding calculated weight ($w_j$), then sum the results across the row for each bank ($i$):

$$Score_i = \sum_{j=1}^{m} p_{ij} \cdot w_j$$

**What this means:** A bank's final score is the sum of its "market share" for every keyword, scaled strictly by how objectively important (heavily weighted) each keyword is. The script then ranks the banks from highest score to lowest for that specific year, outputting the definitive Time-Series Fintech Index.