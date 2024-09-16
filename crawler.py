from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from selenium.webdriver.support import expected_conditions as EC
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathos.multiprocessing import ProcessingPool as Pool 
from threading import Semaphore
import os 
import sqlite3
from contextlib import contextmanager
PATTERNS_TO_EXCLUDE = [
    r'\.css(\?.*)?$', r'\.js(\?.*)?$',
    r'\.mp3(\?.*)?$', r'\.mp4(\?.*)?$', r'\.avi(\?.*)?$', r'\.mov(\?.*)?$', r'\.flv(\?.*)?$',
    r'\.pdf(\?.*)?$', r'\.docx(\?.*)?$', r'\.xlsx(\?.*)?$', r'\.pptx(\?.*)?$', r'\.txt(\?.*)?$',
    r'\.woff(\?.*)?$', r'\.woff2(\?.*)?$', r'\.ttf(\?.*)?$', r'\.eot(\?.*)?$', r'\.ico(\?.*)?$',
    r'\.jpg(\?.*)?$',r'\.jpeg(\?.*)?$',r'\.png(\?.*)?$',r'\.gif(\?.*)?$',r'\.svg(\?.*)?$',r'\.webp(\?.*)?$',r'\.php(\?.*)?$',
    r'\.jsp(\?.*)?$',r'\.scss(\?.*)?$',r'\.py(\?.*)?$',r'\.jsx(\?.*)?$',r'\.tsx(\?.*)?$',r'\.json(\?.*)?$'
    ,r'wp-json', r'/image\?url=', r'/embed\?url='
]
TAGS_WITH_URLS = {
                'a': 'href',
                'link': 'href',
                'script': 'src',
                'iframe': 'src',
                'form': 'action',
                'area': 'href'
            }
TAG_TO_EXCULDE =['script', 'style', 'link', 'meta', 'noscript', 'iframe', 'embed', 'object', 'applet']

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
            # Tạo bảng base_urls
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS base_urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base_url VARCHAR(500) UNIQUE,
                status VARCHAR(20) DEFAULT 'onprocessing'
            )
            ''')
            # Tạo bảng sub_urls
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sub_urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base_url_id INTEGER,
                sub_url VARCHAR(500) UNIQUE,
                data_path VARCHAR(500) UNIQUE,
                file_extension VARCHAR(10),
                FOREIGN KEY (base_url_id) REFERENCES base_urls(id)
            )
            ''')
        print("Bảng `urls` đã được tạo hoặc đã tồn tại.")

    def add_url(self, base_url, sub_url, data_path, file_extension):
        """
        Thêm một URL vào cơ sở dữ liệu.
        Nếu base_url chưa tồn tại, thêm nó trước.
        Sau đó, thêm sub_url vào bảng sub_urls.
        Nếu sub_url đã tồn tại, bỏ qua và in ra thông báo.
        """
        with self.get_db_connection() as cursor:
            # Kiểm tra và thêm base_url nếu chưa tồn tại
            base_url_id = self.check_base_url_exists(base_url)

            if base_url_id is False:
                # Thêm base_url mới vào bảng base_urls
                cursor.execute("INSERT INTO base_urls (base_url) VALUES (?)", (base_url.strip(),))
                base_url_id = cursor.lastrowid  # Lấy id của base_url vừa thêm
                print(f"Base URL '{base_url}' đã được thêm vào cơ sở dữ liệu.")

            # Thêm sub_url vào bảng sub_urls
            try:
                cursor.execute(
                    "INSERT INTO sub_urls (base_url_id, sub_url, data_path, file_extension) VALUES (?, ?, ?, ?)",
                    (base_url_id, sub_url.strip(), data_path.strip(), file_extension.strip())
                )
                print(f"Sub URL '{sub_url}' đã được thêm thành công.")
            except sqlite3.IntegrityError:
                print(f"Sub URL '{sub_url}' đã tồn tại trong cơ sở dữ liệu.")
    def get_all_urls_by_base_url(self, base_url):
        """
        Lấy tất cả các sub URL từ cơ sở dữ liệu dựa trên base_url và trả về dưới dạng danh sách.
        """
        with self.get_db_connection() as cursor:
            cursor.execute("""
                SELECT sub_url FROM sub_urls
                INNER JOIN base_urls ON sub_urls.base_url_id = base_urls.id
                WHERE base_urls.base_url = ?
            """, (base_url.strip(),))
            urls = [row[0] for row in cursor.fetchall()]
        return urls
    def check_base_url_exists(self, base_url):
        """
        Kiểm tra xem base_url đã tồn tại trong cơ sở dữ liệu hay chưa.
        """
        with self.get_db_connection() as cursor:
            cursor.execute("SELECT id FROM base_urls WHERE base_url = ?", (base_url.strip(),))
            return cursor.fetchone() is not None
    def check_and_get_base_url_status(self, base_url):
        """
        Kiểm tra xem base_url đã tồn tại trong cơ sở dữ liệu hay chưa.
        Nếu tồn tại, trả về ID và trạng thái (status) của base_url, ngược lại trả về None.
        """
        with self.get_db_connection() as cursor:
            cursor.execute("SELECT id, status FROM base_urls WHERE base_url = ?", (base_url.strip(),))
            result = cursor.fetchone()

            if result:
                base_url_id, status = result
                return {
                    "exists": True,
                    "id": base_url_id,
                    "status": status
                }
            else:
                return {"exists": False,"status": "none"}
    def update_base_url_status(self, base_url):
        """
        Cập nhật trạng thái của base_url thành 'done'.
        Trả về True nếu cập nhật thành công, ngược lại False.
        """
        with self.get_db_connection() as cursor:
            cursor.execute('''
                UPDATE base_urls
                SET status = 'done'
                WHERE base_url = ?
            ''', (base_url.strip(),))

            # Kiểm tra xem có dòng nào bị ảnh hưởng (tức là đã cập nhật thành công)
            return cursor.rowcount > 0

    def check_url_exists(self, sub_url):
        """
        Kiểm tra xem sub_url đã tồn tại trong cơ sở dữ liệu hay chưa.
        """
        with self.get_db_connection() as cursor:
            cursor.execute("SELECT 1 FROM sub_urls WHERE sub_url = ?", (sub_url.strip(),))
            return cursor.fetchone() is not None
