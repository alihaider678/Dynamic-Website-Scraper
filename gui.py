# job_scraper/gui.py

import tkinter as tk
from tkinter import messagebox
import threading
from scraper import paginate_and_scrape, categorize_jobs_by_month, save_jobs_to_csv
from utils.selenium_setup import setup_selenium
from utils.logger_setup import setup_logger

class ScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Job Scraper")

        # Search Query Label and Entry
        tk.Label(root, text="Search Query:").grid(row=0, column=0, padx=10, pady=10)
        self.query_entry = tk.Entry(root, width=40)
        self.query_entry.grid(row=0, column=1, padx=10, pady=10)

        # Location Label and Entry
        tk.Label(root, text="Location:").grid(row=1, column=0, padx=10, pady=10)
        self.location_entry = tk.Entry(root, width=40)
        self.location_entry.grid(row=1, column=1, padx=10, pady=10)

        # Start Button
        self.start_button = tk.Button(root, text="Start Scraping", command=self.start_scraping)
        self.start_button.grid(row=2, column=1, padx=10, pady=10)

        # Status Label
        self.status_label = tk.Label(root, text="Status: Waiting to start", fg="blue")
        self.status_label.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

        self.logger = setup_logger()

    def start_scraping(self):
        query = self.query_entry.get().strip()
        location = self.location_entry.get().strip()

        if not query or not location:
            messagebox.showwarning("Input Error", "Please provide both search query and location.")
            return

        base_url = f"https://www.indeed.com/jobs?q={query}&l={location}"
        self.status_label.config(text="Status: Scraping started", fg="green")

        # Run the scraping process in a separate thread to avoid freezing the GUI
        threading.Thread(target=self.run_scraping, args=(base_url,)).start()

    def run_scraping(self, base_url):
        driver = setup_selenium()

        try:
            jobs = paginate_and_scrape(driver, base_url, self.logger)
            jobs_by_month = categorize_jobs_by_month(jobs)
            save_jobs_to_csv(jobs_by_month, 'data/jobs_by_month.csv')
            self.status_label.config(text="Status: Scraping completed and data saved", fg="green")
            messagebox.showinfo("Success", "Job data saved successfully to data/jobs_by_month.csv")
        except Exception as e:
            self.logger.error(f"An error occurred during scraping: {e}")
            self.status_label.config(text="Status: Scraping failed", fg="red")
            messagebox.showerror("Error", "An error occurred during scraping. Check the logs for more details.")
        finally:
            driver.quit()
            self.logger.info("Driver closed.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ScraperGUI(root)
    root.mainloop()
