import requests
import re
import time

def extract_qr_url(html_content):
    """从HTML内容中提取二维码URL"""
    pattern = r'var qrurl\s*=\s*"([^"]+)"'
    match = re.search(pattern, html_content)
    return match.group(1) if match else None

def check_login_status(session, base_url, max_checks=20, interval=2):
    """检查登录状态"""
    check_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": base_url,
        "X-Requested-With": "XMLHttpRequest"
    }
    
    login_check_url = f"{base_url}?op=checklogin"
    
    for i in range(max_checks):
        try:
            response = session.get(login_check_url, headers=check_headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("status"):
                redirect_url = result.get("url")
                if redirect_url:
                    redirect_url = redirect_url.strip().strip('"')
                return True, redirect_url
            
            time.sleep(interval)
            
        except requests.exceptions.RequestException:
            time.sleep(interval)
        except ValueError:
            time.sleep(interval)
    
    return False, None

def main():
    base_url = "https://login.b8n.cn/qr/weixin/student/2"
    session = requests.Session()
    
    # 设置基础cookies
    session.cookies.update({
        "successuri": "%2Fstudent%2Fuidlogin",
        "domain": "k8n.cn",
        "append": "ref%3D%252Fstudent",
        "ssl": "1"
    })
    
    # 设置基础请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://login.b8n.cn/auth/login/student/2",
        "Upgrade-Insecure-Requests": "1"
    }
    
    try:
        # 获取二维码页面
        response = session.get(base_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            qr_url = extract_qr_url(response.text)
            if qr_url:
                print(f"二维码链接: {qr_url}")
                print("请使用微信扫描上方二维码进行登录...")
                # 检查登录状态
                login_success, redirect_url = check_login_status(session, base_url)
                
                if login_success and redirect_url:
                    
                    # 访问跳转URL获取cookie
                    try:
                        redirect_response = session.get(redirect_url, headers=headers, timeout=10, allow_redirects=True)
                        
                        # 收集所有Set-Cookie
                        all_cookies = []
                        # 检查重定向历史
                        for resp in redirect_response.history + [redirect_response]:
                            if 'Set-Cookie' in resp.headers:
                                all_cookies.append(resp.headers['Set-Cookie'])
                        
                        # 查找remember_student cookie
                        for cookie in all_cookies:
                            if cookie.strip().startswith('remember_student_'):
                                # 只输出cookie的核心部分，不包含额外信息
                                print(cookie.split(';')[0])
                                return redirect_url
                        
                        # 检查会话中的cookies
                        for name, value in session.cookies.items():
                            if name.startswith('remember_student_'):
                                # 只输出cookie的核心部分，不包含额外信息
                                print(f"{name}={value}")
                                return redirect_url
                        
                    except requests.exceptions.RequestException:
                        pass
                    
                    return redirect_url
                else:
                    return qr_url
            else:
                print("未能提取二维码URL")
                return None
        else:
            print(f"访问失败，状态码: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"访问失败: {e}")
        return None

if __name__ == "__main__":
    main()
