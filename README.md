# Collect and Weight - CoW

**Collect and Weight (CoW)** is an automated data pipeline designed to collect unstructured financial data and apply the entropy weighting method to construct a robust Fintech Index. By scraping bank websites and parsing financial reports, CoW quantifies qualitative text into measurable data points for index calculation.

## Architecture & Execution Pipeline

![Execution Pipeline](assets/execution_pipeline.png)

## How It Works

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

## How to Use

Currently, the data preparation phase requires a few manual steps before the pipeline can take over and do the heavy lifting.

### 1. Configure Your Inventories
You need to tell the pipeline what to look for and where to look. 
* **`data/keyword_inventory.csv`**: Add your master list of Fintech keywords (e.g., Blockchain, AI, Mobile Banking).
* **`data/bank_inventory.csv`**: Add your target banks. You must include the bank's name, their primary domain (for the web scraper), and the exact filenames of their PDF reports. If a bank has multiple PDFs, separate the filenames with a pipe (`|`).

### 2. Prepare the PDF Data
* Manually download the Annual Reports (or other financial PDFs) for the banks you want to analyze.
* Place these PDF files into your data folder. 
* *(Note: If you are running the testing configuration, place these in `data/test_pdfs/`. Ensure the folder structure matches the path defined in your `main.py` script.)*

### 3. Set Up Your Environment
The web scraper module requires a SerpApi key. Create a file named `.env` in the root directory of the project and add your key:
```env
SERPAPI_KEY=your_actual_api_key_here
```

### 4. Execute the Pipeline
Once your inventories, PDFs, and API key are in place, run the main script:
```bash
python main.py
```

### 5. Review the Results
The script will print its progress and output intermediate results to the `data/` folder so it can resume if interrupted. Once all modules finish, it will generate `data/fintech_index_final_scores.csv`, containing your fully weighted and ranked Fintech Index.

## Mathematics details: Entropy Weight Method (EWM)

CoW uses the **Entropy Weight Method (EWM)** to objectively calculate the Fintech Index. Unlike subjective scoring systems where a human guesses which keywords are most important, EWM lets the data decide. It is rooted in Information Theory: if every bank mentions a keyword equally, that keyword provides zero differentiating information and gets a low weight. If only one bank dominates a keyword, it provides high information and gets a heavy weight.

The mathematical pipeline executes in three strict steps:

### 1. Proportion Normalization
Before calculating entropy, the raw count matrix (Banks as rows, Keywords as columns) must be normalized. We use **Proportion Normalization** along the **columns** (`axis=0`).

$$p_{ij} = \frac{x_{ij}}{\sum_{i=1}^{n} x_{ij}}$$

**Why Proportion Normalization?**
The entropy formula requires a true probability distribution where all values are between 0 and 1, and the total sum is exactly 1. 
* We cannot use **Min-Max scaling** because it forces the lowest value to `0`. The entropy formula requires taking the natural log ($\ln(p_{ij})$), and $\ln(0)$ is mathematically undefined and would crash the pipeline.
* We cannot use **Z-Score standardization** because it creates negative numbers, and you cannot take the natural log of a negative number.

**Why Normalize Columns (`axis=0`)?**
We are calculating weights for the *keywords*, not the banks. Normalizing down a column isolates a single keyword (e.g., "Blockchain"). The column sum represents the total universe of "Blockchain" mentions. Dividing a single bank's mentions by this sum answers: *"What market share of the 'Blockchain' conversation does this specific bank own?"* 

### 2. Calculating Information Entropy ($E_j$)
Once we have our probabilities, we calculate the entropy for each keyword column:

$$E_j = -k \sum_{i=1}^{n} p_{ij} \ln(p_{ij})$$

*(Note: $k$ is a constant defined as $\frac{1}{\ln(n)}$, where $n$ is the number of banks, ensuring the entropy value stays between 0 and 1).*

### 3. Calculating Final Objective Weights ($w_j$)
Finally, we convert the entropy of each keyword into its final weight. First, we calculate the degree of divergence ($d_j = 1 - E_j$), and then divide it by the sum of all divergences:

$$w_j = \frac{1 - E_j}{\sum_{j=1}^{m} (1 - E_j)}$$

The resulting weights ($w_j$) will always sum to exactly 1. These objective weights are then multiplied against the normalized matrix to produce the final, ranked Fintech Index score for each bank.

### 4. Calculating the Final Fintech Index Score
Finally, we generate the actual Fintech Index score for each bank. We take the normalized proportion matrix ($p_{ij}$) and multiply each column by its corresponding calculated weight ($w_j$), then sum the results across the row for each bank ($i$):

$$Score_i = \sum_{j=1}^{m} p_{ij} \cdot w_j$$

**What this means:** A bank's final score is the sum of its "market share" for every keyword, scaled strictly by how objectively important (heavily weighted) each keyword is. The script then ranks the banks from highest score to lowest, outputting the definitive Fintech Index.