import requests

def access_course_page(course_url, remember_cookie, verbose=True):
    """访问课程页面并提取用户信息和表单ID
    
    Args:
        course_url: 课程页面的URL
        remember_cookie: remember_student_开头的完整cookie字符串，格式为 "name=value"
        verbose: 是否打印详细信息（默认True）
    
    Returns:
        tuple: (是否成功, 响应对象, 用户信息列表, 表单ID)
               用户信息列表格式: [{"user_id": "xxx", "name": "xxx"}, ...]
               表单ID格式: 字符串或None
    """
    # 创建会话对象
    session = requests.Session()
    
    # 设置与用户提供的完全一致的请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "max-age=0",
        "Priority": "u=0, i",
        "Sec-Ch-Ua": "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "\"Windows\"",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    
    # 设置remember_student cookie
    if remember_cookie:
        try:
            cookie_name = remember_cookie.split('=')[0]
            cookie_value = remember_cookie.split('=', 1)[1]
            session.cookies.update({cookie_name: cookie_value})
        except IndexError:
            print("[错误] cookie格式不正确，应为 'name=value' 格式")
            return False, None, [], None
    
    try:
        # 发送请求
        response = session.get(course_url, headers=headers, timeout=10, allow_redirects=True)
        
        # 不保存网页，直接处理内容
        
        # 检查是否成功访问课程页面
        success = course_url in response.url
        
        # 提取用户ID和姓名信息
        users = []
        form_id = None
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 找到所有用户选项
            user_options = soup.find_all('input', {'name': 'to_user_ida[]'})
            
            for option in user_options:
                user_id = option.get('value')
                label = option.find_parent('label')
                if label:
                    name = label.get_text(strip=True)
                    users.append({
                        'user_id': user_id,
                        'name': name
                    })
            
            # 提取表单ID
            form_input = soup.find('input', {'name': 'form_id', 'type': 'hidden'})
            if form_input:
                form_id = form_input.get('value')
                if verbose:
                    print(f"[成功] 提取到表单ID: {form_id}")
        
        except ImportError:
            # 保留必要的提示信息
            print("[提示] 未安装BeautifulSoup4，跳过用户信息和表单ID提取")
        except Exception as e:
            print(f"提取信息时出错: {e}")
        
        # 不输出成功/失败信息，直接返回结果
            
        return success, response, users, form_id
        
    except requests.exceptions.RequestException as e:
        # 保留必要的错误信息
        print(f"访问失败: {e}")
        return False, None, [], None

def main():
    # 简化的示例用法
    course_url = ""
    remember_cookie = ""
    
    # 静默模式调用
    success, response, users, form_id = access_course_page(course_url, remember_cookie, verbose=False)
    
    if success:
        import json
        result = {
            "form_id": form_id,
            "users": users
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("访问失败")

if __name__ == "__main__":
    main()
