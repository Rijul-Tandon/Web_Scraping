import os
import time
import logging
import pandas as pd
from seleniumbase import SB
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import re

def extract_date(string):
    # Regular expression to match the date format (e.g., 01 Apr 2023)
    match = re.search(r'\d{2} \w{3} \d{4}', string)
    return match.group(0) if match else None


# Configure logging to show timestamps and error details.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def scrape_ronin_chain_token_transfers(csv_file_with_axie_id):
    try:
        df = pd.read_csv(csv_file_with_axie_id)
        axie_ids = df.iloc[:, 0].astype(str).tolist()  # Ensure Axie IDs are strings
        all_data = []

        with SB(uc=True, headless=False) as sb:
            for axie_id in axie_ids:
                try:
                    url = f"https://app.roninchain.com/token/0x32950db2a7164ae833121501c797d79e7b79d74c/{axie_id}?p=1&ps=25"
                    logging.info(f"Processing Axie ID: {axie_id}")
                    sb.open(url)

                    WebDriverWait(sb.driver, 30).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "ronin-table-tbody"))
                    )

                    sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0)  # Increased sleep

                    rows = sb.find_elements(By.CLASS_NAME, "ronin-table-row")
                    logging.info(f"Axie ID {axie_id}: Found {len(rows)} transaction rows.")

                    for row in rows:
                        try:
                            cells = row.find_elements(By.CLASS_NAME, "ronin-table-cell")
                            if len(cells) >= 1:
                                try:
                                    anchor = cells[0].find_element(By.TAG_NAME, "a")
                                    href = anchor.get_attribute("href").strip()
                                    tx_hash = href.split("/tx/")[-1] if "/tx/" in href else href

                                    all_data.append({
                                        'Axie ID': axie_id,
                                        'Tx Hash': tx_hash
                                    })
                                except NoSuchElementException:
                                    logging.warning(f"No anchor tag found in row for Axie ID {axie_id}")
                                    continue  # Skip this row
                                except Exception as anchor_ex:
                                    logging.error(f"Error processing anchor tag for Axie ID {axie_id}: {anchor_ex}", exc_info=True)
                                    continue
                        except Exception as row_ex:
                            logging.error(f"Error extracting row data for Axie ID {axie_id}: {row_ex}", exc_info=True)
                            continue
                except Exception as id_ex:
                    logging.error(f"Error processing Axie ID {axie_id}: {id_ex}", exc_info=True)
                    continue

        final_df = pd.DataFrame(all_data)
        return final_df

    except Exception as overall_ex:
        logging.error(f"Scraping failed: {overall_ex}", exc_info=True)
        return None

def extract_dates_from_csv(csv_filename):
    try:
        df = pd.read_csv(csv_filename)
        results = []
        base_url = "https://app.roninchain.com/tx/"

        with SB(uc=True, headless=False) as sb:
            for index, row in df.iterrows():
                try:
                    tx_hash = str(row['Tx Hash']).strip()
                    full_url = base_url + tx_hash
                    print(f"Processing URL: {full_url}")
                    sb.open(full_url)
                    
                    WebDriverWait(sb.driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.-mb-8"))
                    )
                    time.sleep(0)
                    
                    try:
                        date_div = sb.find_element(By.CSS_SELECTOR, "div.-mb-8")
                        date_text = date_div.text.strip()
                    except NoSuchElementException as inner_e:
                        print(f"Error finding date element for tx_hash {tx_hash}: {inner_e}")
                        date_text = "N/A"
                    except Exception as e:
                        logging.error(f"General error finding date element for tx_hash {tx_hash}: {e}", exc_info=True)
                        date_text = "N/A"
                    
                    results.append({
                        'Tx Hash': tx_hash,
                        'Date': extract_date(date_text),  # Ensure extract_date is defined elsewhere
                        'Axie_id': str(row['Axie ID']).strip()
                    })
                except Exception as row_ex:
                    logging.error(f"Error processing row {index} in CSV: {row_ex}", exc_info=True)
                    continue
        
        result_df = pd.DataFrame(results)
        if not result_df.empty:  # Only save if there's data
            result_df.to_csv("tx_dates.csv", mode='a', index=False, header=False)
            print("Data saved to tx_dates.csv")
        else:
            print("No data to save to tx_dates.csv")
    
    except FileNotFoundError as fnf_error:
        print(f"CSV file not found: {fnf_error}")
    except Exception as e:
        print(f"Operation failed: {e}")

# Usage example
for i in range(1, 3):
    try:
        df = scrape_ronin_chain_token_transfers(f"axie_ids_{i}.csv")
        if not df.empty:
            logging.info("Data extracted successfully:")
            print(df)
            df.to_csv(f"ronin_transfers{i}.csv", index=False)
            logging.info(f"Data saved to ronin_transfers{i}.csv")
        else:
            logging.info("No data found or extraction encountered errors!")
    except Exception as e:
        logging.error(f"Error in scraping iteration {i}: {e}", exc_info=True)

for i in range(1, 3):
    try:
        # Check if the file exists before attempting to process it
        if os.path.exists(f"ronin_transfers{i}.csv"):
            extract_dates_from_csv(f"ronin_transfers{i}.csv")
        else:
            logging.warning(f"File ronin_transfers{i}.csv not found, skipping date extraction.")
    except Exception as e:
        logging.error(f"Error in extracting dates for iteration {i}: {e}", exc_info=True)
