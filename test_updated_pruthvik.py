#!/usr/bin/env python3
"""
Updated version of pruthvik-sheth scraper with current Google Images selectors
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from threading import Thread, Lock
from urllib import parse
import time

class UpdatedScraper:
    
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
        options = webdriver.ChromeOptions()
        options.add_argument("incognito")
        if not self.__show_ui:
            options.add_argument("headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Use Selenium Docker
        driver = webdriver.Remote(
            command_executor='http://localhost:4444/wd/hub',
            options=options
        )
        print("✅ Connected to Selenium Docker container")
        
        driver.get("https://www.google.com/imghp?hl=en")
        self.__drivers.append(driver)

    def _load_thumbnails(self, driver):
        def get_thumbnails():
            try:
                print("\nFetching image thumbnails...")
                # Current working selector
                thumbnails = driver.find_elements(By.XPATH, "//div[@class='czzyk XOEbc']")
                print(f"🤖: Found {len(thumbnails)} image thumbnails!")
            except Exception as e:
                print(f"\n🔴🔴 Error while fetching image containers! 🔴🔴: {e}")
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
                print(f"\n🔴🔴 Search more button not found! 🔴🔴: {e}")

        print(f"🤖: Found a total of {len(thumbnails)} image thumbnails!") 
        driver.execute_script("window.scrollTo(0,0)")
        time.sleep(2)
        return thumbnails

    def _get_images(self, driver):
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
                if not index >= self.__image_limit and index < len(thumbnails):
                    print(f"🔍 Clicking thumbnail {index + 1}...")
                    thumbnails[index].click()
                    time.sleep(3)
                    
                    # Try multiple selectors for full-size images
                    full_size_selectors = [
                        "//img[@class='sFlh5c FyHeAf iPVvYb']",  # Original
                        "//img[contains(@class, 'sFlh5c')]",     # Partial match
                        "//img[contains(@src, 'http') and not(contains(@src, 'googleusercontent'))]",  # HTTP images
                        "//img[contains(@src, 'data:image')]",   # Base64 images
                        "//img[@data-src]",                      # Lazy loaded images
                        "//img[contains(@class, 'YQ4gaf')]"     # Another possible class
                    ]
                    
                    link = None
                    for selector in full_size_selectors:
                        try:
                            wait.until(EC.visibility_of_element_located((By.XPATH, selector)))
                            img_window = driver.find_element(By.XPATH, selector)
                            link = img_window.get_attribute('src')
                            if link and link.startswith(('http', 'data:image')):
                                print(f"✅ Found image with selector: {selector}")
                                break
                        except:
                            continue
                    
                    if link:
                        self.__images.add(link)
                        print(f"📸 Image {len(self.__images)}: {link[:80]}...")
                    else:
                        print(f"⚠️ No image found for thumbnail {index + 1}")
                else:
                    print("✔️✔️✔️ Links Scraping complete! ✔️✔️✔️")
                    break
                                    
            except Exception as e:
                print(f"🔴🔴 Link not found for thumbnail {index + 1}! 🔴🔴: {e}")
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
        
        print(f"\n📊 Found {len(self.__images)} images")
        print(f"⏱️ Total elapsed time for {self.__image_limit} images: {(end - start) / 60:.2f} mins")
        return self.__images

def main():
    """Test the updated pruthvik-sheth scraper"""
    print("🚀 Testing Updated Pruthvik-Sheth Google Images Scraper")
    print("=" * 70)
    
    try:
        # Create scraper with 1 thread and headless mode
        scraper = UpdatedScraper(num_threads=1, show_ui=False)
        
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
        for driver in scraper._UpdatedScraper__drivers:
            driver.quit()
        
        print(f"\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