class Crawler:
    __driver_options__: Options
    __driver__: webdriver.Edge
    MAX_CONNECTIONS: int = 5
    num_workers:int= 5
    MAX_RETRIES: int = 3
    TIMEOUT: int = 10 
    __semaphore__ : Semaphore
    __db__ :SQLite
    base_url = "https://fpt-7.gitbook.io/hdsd-sale-online-platform-sop"
    def __new__(cls):
        instance = super().__new__(cls)
        instance.__driver_options__ = Options()
        instance.__driver_options__.add_argument("--headless")  # Run in headless mode
        instance.__driver_options__.add_argument("--disable-gpu")  # Disable GPU acceleration
        instance.__driver_options__.add_argument("--no-sandbox")  # Bypass OS security model
        instance.__driver_options__.add_argument("--disable-dev-shm-usage")
        instance.__driver_options__.add_argument('--ignore-certificate-errors')
        instance.__driver_options__.add_argument('--ignore-ssl-errors') 
        instance.__driver__ = webdriver.Edge(options=instance.__driver_options__)
        instance.__semaphore__= Semaphore(instance.MAX_CONNECTIONS)
        instance.__db__ = SQLite()
        return instance
    def __init__(self):
        os.makedirs(os.path.dirname("output"), exist_ok=True)
        pass
    def url_to_path(self, url, base_url):
        """
        Chuyển URL thành một đường dẫn file hợp lệ để lưu HTML.
        """
        parsed_url = urlparse(url)
        # Bỏ phần http:// hoặc https://, thay dấu '/' bằng '\\' hoặc '/'
        path = parsed_url.path.lstrip('/')
        path = path.replace('/', os.sep)  # Sử dụng os.sep để phù hợp với hệ điều hành (Windows là '\\', Unix là '/')

        # Nếu đường dẫn trống (tức là URL là trang gốc), sử dụng 'index.html'
        if not path:
            path = 'index.html'
        elif not path.endswith('.html'):
            # Nếu không có đuôi file, thêm '.html' vào cuối
            path += '.html'

        # Ghép với domain của base_url để tạo folder chính
        base_domain = urlparse(base_url).netloc
        full_path = os.path.join("output",base_domain, path)
        return full_path
    def is_valid_url(self,url, base_domain):
        parsed_url = urlparse(url)
        return parsed_url.netloc == base_domain
    def save_html_content(self, content, filename):
        """ Lưu nội dung HTML vào file. """
        try:
            # Tạo thư mục nếu chưa có
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(str(content))
        except IOError as e:
            print(e)
    def normalize_url(self,url):
        """Chuẩn hóa URL bằng cách loại bỏ dấu gạch chéo cuối và fragment identifier."""
        parsed_url = urlparse(url)
        path = parsed_url.path.rstrip('/')
        normalized_url = parsed_url._replace(path=path, fragment='').geturl()
        return normalized_url
    def fetch_url(self,url):
        """Lấy nội dung của URL và phân tích các liên kết."""
        if self.__db__.check_url_exists(url):
            return url, None
        attempt = 0
        while attempt < self.MAX_RETRIES:
            try:
                with self.__semaphore__:
                    self.__driver__.get(url)

                    # Scroll to the bottom to trigger loading of all dynamic content in case it's an SPA
                    last_height = self.__driver__.execute_script("return document.body.scrollHeight")
                        
                    while True:
                        self.__driver__.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)  # Wait for new content to load
                        new_height = self.__driver__.execute_script("return document.body.scrollHeight")
                            
                        if new_height == last_height:
                            break  # Break the loop if no new content has loaded
                        last_height = new_height
                        
                        # Use WebDriverWait to wait for a specific element to ensure page is fully loaded
                        try:
                            WebDriverWait(self.__driver__, 30).until(
                                EC.presence_of_element_located((By.ID, "fullpage"))  # Change this if needed
                            )
                        except:
                            # print(f"Element not found or page load timeout: {e}")
                            continue  # Skip to the next URL if it fails
                    rendered_html = self.__driver__.page_source
                    soup = BeautifulSoup(rendered_html, "html.parser")
                    return url, soup
            except Exception as e:
                # print("Error: ",e)
                continue
            attempt += 1
            time.sleep(2 ** attempt)  # Backoff mỗi lần thử lại
        return url, None
    def crawl_threaded(self,base_url):
        """Crawl dữ liệu song song bằng threading."""
        visited_urls = set()
        queue = [self.normalize_url(base_url)]
        base_domain = urlparse(base_url).netloc
        base_status = self.check_and_get_base_url_status(base_url)
        if base_status['exists'] and base_status['status'] =='done':
            print(f"Base URL tồn tại với ID: {base_status['id']}, trạng thái: {base_status['status']}")
            return
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            while queue:
                futures = {executor.submit(self.fetch_url, url): url for url in queue}
                queue = []
                for future in as_completed(futures):
                    url, soup = future.result()
                    if url and soup and url not in visited_urls:
                        visited_urls.add(url)
                        print(f'Crawling {url}')
                        body = soup.find('body')
                        if body:
                            url_tag = soup.new_tag("p")
                            url_tag.string = f"Paper URL: [paper[{url}]paper]"
                            body.insert(0, url_tag) 
                            # Loại bỏ các thẻ không cần thiết
                            for tag in body(TAG_TO_EXCULDE):
                                tag.decompose()
                            for img in body.find_all("img"):
                                src = img.get("src")
                                if src:
                                    # Create a new tag or text to replace the <img> tag
                                    img_tag = soup.new_tag("p")
                                    img_tag.string = "Image URL: [img["+ urljoin(url, src) + "]img]"
                                    img.insert_after(img_tag)
                                    img.decompose()
                            try:
                            # Chuyển URL thành đường dẫn file
                                file_path = self.url_to_path(url, base_url)
                                self.save_html_content(body, file_path)
                                self.__db__.add_url(base_url,url,file_path,".html")
                            except:
                                continue
                        for tag, attribute in TAGS_WITH_URLS.items():
                            for element in soup.find_all(tag):
                                link = element.get(attribute)
                                if link:
                                    # Bỏ qua các URL hình ảnh (dựa trên phần mở rộng file)
                                    if any(re.search(pattern, link) for pattern in PATTERNS_TO_EXCLUDE):
                                        continue
                                    # Xử lý URL tương đối
                                    if link.startswith('/'):
                                        full_url = urljoin(base_url, link)  # Kết hợp với base URL để tạo thành URL tuyệt đối
                                        normalized_url = self.normalize_url(full_url)
                                        if self.is_valid_url(normalized_url, base_domain) and normalized_url not in visited_urls:
                                            queue.append(normalized_url)

                                    # Xử lý URL tuyệt đối và kiểm tra tính hợp lệ với domain cơ sở
                                    elif link.startswith('http://') or url.startswith('https://'):
                                        normalized_url = self.normalize_url(link)
                                        if self.is_valid_url(normalized_url, base_domain) and normalized_url not in visited_urls:
                                            queue.append(normalized_url)
        self.__db__.update_base_url_status(base_url)                                   
if __name__ == "__main__":
    c = Crawler()
    c.crawl_threaded(base_url='https://emind.vn/')
