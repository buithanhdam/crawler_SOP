from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import time
import heapq
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from selenium.webdriver.support import expected_conditions as EC
import re
patterns_to_exclude = [
    r'\.css(\?.*)?$', r'\.js(\?.*)?$',
    r'\.mp3(\?.*)?$', r'\.mp4(\?.*)?$', r'\.avi(\?.*)?$', r'\.mov(\?.*)?$', r'\.flv(\?.*)?$',
    r'\.pdf(\?.*)?$', r'\.docx(\?.*)?$', r'\.xlsx(\?.*)?$', r'\.pptx(\?.*)?$', r'\.txt(\?.*)?$',
    r'\.woff(\?.*)?$', r'\.woff2(\?.*)?$', r'\.ttf(\?.*)?$', r'\.eot(\?.*)?$', r'\.ico(\?.*)?$',
    r'\.jpg(\?.*)?$',r'\.jpeg(\?.*)?$',r'\.png(\?.*)?$',r'\.gif(\?.*)?$',r'\.svg(\?.*)?$',r'\.webp(\?.*)?$',r'\.php(\?.*)?$',
    r'\.jsp(\?.*)?$',r'\.scss(\?.*)?$',r'\.py(\?.*)?$',r'\.jsx(\?.*)?$',r'\.tsx(\?.*)?$',r'\.json(\?.*)?$'
    ,r'wp-json', r'/image\?url=', r'/embed\?url='
]
tags_with_urls = {
                'a': 'href',
                'link': 'href',
                'script': 'src',
                'iframe': 'src',
                'form': 'action',
                'area': 'href'
            }
def is_valid_url(url, base_domain):
    parsed_url = urlparse(url)
    # Kiểm tra nếu URL là tuyệt đối và cùng domain
    return parsed_url.netloc == base_domain
def normalize_url(url):
    """Chuẩn hóa URL bằng cách loại bỏ dấu gạch chéo cuối và fragment identifier."""
    parsed_url = urlparse(url)
    path = parsed_url.path.rstrip('/')
    normalized_url = parsed_url._replace(path=path, fragment='').geturl()
    return normalized_url
def get_data():
    
    visited_urls = set()
    queue = []
    base_url = "https://fpt-7.gitbook.io/hdsd-sale-online-platform-sop"
    heapq.heappush(queue, (0, normalize_url(base_url)))  
    base_domain = urlparse(base_url).netloc
    # Configure Selenium to use headless Chrome
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")  # Disable GPU acceleration
    options.add_argument("--no-sandbox")  # Bypass OS security model
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    
    # Initialize the WebDriver (ensure chromedriver is in your PATH)
    driver = webdriver.Edge(options=options)
    while queue:
        priority, current_url = heapq.heappop(queue)
        if current_url in visited_urls:
            continue

        visited_urls.add(current_url)
        print(f"Processing URL: {current_url}")
        try: # Use pop(0) to process URLs in order
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
            # Các thẻ HTML và thuộc tính cần lấy URL

            # Thu thập URL từ các thẻ và thuộc tính đã chỉ định
            for tag, attribute in tags_with_urls.items():
                for element in soup.find_all(tag):
                    url = element.get(attribute)
                    if url:
                        # Bỏ qua các URL hình ảnh (dựa trên phần mở rộng file)
                        if any(re.search(pattern, url) for pattern in patterns_to_exclude):
                            continue
                        # Xử lý URL tương đối
                        if url.startswith('/'):
                            full_url = urljoin(base_url, url)  # Kết hợp với base URL để tạo thành URL tuyệt đối
                            if is_valid_url(full_url, base_domain) and full_url not in visited_urls:
                                heapq.heappush(queue, (0, normalize_url(full_url)))

                        # Xử lý URL tuyệt đối và kiểm tra tính hợp lệ với domain cơ sở
                        elif url.startswith('http://') or url.startswith('https://'):
                            if is_valid_url(url, base_domain) and url not in visited_urls:
                                heapq.heappush(queue, (0, normalize_url(url)))       
        except Exception as e:
            print(f"An error occurred: {e}")
        # Lưu các URL vào file txt
    with open('urls.txt', 'w') as f:
        for url in visited_urls:
            f.write(url + '\n')
        print(f'Đã lưu {len(visited_urls)} URL vào file urls.txt.')
    driver.quit()

if __name__ == "__main__":
    get_data()
