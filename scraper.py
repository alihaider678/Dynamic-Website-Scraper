# job_scraper/scraper.py

import time
from httpcore import TimeoutException
import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.selenium_setup import setup_selenium
from utils.logger_setup import setup_logger

def scrape_page(driver, url, logger):
    jobs = []
    try:
        logger.info(f"Scraping page: {url}")
        driver.get(url)

        # Wait until job cards are present
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'jobsearch-SerpJobCard'))
        )

        # Capture the page source for debugging
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        job_cards = soup.find_all('div', class_='jobsearch-SerpJobCard')

        if not job_cards:
            logger.error(f"No job cards found on page: {url}")
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            return jobs

        for job_card in job_cards:
            try:
                title = job_card.find('a', class_='jobtitle').text.strip()
                company = job_card.find('span', class_='company').text.strip()
                location = job_card.find('div', class_='location').text.strip() if job_card.find('div', class_='location') else 'N/A'
                
                # Check for 'DatePosted' and handle gracefully
                date_posted_element = job_card.find('span', class_='date')
                date_posted = date_posted_element.text.strip() if date_posted_element else 'Unknown'
                
                description = job_card.find('div', class_='summary').text.strip() if job_card.find('div', class_='summary') else 'N/A'

                logger.info(f"Scraped job: {title} at {company}, Date: {date_posted}")

                jobs.append({
                    'Title': title,
                    'Company': company,
                    'Location': location,
                    'DatePosted': date_posted,
                    'Description': description
                })

            except AttributeError as e:
                logger.warning(f"Failed to scrape job card: {e}")

    except Exception as e:
        logger.error(f"An error occurred while scraping {url}: {e}")
        # Save the page source for debugging purposes
        with open("debug_error.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

    return jobs

def paginate_and_scrape(driver, base_url, logger):
    jobs = []
    page_urls = [f"{base_url}&start={i}" for i in range(0, 30, 10)]  # Scrape the first 3 pages for testing
    with ThreadPoolExecutor(max_workers=1) as executor:  # Reduced max_workers to 1
        futures = {executor.submit(scrape_page, driver, url, logger): url for url in page_urls}
        for future in as_completed(futures):
            try:
                page_jobs = future.result()
                jobs.extend(page_jobs)
            except Exception as e:
                logger.error(f"An error occurred during multi-threaded scraping: {e}")
    return jobs

def categorize_jobs_by_month(jobs):
    df = pd.DataFrame(jobs)
    df['Month'] = pd.to_datetime(df['DatePosted'], errors='coerce').dt.to_period('M')
    jobs_by_month = df.groupby('Month').apply(lambda x: x.to_dict(orient='records')).to_dict()
    return jobs_by_month

def save_jobs_to_csv(jobs_by_month, output_file):
    df = pd.DataFrame([(month, job) for month, jobs in jobs_by_month.items() for job in jobs],
                      columns=['Month', 'JobDetails'])
    df.to_csv(output_file, index=False)

if __name__ == "__main__":
    logger = setup_logger()
    base_url = "https://www.indeed.com/jobs?q=software+engineer&l=New+York"
    driver = setup_selenium()

    try:
        jobs = paginate_and_scrape(driver, base_url, logger)
        jobs_by_month = categorize_jobs_by_month(jobs)
        save_jobs_to_csv(jobs_by_month, 'data/jobs_by_month.csv')
        logger.info("Job data saved successfully.")
    except TimeoutException as e:
        logger.error(f"Page load timed out: {e}")
    finally:
        driver.quit()
        logger.info("Driver closed.")
