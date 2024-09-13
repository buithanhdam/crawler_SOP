import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import requests

def split_url(url):
    parts = [part for part in url.split('/') if part]
    if len(parts) > 3:
        return parts[-1]
    else:
        return "general"

def fetch_css_links(soup, current_url):
    """Extract external CSS links from the HTML."""
    css_files = []
    for link_tag in soup.find_all("link", rel="stylesheet"):
        href = link_tag.get("href")
        if href:
            css_url = urljoin(current_url, href)
            css_files.append(css_url)
    return css_files

def download_css_files(css_urls, output_dir):
    """Download CSS files from the extracted URLs."""
    css_content = ""
    for css_url in css_urls:
        try:
            response = requests.get(css_url)
            if response.status_code == 200:
                css_content += response.text
            else:
                print(f"Failed to download CSS: {css_url}")
        except Exception as e:
            print(f"Error fetching CSS from {css_url}: {e}")
    return css_content

def get_data():
    urls = [
        "https://epoints.vn/",
    ]
    
    # Configure Selenium to use headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Edge(options=chrome_options)
    
    try:
        while urls:
            current_url = urls.pop(0)
            print(f"Processing URL: {current_url}")
            
            driver.get(current_url)

            # Scroll to the bottom to ensure all dynamic content is loaded
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Wait for a specific element to ensure all dynamic content is loaded
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "fullpage"))
                )
            except Exception as e:
                print(f"Element not found or page load timeout: {e}")
                continue
            
            # Get the rendered HTML
            rendered_html = driver.page_source
            soup = BeautifulSoup(rendered_html, "html.parser")
            
            # Locate the main content
            main_element = soup.find("div", id="fullpage")
            
            if main_element:
                # Convert relative image URLs to absolute URLs
                for img in main_element.find_all("img"):
                    src = img.get("src")
                    if src:
                        img["src"] = urljoin(current_url, src)
                
                html_content = str(main_element)
                
                # Fetch external CSS links
                css_urls = fetch_css_links(soup, current_url)
                
                # Download the CSS content
                css_content = download_css_files(css_urls, "output")
                
                # Combine HTML content and CSS
                final_html = f"<html><head><style>{css_content}</style></head><body>{html_content}</body></html>"
                
                # Create the output directory if it doesn't exist
                output_dir = "output"
                os.makedirs(output_dir, exist_ok=True)
                
                # Generate a file name from the URL
                file_name = split_url(current_url)
                html_file_path = f"{output_dir}/{file_name}.html"
                
                # Save the HTML content to a file
                with open(html_file_path, "w", encoding="utf-8") as file:
                    file.write(final_html)
                
                print(f"HTML saved as {html_file_path}")
            else:
                print("No main content found.")
                
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_data()
