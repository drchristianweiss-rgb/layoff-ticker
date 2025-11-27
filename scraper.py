import tweepy
import json
import re
import os
from datetime import datetime

# --- CONFIGURATION ---
# We retrieve these from Environment Variables (set in GitHub Secrets)
BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN")
TARGET_USER = "E_Boeminghaus"

def get_twitter_client():
    if not BEARER_TOKEN:
        raise ValueError("Bearer Token not found in environment variables.")
    return tweepy.Client(bearer_token=BEARER_TOKEN)

def parse_tweet(text):
    """
    Analyzes text to find a company name and a number.
    Style: Brutalist/Simple.
    """
    # 1. Extract Number
    # Looks for numbers like 1.000, 500, 10,000
    number_pattern = r'(\d{1,3}(?:[.,]\d{3})*|\d+)'
    
    # Keyword filter: Ensure it's about layoffs
    keywords = ['stellen', 'abbau', 'entlassung', 'kündigung', 'jobs', 'streichen']
    if not any(k in text.lower() for k in keywords):
        return None, 0

    match = re.search(number_pattern, text)
    count = 0
    if match:
        num_str = match.group(1).replace('.', '').replace(',', '')
        if num_str.isdigit():
            count = int(num_str)

    # 2. Extract Company (Heuristic)
    # We assume the company is often the first word or capitalized words at start
    words = text.split()
    company = "Unbekannt"
    
    # Basic cleanup to remove hashtags or common start words
    clean_words = [w for w in words if not w.startswith('#') and w.lower() not in ['bei', 'der', 'die', 'das']]
    if clean_words:
        company = clean_words[0].replace(':', '').replace(',', '')

    return company, count

def main():
    print(f"--- Starting Scraper for {TARGET_USER} ---")
    
    try:
        client = get_twitter_client()
        
        # 1. Get User ID
        user = client.get_user(username=TARGET_USER)
        if not user.data:
            print("User not found.")
            return
        user_id = user.data.id

        # 2. Get Tweets (Last 20)
        # tweet_fields=['created_at'] allows us to get the date
        response = client.get_users_tweets(user_id, max_results=20, tweet_fields=['created_at'])
        
        if not response.data:
            print("No tweets found.")
            return

        new_entries = []
        
        # 3. Load existing data
        file_path = 'data/layoffs.json'
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_ids = {entry['id'] for entry in existing_data}
        else:
            existing_data = []
            existing_ids = set()

        # 4. Process Tweets
        for tweet in response.data:
            t_id = str(tweet.id)
            
            if t_id in existing_ids:
                continue

            text = tweet.text
            company, count = parse_tweet(text)

            if count > 0:
                print(f"Found: {company} - {count}")
                entry = {
                    "id": t_id,
                    "date": tweet.created_at.strftime("%Y-%m-%d"),
                    "company": company,
                    "count": count,
                    "text": text,
                    "link": f"https://twitter.com/{TARGET_USER}/status/{t_id}"
                }
                new_entries.append(entry)

        # 5. Save
        if new_entries:
            all_data = new_entries + existing_data
            # Sort by Date descending
            all_data.sort(key=lambda x: x['date'], reverse=True)
            
            os.makedirs('data', exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=4, ensure_ascii=False)
            print(f"Saved {len(new_entries)} new entries.")
        else:
            print("No new relevant data found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
