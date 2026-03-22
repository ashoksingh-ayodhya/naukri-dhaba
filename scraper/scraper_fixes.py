import requests
import time

class Scraper:
    def __init__(self, max_retries=3, backoff_factor=1):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def fetch_with_retries(self, url):
        retries = 0
        while retries < self.max_retries:
            try:
                response = requests.get(url)
                response.raise_for_status()  # Raise an error for bad responses
                return response.text
            except requests.RequestException as e:
                print(f"Attempt {retries + 1} failed: {e}")
                retries += 1
                time.sleep(self.backoff_factor * (2 ** (retries - 1)))  # Exponential backoff
        raise Exception(f"Failed to fetch {url} after {self.max_retries} retries")

# Example usage:
# scraper = Scraper()
# content = scraper.fetch_with_retries('http://example.com')
