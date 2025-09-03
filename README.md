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
