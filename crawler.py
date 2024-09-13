import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlparse
import pdfkit
import os
import sqlite3
from contextlib import contextmanager
  
  
# extract ul li or find a with href (#ascasc, full https://.. , /.... )
class SQLite:
    __db_name__ = "crawler.db"
    def __init__(self):
        self.create_table()
        pass
    @contextmanager
    def get_db_connection(self):
        conn = sqlite3.connect(self.__db_name__)
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()  # Lưu thay đổi sau khi thực thi xong
        finally:
            conn.close()  # Đóng kết nối khi xong
    def create_table(self):
        with self.get_db_connection() as cursor:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base_url VARCHAR(500),
                url VARCHAR(500) UNIQUE,
                data_path VARCHAR(500) UNIQUE
            )
            ''')
        print("Bảng `urls` đã được tạo hoặc đã tồn tại.")
    def add_url(self,base_url,url,data_path):
        """
        Thêm một URL vào cơ sở dữ liệu.
        Nếu URL đã tồn tại, bỏ qua và in ra thông báo.
        """
        with self.get_db_connection() as cursor:
            try:
                cursor.execute("INSERT INTO urls (base_url,url,data_path) VALUES (?,?,?)", (base_url.strip(),url.strip(),data_path.strip()))
                print(f"URL '{url}' đã được thêm thành công.")
            except sqlite3.IntegrityError:
                print(f"URL '{url}' đã tồn tại trong cơ sở dữ liệu.")
    def get_all_urls_by_base_url(self,base_url):
        """
        Đọc tất cả các URL từ cơ sở dữ liệu và trả về dưới dạng danh sách.
        """
        with self.get_db_connection() as cursor:
            cursor.execute("SELECT url FROM urls WHERE base_url = ?", (base_url,))
            urls = [row[0] for row in cursor.fetchall()]
        return urls
    def check_base_url_exists(self,base_url):
        """
        Kiểm tra xem URL đã tồn tại trong cơ sở dữ liệu hay chưa.
        """
        with self.get_db_connection() as cursor:
            cursor.execute("SELECT 1 FROM urls WHERE base_url = ?", (base_url,))
            return cursor.fetchone() is not None
    def check_url_exists(self,url):
        """
        Kiểm tra xem URL đã tồn tại trong cơ sở dữ liệu hay chưa.
        """
        with self.get_db_connection() as cursor:
            cursor.execute("SELECT 1 FROM urls WHERE url = ?", (url,))
            return cursor.fetchone() is not None
    
class Crawler:
    __config__ = pdfkit.configuration(wkhtmltopdf=os.path.join("wkhtmltox/bin/wkhtmltopdf.exe"))
    __pdf_options__ : dict = {
        'encoding': 'UTF-8',
        '--no-stop-slow-scripts': '', 
        '--disable-javascript': '', 
        # '--ignore-load-errors': ''
        }
    __edge_options__ : Options
    __driver__ : webdriver.Edge
    __db__ :SQLite
    def __new__(cls):
        instance = super().__new__(cls)
        instance.__edge_options__ = Options()
        instance.__edge_options__.add_argument("--headless")  # Run in headless mode
        instance.__edge_options__.add_argument("--disable-gpu")  # Disable GPU acceleration
        instance.__edge_options__.add_argument("--no-sandbox")  # Bypass OS security model
        instance.__edge_options__.add_argument("--disable-dev-shm-usage") 
        instance.__driver__ = webdriver.Edge(options=instance.__edge_options__)
        instance.__db__ = SQLite()
        return instance
    
    def __init__(self):
        pass
    
    def split_url(self,url) -> str:
        parts = [part for part in url.split('/') if part]
        if len(parts) > 3:
            return parts[-1]
        else:
            return "general"
    def create_directory(self,path):
        """Create directories if they don't exist."""
        os.makedirs(path, exist_ok=True)

    def extract_path_structure(self,base_url, full_url):
        """Extract the relative path from the full URL based on the base URL."""
        parsed_url = urlparse(full_url)
        base_path = urlparse(base_url).path
        relative_path = parsed_url.path.replace(base_path, "").strip("/")
        return relative_path.split("/")
    def count_sub_links(self,url_list, base_url):
        """Count the number of sub-links for each parent link."""
        count = {}
        
        for url in url_list:
            # Extract path structure relative to the base URL
            path_structure = self.extract_path_structure(base_url, url)
            parent_path = "/".join(path_structure[:-1]) if len(path_structure) > 1 else ""
            
            # Increment count of sub-links for the parent path
            if parent_path not in count:
                count[parent_path] = 0
            count[parent_path] += 1
        return count
    def determine_save_path(self,base_url, current_url, count_sub_links):
        """Determine the save path, ensuring that folders are only created when necessary."""
        path_structure = self.extract_path_structure(base_url, current_url)
        # check
        parent_path = "/".join(path_structure[:-1]) if len(path_structure) > 1 else ""
        # Kiểm tra nếu số lượng link con >= 2 mới tạo folder
        if count_sub_links.get(parent_path, 0) >= 2:
            # Tạo đường dẫn thư mục cho đến phần thứ 2 từ cuối trở lên
            folder_path = os.path.join("output", *path_structure[:-1])
            self.create_directory(folder_path)
            file_name = path_structure[-1] or "index"
            output_filename = os.path.join(folder_path, f"{file_name}.pdf")
        else:
            # Không tạo folder khi số lượng link con < 2
            output_filename = os.path.join("output", f"{path_structure[0]}.pdf")
    
        return output_filename
    def get_sub_urls_from_base_url(self,base_url) -> list:
        """Crawl the base URL to extract the list of relevant URLs."""
        self.__driver__.get(base_url)
        time.sleep(5)
        soup = BeautifulSoup(self.__driver__.page_source, "html.parser")
        url_list = []
        ul_element = soup.find("ul", class_="flex flex-1 flex-col gap-y-0.5")
        if ul_element:
            for li in ul_element.find_all("li", class_="flex flex-col"):
                a_tag = li.find("a", href=True)
                if a_tag and 'href' in a_tag.attrs:
                    # Construct the full URL
                    full_url = urljoin(base_url, a_tag['href'])
                    url_list.append(full_url)
        return url_list
    
    def get_urls_to_crawl(self,base_url) -> list:
        """Check if the extracted URLs are already present in the file."""
        try:
            urls_to_check = self.get_sub_urls_from_base_url(base_url)
            if not self.__db__.check_base_url_exists(base_url):
                return urls_to_check
            existing_urls = self.__db__.get_all_urls_by_base_url(base_url)
            result = []
            # Compare URLs
            for url in urls_to_check:
                if url not in existing_urls:
                # if not self.__db__.url_exists(url):
                    result.append(url)
            return result
        except Exception as e:
            print(f"An error occurred while crawling URLs: {e}")
            return []
        
    def crawl(self,base_url):
        try:
            os.makedirs("output", exist_ok=True)
            urls = self.get_urls_to_crawl(base_url)
            if len(urls) ==0:
                print("Data from paper url already upto-date.")
                return
            # Xử lý từng URL để chuyển đổi nội dung thành PDF
            sub_link_count = self.count_sub_links(urls, base_url)
            while urls:
                current_url = urls.pop(0)
                print(f"Processing URL: {current_url}")
                
                self.__driver__.get(current_url)
                time.sleep(5)
                
                # Get the rendered HTML
                rendered_html = self.__driver__.page_source
                soup = BeautifulSoup(rendered_html, "html.parser", from_encoding="utf-8")
                
                # Locate the <main> element with specific classes
                main_element = soup.find("main", class_=lambda x: x and "flex-1" in x)
                
                if main_element:
                    # Convert relative image URLs to absolute URLs
                    url_tag = soup.new_tag("p")
                    url_tag.string = f"Paper URL: [paper[{current_url}]paper]"
                    main_element.insert(0, url_tag) 
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
                    output_filename = self.determine_save_path(base_url, current_url, sub_link_count)
                    try:
                        pdfkit.from_string(html_content, output_filename, options=self.__pdf_options__, configuration=self.__config__)
                        self.__db__.add_url(base_url,current_url,output_filename)
                        print(f"PDF saved to {output_filename}")
                    except:
                        try:
                            file_name = self.split_url(current_url)
                            file_output = os.path.join("output", f"{file_name}.pdf")
                            pdfkit.from_string(html_content, file_output, options=self.__pdf_options__, configuration=self.__config__)
                            self.__db__.add_url(base_url,current_url,file_output)
                            print(f"PDF saved to {file_output}")
                        except OSError as pdf_error:
                            print(f"Failed to save PDF for {current_url}. Error: {pdf_error}")     
                else:
                    print("No <main> content found.")
                                    
        except Exception as e:
            print(f"An error occurred while processing URLs: {e}")
        
if __name__ == "__main__":
    base_url = "https://fpt-7.gitbook.io/hdsd-sale-online-platform-sop" 
    crawler_tool = Crawler()
    crawler_tool.crawl(base_url=base_url)
    
