from openai import OpenAI
import os
from dotenv import load_dotenv

# Main function to perform the summarization process
def generate_keywords(content,file_name):
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Hãy đọc nội dung được cung cấp, phân tích nó, "
                    "và trích xuất các từ khóa liên quan nhất, chỉ lấy top 5 từ khoá. Chỉ trả về kết quả ở định dạng như sau: "
                    '{"keyword": ["keyword1", "keyword2", "keyword3"]}. Không thêm bất kỳ thông tin nào khác."'
                )
            },
            {
                "role": "user",
                "content": content
            }
        ],
        temperature=0.2,
        top_p=1
    )
    response_message = response.choices[0].message.content
    
    # Optionally, save to a file with a unique name per URL
    output_filename = f"output/{file_name}.json"
    with open(output_filename, "w", encoding="utf-8") as file:
        file.write(response_message)
    
    print(f"Keywords saved to {output_filename}")

if __name__ == "__main__":
    # Example content; replace with your actual content
    content = "<html>Your HTML content here</html>"
    generate_keywords(content)
