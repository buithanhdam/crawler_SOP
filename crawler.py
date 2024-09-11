import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pdfkit
import os

# Path to wkhtmltopdf
path_to_wkhtmltopdf = os.path.join("wkhtmltox/bin/wkhtmltopdf.exe")
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
pdf_options = {
    'encoding': 'UTF-8',
    '--no-stop-slow-scripts': '',  # Bỏ qua các script chạy chậm
    '--disable-javascript': '',    # Vô hiệu hóa JavaScript để tránh lỗi liên quan
    # '--ignore-load-errors': ''     # Bỏ qua các lỗi tải trang
}   # Bỏ qua các lỗi tải trang}

def create_directory(path):
    """Create directories if they don't exist."""
    os.makedirs(path, exist_ok=True)

def extract_path_structure(base_url, full_url):
    """Extract the relative path from the full URL based on the base URL."""
    parsed_url = urlparse(full_url)
    base_path = urlparse(base_url).path
    relative_path = parsed_url.path.replace(base_path, "").strip("/")
    return relative_path.split("/")

def get_urls(base_url, driver, link_file):
    """Crawl the base URL to extract the list of relevant URLs."""
    driver.get(base_url)
    time.sleep(5)  # Wait for the page to load
    
    # Get the rendered HTML and parse it
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Find the desired list and extract all URLs
    url_list = []
    ul_element = soup.find("ul", class_="flex flex-1 flex-col gap-y-0.5")
    if ul_element:
        for li in ul_element.find_all("li", class_="flex flex-col"):
            a_tag = li.find("a", href=True)
            if a_tag and 'href' in a_tag.attrs:
                # Construct the full URL
                full_url = urljoin(base_url, a_tag['href'])
                url_list.append(full_url)
                link_file.write(full_url + "\n")
    return url_list

def count_sub_links(url_list, base_url):
    """Count the number of sub-links for each parent link."""
    count = {}
    base_path = urlparse(base_url).path
    
    for url in url_list:
        # Extract path structure relative to the base URL
        path_structure = extract_path_structure(base_url, url)
        parent_path = "/".join(path_structure[:-1]) if len(path_structure) > 1 else ""
        
        # Increment count of sub-links for the parent path
        if parent_path not in count:
            count[parent_path] = 0
        count[parent_path] += 1
    return count

def determine_save_path(base_url, current_url, count_sub_links):
    """Determine the save path, ensuring that folders are only created when necessary."""
    path_structure = extract_path_structure(base_url, current_url)
    # check
    parent_path = "/".join(path_structure[:-1]) if len(path_structure) > 1 else ""
    # Kiểm tra nếu số lượng link con >= 2 mới tạo folder
    if count_sub_links.get(parent_path, 0) >= 2:
        # Tạo đường dẫn thư mục cho đến phần thứ 2 từ cuối trở lên
        folder_path = os.path.join("output_pdf", *path_structure[:-1])
        create_directory(folder_path)
        file_name = path_structure[-1] or "index"
        output_filename = os.path.join(folder_path, f"{file_name}.pdf")
    else:
        # Không tạo folder khi số lượng link con < 2
        output_filename = os.path.join("output_pdf", f"{path_structure[0]}.pdf")
  
    return output_filename

def get_data():
    base_url = "https://fpt-7.gitbook.io/hdsd-sale-online-platform-sop"
    
    # Configure Selenium to use headless Chrome
    edge_options = Options()
    edge_options.add_argument("--headless")  # Run in headless mode
    edge_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    edge_options.add_argument("--no-sandbox")  # Bypass OS security model
    edge_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    
    # Initialize the WebDriver
    driver = webdriver.Edge(options=edge_options)
    
    with open("links.txt", "w") as link_file:
        try:
            # Gọi hàm get_urls để lấy danh sách URL và lưu vào link.txt
            get_urls(base_url, driver, link_file)
            print("URLs have been saved to link.txt.")
        except Exception as e:
            print(f"An error occurred while crawling URLs: {e}")

    try:
        # Đọc các URL từ file link.txt
        with open("links.txt", "r") as link_file:
            urls = [line.strip() for line in link_file.readlines() if line.strip()]
            print(f"Found {len(urls)} URLs from link.txt: {urls}")

        # Đếm số lượng link con để tạo folder hợp lý
        sub_link_count = count_sub_links(urls, base_url)

        # Xử lý từng URL để chuyển đổi nội dung thành PDF
        while urls:
            current_url = urls.pop(0)
            print(f"Processing URL: {current_url}")
            
            driver.get(current_url)
            time.sleep(5)
            
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
                        # Create a new tag or text to replace the <img> tag
                        img_tag = soup.new_tag("p")
                        img_tag.string = "Image URL: [img["+ urljoin(current_url, src) + "]img]"
                        img.insert_after(img_tag)
                        img.decompose() 

                
                # Save the HTML content with images
                html_content = str(main_element)
                
                # Determine the save path based on the URL structure and sub-link count
                output_filename = determine_save_path(base_url, current_url, sub_link_count)
                
                # # Convert HTML to PDF
                # pdfkit.from_string(html_content, output_filename, options=pdf_options, configuration=config)
                # print(f"PDF saved to {output_filename}")   
                try:
                        # Convert HTML to PDF
                    pdfkit.from_string(html_content, output_filename, options=pdf_options, configuration=config)
                    print(f"PDF saved to {output_filename}")
                except OSError as pdf_error:
                    print(f"Failed to save PDF for {current_url}. Error: {pdf_error}")     
            else:
                print("No <main> content found.")
                                
    except Exception as e:
        print(f"An error occurred while processing URLs: {e}")
    

if __name__ == "__main__":
    get_data()
