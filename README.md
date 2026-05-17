# Pinterest Pro Bulk System (Enterprise Version)

This system is designed for high-volume Pinterest scraping with full automation and folder-based organization.

## Folder Structure
- **`1_URL_Collector/`**: For collecting Pin URLs from profiles.
  - `profiles.txt`: Add your Pinterest profile URLs here (one per line).
  - `collected_urls/`: Where the URL CSVs will be saved.
- **`2_Data_Extractor/`**: For extracting detailed data from Pin URLs.
  - `inputs/`: Put your URL CSV files here.
  - `outputs/`: Where the final detailed data CSVs will be saved.

## How to use on Local Computer
1. Install dependencies: `pip install playwright && playwright install chromium`
2. **Step 1**: Add profiles to `1_URL_Collector/profiles.txt`. Run `python 1_URL_Collector/bulk_collector.py`.
3. **Step 2**: Copy CSVs from `collected_urls` to `2_Data_Extractor/inputs`.
4. **Step 3**: Run `python 2_Data_Extractor/bulk_extractor.py`.

## How to use on GitHub
1. Create a **Private** repository and upload all files.
2. Go to **Actions** -> **Pinterest Pro Bulk System**.
3. Click **Run workflow**.
4. **Select Mode**:
   - `collect_urls`: Only scrapes profiles from `profiles.txt`.
   - `extract_data`: Only scrapes data from CSVs in `inputs/`.
   - `both`: Runs collector first, then immediately extracts data from those URLs.

## Features
- **Bulk Processing**: Handles multiple profiles and multiple CSV files at once.
- **Resume System**: Automatically skips URLs that are already in the `outputs` folder.
- **GitHub Interactive**: Choose what to run directly from the GitHub interface.
- **Auto-Sync**: In `both` mode, URLs collected are automatically passed to the extractor.
