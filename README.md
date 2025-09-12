# 📦 Project: GBI News Crawler → Gemini Enrichment → CSV (.csv)

## Step 1: Setup

1. Go into `.env` and fill in your Gemini API key.
2. 
 - run `setup_env.bat` to create and activate the conda environment. Just type `setup_env.bat` in the terminal and enter.
 - type in `conda activate myenv` to activate the environment.
OR
2. 
 - Activate the environment using conda
 - `conda activate myenv`
 - `conda install pip`
 - `pip install -r requirements.txt`

## Step 2: Run the Crawler

1. Make sure your environment is activated.
2. Run the crawler using these commands:

#### Run (run for 3 pages starting from homepage of https://news.gbimonthly.com/tw/article/index.php)
   ```
   python pipeline.py --max-pages 3 --csv data/articles.csv
   ```
#### Run (run for all the pages)
   ```
   python pipeline.py --all --csv data/articles.csv
   ```

### Notes
- CSV file will be saved to `data/articles.csv`
- DB is `data/news.db`. Unique key: `article_id` (from `?num=...`).

## (Optional) Step 3: If you want to delete a single article from csv and db

#### Delete Article using article_id
- `python manage.py delete --ids 80108`

#### Delete multiple articles using article_ids
- `python manage.py delete --ids 80098,80123,80555`

#### Delete from file
- `python manage.py delete --from-file ids_to_redo.txt`

#### Find files that are missing "keywords", "summary", etc.
- `python audit_failed_enrichment.py data/articles.csv ids_to_redo.txt`


### Explanation of Code
#### `config.py`
This file is to set the folder's path, the data folder location, crawling settings(news url, page to scans, etc) and LLM parameters (GEMINI_API_KEY, GEMINI_MODEL, timeouts). This is imported by other python file to use. 

TLDR: A file that stores global variables


#### `storage.py`
Handles the database(the things in the data folder that ends with .db) database:

init_db, get_conn manage the DB connection.
upsert_article, fetch_all_df, delete_article(s) will allow use to create, read, update, and delete each row we collect(each data we collected and organized).

_list_json_to_str cleans JSON fields for CSV export.
Used by pipeline.py to store results and by manage.py/audit_failed_enrichment.py when exporting or cleaning data.


#### `crawler.py`
Crawls index pages and extracts correct article URLs (crawl_links). Supplies URLs for parsing in pipeline.py.


#### `parser.py`
Gets individual article pages and extracts structured fields (headline, publish_date, body) using BeautifulSoup. Used by pipeline.py after the crawling step.


#### `prompts.py`
Defines the system prompt, JSON description, and user prompt template for the Gemini LLM. Imported by enrich.py to ensure consistent instructions to the model.

#### `enrich.py`
Provides GeminiEnricher, which calls the Gemini API (via google.genai; basically just like feeding in stuff to AI such as GPT to get a response) to generate summaries, keywords, company info, etc. Includes retry logic when it fail to call and normalization of model output. Used by pipeline.py when enrichment is enabled.

#### `pipeline.py`
Full Workflow:
- initializes DB (storage.init_db)
- crawls URLs (crawler.crawl_links)
- parses articles and get headline, publish_date, body (parser.parse_article_page)
- enriches them using the prompts in prompts.py and call GeminiEnricher API to get the response from Gemini
- save into the DB and exports a CSV


#### `manage.py`
Administrative CLI for the article database. Let you delete articles by ID and re‑exporting the CSV snapshot (export_csv_atomic). Relies on storage.py and config.py. Useful for cleanup after auditing.

#### `audit_failed_enrichment.py`
Don't need to care about this. But basically it detect rows with missing information/enrichment (things that produce from AI: keywords, summary, ...) in the db/csv file.
Then remove it. 

#### `Module Connections Overview`
config.py ➜ provides shared constants to all other python file.

pipeline.py ➜ central pipeline calling crawler, parser, enrich, and storage.

prompts.py ➜ define prompts and feed to enrich.py for LLM interaction.

manage.py and audit_failed_enrichment.py ➜ post‑processing/maintenance utilities operating on the same DB/CSV produced by the pipeline.
