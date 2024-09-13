import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pdfkit
import os

__config__ = pdfkit.configuration(wkhtmltopdf=os.path.join("wkhtmltox/bin/wkhtmltopdf.exe"))
__pdf_options__ : dict = {
        'encoding': 'UTF-8',
        '--no-stop-slow-scripts': '', 
        '--disable-javascript': '', 
        # '--ignore-load-errors': ''
        }

def split_url(url):
    # Split the URL by '/' and filter out empty parts
    parts = [part for part in url.split('/') if part]
    # Check if there is a path after the base URL
    if len(parts) > 3:
        return parts[-1]
    else:
        return "general"


def get_data():
    urls = [
        "https://epoints.vn/",
    ]
    
    # Configure Selenium to use headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    
    # Initialize the WebDriver (ensure chromedriver is in your PATH)
    driver = webdriver.Edge(options=chrome_options)
    
    try:
        while urls:
            current_url = urls.pop(0)  # Use pop(0) to process URLs in order
            print(f"Processing URL: {current_url}")
            
            driver.get(current_url)

            # Scroll to the bottom to trigger loading of all dynamic content in case it's an SPA
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)  # Wait for new content to load
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    break  # Break the loop if no new content has loaded
                last_height = new_height
            
            # Use WebDriverWait to wait for a specific element to ensure page is fully loaded
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "fullpage"))  # Change this if needed
                )
            except Exception as e:
                print(f"Element not found or page load timeout: {e}")
                continue  # Skip to the next URL if it fails
            
            # Get the rendered HTML after the page has fully loaded
            rendered_html = driver.page_source
            soup = BeautifulSoup(rendered_html, "html.parser")
            
            # Locate the <div id="fullpage">
            main_element = soup.find("div", id="fullpage")
            
            if main_element:
                # Convert relative image URLs to absolute URLs
                # for img in main_element.find_all("img"):
                #     src = img.get("src")
                #     if src:
                #         img["src"] = urljoin(current_url, src)
                
                # Save the HTML content with images
                html_content = str(main_element)
                
                # Optionally, save to a file with a unique name per URL
                file_name = split_url(current_url)
                output_filename = f"output/{file_name}.pdf"
                pdfkit.from_string(html_content, output_filename, options=__pdf_options__, configuration=__config__)

                
                print(f"Content saved to {output_filename}")
            else:
                print("No <main> content found.")
                
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_data()
