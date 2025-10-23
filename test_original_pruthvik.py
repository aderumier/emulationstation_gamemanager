#!/usr/bin/env python3
"""
Test script using the EXACT original pruthvik-sheth/google-images-scraper code
Based on: https://github.com/pruthvik-sheth/google-images-scraper/blob/main/scraping/scraper.py
"""

import sys
import os
sys.path.append('google-images-scraper')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from threading import Thread, Lock
from urllib import parse
import time

class Scraper:
    
    def __init__(self, num_threads = 1, show_ui = True) -> None:
        self.__num_threads = num_threads
        self.__show_ui = show_ui
        self.__drivers = []

        self._initialize_scraper()

    def _initialize_scraper(self):
        pool = []
        for i in range(self.__num_threads):
            thread = Thread(target = self._create_driver)
            pool.append(thread)
            thread.start()
        
        for thread in pool:
            thread.join()
            
    def _create_threads(self):
        for i in range(self.__num_threads):
            thread = Thread(target = self._get_images, args = (self.__drivers[i],))
            self.__threads_pool.append(thread)
            thread.start()

    def _destroy_threads(self):
        for thread in self.__threads_pool:
            thread.join()

    def _create_driver(self):
        self.__options = webdriver.ChromeOptions()
        self.__options.add_argument("incognito")
        if not self.__show_ui:
            self.__options.add_argument("headless")
        
        # Use remote Selenium Docker instead of local Chrome
        try:
            driver = webdriver.Remote(
                command_executor='http://localhost:4444/wd/hub',
                options=self.__options
            )
            print("✅ Connected to Selenium Docker container")
        except Exception as e:
            print(f"❌ Failed to connect to Selenium Docker: {e}")
            # Fallback to local Chrome
            driver = webdriver.Chrome(options=self.__options)
            print("✅ Using local Chrome driver")
        
        driver.get("https://www.google.com/imghp?hl=en")
        self.__drivers.append(driver)

    def _load_thumbnails(self, driver):
        def get_thumbnails():
            try:
                print("\nFetching image thumbnails...")
                # older = isv-r PNCib ViTmJb BUooTd
                thumbnails = driver.find_elements(By.XPATH, "//div[@class='czzyk XOEbc']")
                # updated = czzyk XOEbc
                print(f"🤖: Found {len(thumbnails)} image thumbnails!")
            except Exception as e:
                print("\n🔴🔴 Error while fetching image containers! 🔴🔴")
            return thumbnails
        thumbnails = get_thumbnails()

        while len(thumbnails) < self.__image_limit:
            print("🤖: Scrolling...")
            driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
            time.sleep(3)
            thumbnails = get_thumbnails()
            time.sleep(3)
            try:
                end_of_page = driver.find_element(By.XPATH, """//input[@class='LZ4I']""").is_displayed()
                no_more_results = driver.find_element(By.XPATH, """//div[@class='OuJzKb Yu2Dnd']""").is_displayed()
                if end_of_page:
                    driver.find_element(By.XPATH, """//input[@class='LZ4I']""").click()

                if no_more_results:
                    break
            except Exception as e:
                print("\n🔴🔴 Search more button not found! 🔴🔴")

        print(f"🤖: Found a total of {len(thumbnails)} image thumbnails!") 
        driver.execute_script("window.scrollTo(0,0)")
        time.sleep(2)
        return thumbnails

    def _get_images(self, driver):
        # driver = webdriver.Chrome()
        driver.get(self.__url)
        thumbnails = self._load_thumbnails(driver)
        
        wait = WebDriverWait(driver, 10)
        print("\nFetching Links...")

        while len(self.__images) < self.__image_limit:   
            self.__shared_index_lock.acquire()
            index = self.__shared_index
            self.__shared_index += 1
            self.__shared_index_lock.release()
            try:
                if not index >= self.__image_limit:
                    # print(len(self.__images))
                    thumbnails[index].click()
                    # print(index)
                    time.sleep(2)
                    # older = sFlh5c pT0Scc iPVvYb
                    wait.until(EC.visibility_of_element_located((By.XPATH, """//img[@class='sFlh5c FyHeAf iPVvYb']""")))
                    # updated = sFlh5c FyHeAf iPVvYb
                    img_window = driver.find_element(By.XPATH, """//img[@class='sFlh5c FyHeAf iPVvYb']""")
                    # time.sleep(2)
                    link = img_window.get_attribute('src')
                    self.__images.add(link)
                    print(link)
                else:
                    print("✔️✔️✔️ Links Scraping complete! ✔️✔️✔️")
                    break
                                    
            except Exception as e:
                print(" \n🔴🔴 Link not found! 🔴🔴")
                continue

    @staticmethod
    def create_url(search_query):
        parsed_query = parse.urlencode({'q': search_query})
        url = f"https://www.google.com/search?{parsed_query}&source=lnms&tbm=isch&sa=X&ved=2ahUKEwjR5qK3rcbxAhXYF3IKHYiBDf8Q_AUoAXoECAEQAw&biw=1291&bih=590"
        return url

    def scrape(self, query, count):
        self.__threads_pool = []
        self.__shared_index = 0
        self.__shared_index_lock = Lock()
        self.__images = set()

        self.__url = self.create_url(query)
        self.__image_limit = count
        start = time.time()
        self._create_threads()
        self._destroy_threads()
        end = time.time()
        print(len(self.__images))
        
        print(f"Total elapsed time for {self.__image_limit} images is: {(end - start) / 60} mins")
        return self.__images

def main():
    """Test the original pruthvik-sheth scraper"""
    print("🚀 Testing Original Pruthvik-Sheth Google Images Scraper")
    print("=" * 70)
    
    try:
        # Create scraper with 1 thread and headless mode
        scraper = Scraper(num_threads=1, show_ui=False)
        
        # Test with a simple query
        query = "Alan Wake"
        count = 5
        
        print(f"🔍 Searching for: {query}")
        print(f"📊 Target count: {count} images")
        
        # Scrape images
        images = scraper.scrape(query=query, count=count)
        
        print(f"\n{'='*70}")
        print(f"📊 RESULTS SUMMARY")
        print(f"{'='*70}")
        print(f"Query: {query}")
        print(f"Target: {count} images")
        print(f"Found: {len(images)} images")
        
        if images:
            print(f"\n📋 Image URLs:")
            for i, url in enumerate(images, 1):
                print(f"  {i}. {url[:80]}...")
        else:
            print("❌ No images found!")
        
        # Close drivers
        for driver in scraper._Scraper__drivers:
            driver.quit()
        
        print(f"\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
