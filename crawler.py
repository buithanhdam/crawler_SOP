import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pdfkit 
# from keywordgen import generate_keywords
# Đường dẫn đến wkhtmltopdf
import os
path_to_wkhtmltopdf = os.path.join("wkhtmltox/bin/wkhtmltopdf.exe")

config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
pdf_options={'encoding': 'UTF-8','enable-local-file-access': True}

def split_url(url):
    # Split the URL by '/' and filter out empty parts
    parts = [part for part in url.split('/') if part]
    # Check if there is a path after the base URL
    if len(parts) > 3:
        return parts[-1]
    else:
        return "general"

def get_data():
    # urls = [
    #     "https://fpt-7.gitbook.io/hdsd-sale-online-platform-sop",
    #     "https://fpt-7.gitbook.io/hdsd-sale-online-platform-sop/upcoming",
    # ]
    urls = [
        "https://fpt-7.gitbook.io/hdsd-sale-online-platform-sop/chuc-nang-dang-bai/chia-se-quyen-dang-bai-viet",
        "https://fpt-7.gitbook.io/hdsd-sale-online-platform-sop/chuc-nang-dang-bai/kho-bai-viet-manager",
        "https://fpt-7.gitbook.io/hdsd-sale-online-platform-sop/chuc-nang-dang-bai/kho-bai-viet-salesman",
        "https://fpt-7.gitbook.io/hdsd-sale-online-platform-sop/chuc-nang-dang-bai/canh-bao-spam",
        "https://fpt-7.gitbook.io/hdsd-sale-online-platform-sop/chuc-nang-dang-bai/quan-ly-bai-viet"
    ]
    # Configure Selenium to use headless Chrome
    edge_options = Options()
    edge_options.add_argument("--headless")  # Run in headless mode
    edge_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    edge_options.add_argument("--no-sandbox")  # Bypass OS security model
    edge_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    # Initialize the WebDriver (ensure chromedriver is in your PATH)
    driver = webdriver.Edge(options=edge_options)
    
    try:
        while urls:
            current_url = urls.pop(0)  # Use pop(0) to process URLs in order
            print(f"Processing URL: {current_url}")
            
            driver.get(current_url)
            
            # Wait for the page to fully load
            time.sleep(5)  # Adjust this as necessary based on your connection and page complexity
            
            # Get the rendered HTML
            rendered_html = driver.page_source
            soup = BeautifulSoup(rendered_html, "html.parser", from_encoding="utf-8")
            
            # Locate the <main> element with specific classes
            main_element = soup.find("main", class_=lambda x: x and "flex-1" in x)
            
            if main_element:
                # Convert relative image URLs to absolute URLs
                for img in main_element.find_all("img"):
                    src = img.get("src")
                    if src:
                        img["src"] = urljoin(current_url, src)
                
                # Optionally, handle other media like <source> tags in <picture>, etc.
                
                # Save the HTML content with images
                html_content = str(main_element)
                
                # Optionally, save to a file with a unique name per URL
                file_name = split_url(current_url)
                
                
                output_filename = f"output/{file_name}.pdf"
                pdfkit.from_string(html_content, output_filename,options=pdf_options,configuration=config)
                
                print(f"PDF saved to {output_filename}")
                # generate_keywords(html_content,file_name)
            else:
                print("No <main> content found.")
                
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_data()
