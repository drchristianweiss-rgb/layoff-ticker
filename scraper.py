import json
import re
import time
from datetime import datetime
from ntscraper import Nitter

# CONFIGURATION
TARGET_USER = "E_Boeminghaus"
START_DATE = datetime(2025, 1, 1)

def get_layoff_data(text):
    """
    Parses text for company and number.
    """
    # 1. Clean number (remove points like 1.000)
    # This regex looks for numbers like 100, 1.000, 10,000
    number_pattern = r'(\d{1,3}(?:[.,]\d{3})*|\d+)'
    
    keywords = ['stellen', 'abbau', 'entlassung', 'kündigung', 'jobs', 'streichen', 'wegfallen']
    
    # Must contain a keyword
    if not any(k in text.lower() for k in keywords):
        return None, 0

    match = re.search(number_pattern, text)
    count = 0
    if match:
        num_str = match.group(1).replace('.', '').replace(',', '')
        if num_str.isdigit():
            count = int(num_str)

    # Heuristic for Company Name (First word that isn't a stopword)
    words = text.split()
    company = "Unbekannt"
    stop_words = ['bei', 'der', 'die', 'das', 'in', 'von', 'nach', 'mehr', 'rund', 'knapp', 'etwa']
    
    for w in words:
        clean_w = w.strip('.,:;!?')
        if clean_w.lower() not in stop_words and not clean_w.startswith('#') and len(clean_w) > 2:
            company = clean_w
            break

    return company, count

def main():
    print(f"--- Scraping {TARGET_USER} since {START_DATE.strftime('%Y-%m-%d')} ---")
    scraper = Nitter(log_level=1, skip_instance_check=False)

    try:
        # We fetch a large number (500) to ensure we go back to Jan 1st
        # Nitter is slow, so this might take a minute.
        tweets = scraper.get_tweets(TARGET_USER, mode='user', number=500)
    except Exception as e:
        print(f"Scraping failed: {e}")
        return

    final_data = []
    
    for tweet in tweets.get('tweets', []):
        try:
            # Parse Date from Nitter format "Jan 1, 2025 · 10:00 AM UTC"
            # Format depends on the Nitter instance, usually "MMM D, YYYY"
            raw_date = tweet['date']
            # Simplistic date parser, might need adjustment based on instance
            # This handles the common Nitter format
            date_str = raw_date.replace(',', '').split('·')[0].strip() 
            try:
                dt_obj = datetime.strptime(date_str, "%b %d %Y")
            except:
                # Fallback for different formats
                continue

            # Check if older than Jan 1, 2025
            if dt_obj < START_DATE:
                continue

            text = tweet['text']
            company, count = get_layoff_data(text)

            if count > 0:
                print(f"Found: {company} ({count}) on {dt_obj.date()}")
                entry = {
                    "id": tweet['link'], # Use link as ID
                    "date": dt_obj.strftime("%Y-%m-%d"),
                    "company": company,
                    "count": count,
                    "text": text,
                    "link": tweet['link']
                }
                final_data.append(entry)
                
        except Exception as parse_error:
            continue

    # Sort by date descending
    final_data.sort(key=lambda x: x['date'], reverse=True)

    # Save to file
    with open('data/layoffs.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)
    
    print(f"Successfully saved {len(final_data)} entries.")

if __name__ == "__main__":
    main()
