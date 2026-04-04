from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import json
import os
import requests
import re
import time
import uuid
import urllib.parse
import schedule_manager
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 设置Flask会话密钥
app.secret_key = os.urandom(24)

# 访问控制装饰器
def login_required(f):
    """确保用户已登录"""
    def decorated_function(*args, **kwargs):
        if 'credential' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        credential = data.get('credential')
        
        if not credential:
            return jsonify({"success": False, "message": "请输入凭证"})
        
        # 验证凭证
        is_valid, cred = validate_credential(credential)
        if not is_valid:
            return jsonify({"success": False, "message": "无效的凭证"})
        
        # 不再检查凭证是否已使用，允许重复登录
        # 标记凭证为已使用（保持向后兼容）
        mark_credential_used(credential)
        
        # 设置会话
        session['credential'] = credential
        session['user_id'] = cred.get('user_id', credential)
        
        return jsonify({"success": True, "message": "登录成功"})
    
    # GET请求返回登录页面
    return render_template('login.html')

# 登出路由
@app.route('/logout')
def logout():
    if 'credential' in session:
        # 不再重置凭证状态，允许重复使用
        # 清除会话
        session.clear()
    return redirect(url_for('login'))

# 获取当前用户凭证信息的API端点
@app.route('/get_current_credential')
@login_required
def get_current_credential():
    """获取当前登录用户的凭证信息"""
    try:
        # 从会话中获取凭证
        current_credential = session.get('credential')
        if not current_credential:
            return jsonify({'success': False, 'message': '未找到用户凭证'})
        
        # 获取用户提交内容（如果有）
        submission = get_user_submission(current_credential)
        has_submission = submission is not None
        
        return jsonify({
            'success': True,
            'credential': current_credential,
            'has_submission': has_submission
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取凭证信息失败: {str(e)}'
        })

# 服务器端存储会话信息
server_sessions = {}

# 凭证相关配置
CREDENTIALS_FILE = 'credentials.json'

# 用户提交内容配置
SUBMISSIONS_FILE = 'submissions.json'

# 初始化提交内容文件
if not os.path.exists(SUBMISSIONS_FILE):
    with open(SUBMISSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

# 加载提交内容
def load_submissions():
    """加载所有用户提交内容"""
    try:
        with open(SUBMISSIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载提交内容文件失败: {e}")
        return {}

# 保存提交内容
def save_submissions(submissions):
    """保存提交内容到文件"""
    try:
        with open(SUBMISSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(submissions, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"保存提交内容文件失败: {e}")
        return False

# 保存用户提交内容
def save_user_submission(credential, submission_data):
    """保存用户提交内容"""
    submissions = load_submissions()
    submissions[credential] = submission_data
    return save_submissions(submissions)

# 获取用户提交内容
def get_user_submission(credential):
    """获取用户提交内容"""
    submissions = load_submissions()
    return submissions.get(credential, None)

# 删除用户提交内容
def delete_user_submission(credential):
    """删除用户提交内容"""
    submissions = load_submissions()
    if credential in submissions:
        del submissions[credential]
        return save_submissions(submissions)
    return True

# 初始化凭证文件
if not os.path.exists(CREDENTIALS_FILE):
    with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False, indent=4)

# 加载凭证
def load_credentials():
    """加载所有凭证"""
    try:
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载凭证文件失败: {e}")
        return []

# 保存凭证
def save_credentials(credentials):
    """保存凭证到文件"""
    try:
        with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(credentials, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"保存凭证文件失败: {e}")
        return False

# 验证凭证
def validate_credential(credential):
    """验证凭证是否有效"""
    credentials = load_credentials()
    for cred in credentials:
        if cred['credential'] == credential:
            return True, cred
    return False, None

# 标记凭证为已使用（保持向后兼容，实际不再使用）
def mark_credential_used(credential):
    """标记凭证为已使用"""
    # 不再需要标记used字段，直接返回True
    return True

# 重置凭证状态（保持向后兼容，实际不再使用）
def reset_credential(credential):
    """重置凭证状态为未使用"""
    # 不再需要重置used字段，直接返回True
    return True


# 会话配置
SESSION_TIMEOUT = 120  # 会话超时时间（秒）
MAX_SESSIONS = 100  # 最大会话数量

# 清理过期会话
def cleanup_sessions():
    current_time = time.time()
    expired_sessions = []
    
    for session_id, data in server_sessions.items():
        # 检查会话是否过期
        if current_time - data.get('created_at', 0) > SESSION_TIMEOUT:
            expired_sessions.append(session_id)
    
    # 删除过期会话
    if expired_sessions:
        logger.info(f"清理 {len(expired_sessions)} 个过期会话")
        for session_id in expired_sessions:
            del server_sessions[session_id]

# 微信登录相关配置
BASE_URL = "https://login.b8n.cn/qr/weixin/student/2"

# 从HTML内容中提取二维码URL
def extract_qr_url(html_content):
    pattern = r'var qrurl\s*=\s*"([^"]+)"'
    match = re.search(pattern, html_content)
    return match.group(1) if match else None

# 检查登录状态
def check_login_status(session_obj, base_url):
    check_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": base_url,
        "X-Requested-With": "XMLHttpRequest"
    }
    
    login_check_url = f"{base_url}?op=checklogin"
    
    try:
        response = session_obj.get(login_check_url, headers=check_headers, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("status"):
            redirect_url = result.get("url")
            if redirect_url:
                redirect_url = redirect_url.strip().strip('"')
            return True, redirect_url
        
    except requests.exceptions.RequestException:
        pass
    except ValueError:
        pass
    
    return False, None

# 获取remember_student cookie
def get_remember_cookie(session_obj, redirect_url, headers):
    try:
        redirect_response = session_obj.get(redirect_url, headers=headers, timeout=10, allow_redirects=True)
        
        # 收集所有Set-Cookie
        all_cookies = []
        for resp in redirect_response.history + [redirect_response]:
            if 'Set-Cookie' in resp.headers:
                all_cookies.append(resp.headers['Set-Cookie'])
        
        # 查找remember_student cookie
        for cookie in all_cookies:
            if cookie.strip().startswith('remember_student_'):
                return cookie.split(';')[0]
        
        # 检查会话中的cookies
        for name, value in session_obj.cookies.items():
            if name.startswith('remember_student_'):
                return f"{name}={value}"
        
    except requests.exceptions.RequestException:
        pass
    
    return None

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/get_qr_code')
@login_required
def get_qr_code():
    # 创建新的会话ID
    session_id = str(uuid.uuid4())
    
    # 创建请求会话
    req_session = requests.Session()
    
    # 设置基础cookies
    req_session.cookies.update({
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
        response = req_session.get(BASE_URL, headers=headers, timeout=10)
        response.raise_for_status()  # 自动抛出HTTP错误
        
        qr_url = extract_qr_url(response.text)
        if not qr_url:
            return jsonify({
                'success': False,
                'message': '未能从页面中提取二维码URL'
            })
        
        # 保存会话信息
        current_time = time.time()
        server_sessions[session_id] = {
            'session_obj': req_session,
            'headers': headers,
            'qr_url': qr_url,
            'base_url': BASE_URL,
            'login_success': False,
            'cookie': None,
            'redirect_url': None,
            'created_at': current_time,  # 创建时间
            'last_accessed': current_time  # 最后访问时间
        }
        
        # 在添加新会话前清理过期会话
        cleanup_sessions()
        
        # 检查会话数量是否超过限制，超过则清理LRU会话
        cleanup_lru_sessions()
        
        # 生成二维码图片URL
        encoded_url = urllib.parse.quote(qr_url)
        
        # 使用可靠的备用二维码生成服务（qrserver）
        qrcode_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_url}"
        
        logger.info(f"新会话创建成功: {session_id}")
        return jsonify({
            'success': True,
            'session_id': session_id,
            'qr_url': qrcode_url
        })
    except requests.exceptions.HTTPError as e:
        return jsonify({
            'success': False,
            'message': f'获取二维码失败 (HTTP {e.response.status_code})'
        })
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'message': '网络连接错误，请检查您的网络设置'
        })
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'message': '请求超时，请稍后重试'
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'message': f'获取二维码失败: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'服务器内部错误: {str(e)}'
        })

# 添加LRU会话清理（当会话数量超过限制时）
def cleanup_lru_sessions():
    if len(server_sessions) <= MAX_SESSIONS:
        return
    
    # 按最后访问时间排序会话（最久未访问的在前）
    sorted_sessions = sorted(
        server_sessions.items(),
        key=lambda x: x[1].get('last_accessed', 0)
    )
    
    # 删除最久未访问的会话，直到达到限制
    sessions_to_delete = len(server_sessions) - MAX_SESSIONS
    for i in range(sessions_to_delete):
        del server_sessions[sorted_sessions[i][0]]

@app.route('/check_login/<session_id>')
@login_required
def check_login(session_id):
    # 先清理过期会话
    cleanup_sessions()
    
    if session_id not in server_sessions:
        logger.warning(f"会话不存在或已过期: {session_id}")
        return jsonify({
            'success': False,
            'message': '会话不存在或已过期'
        })
    
    session_data = server_sessions[session_id]
    
    # 更新最后访问时间
    session_data['last_accessed'] = time.time()
    server_sessions[session_id] = session_data
    
    if session_data['login_success']:
        return jsonify({
            'success': True,
            'logged_in': True,
            'cookie': session_data['cookie']
        })
    
    # 检查登录状态
    login_success, redirect_url = check_login_status(session_data['session_obj'], session_data['base_url'])
    
    if login_success and redirect_url:
        # 获取remember_student cookie
        cookie = get_remember_cookie(session_data['session_obj'], redirect_url, session_data['headers'])
        
        # 更新会话信息
        session_data['login_success'] = True
        session_data['redirect_url'] = redirect_url
        session_data['cookie'] = cookie
        server_sessions[session_id] = session_data
        
        logger.info(f"用户登录成功: {session_id}")
        return jsonify({
        'success': True,
        'logged_in': True,
        'cookie': cookie
    })
    
    # 用户还未扫码登录，返回正常状态（不是错误）
    return jsonify({
        'success': True,
        'logged_in': False,
        'message': '等待扫码登录'
    })

# 获取课程信息的函数
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
    
    # 设置请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "max-age=0",
        "Priority": "u=0, i",
        "Sec-Ch-Ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
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
            return False, None, [], None, "cookie格式不正确，应为 'name=value' 格式"
    
    try:
        # 发送请求
        response = session.get(course_url, headers=headers, timeout=10, allow_redirects=True)
        
        # 检查是否成功访问课程页面
        success = course_url in response.url
        
        # 提取用户ID和姓名信息
        users = []
        form_id = None
        error_message = None
        
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
        
        except ImportError:
            error_message = "未安装BeautifulSoup4，无法提取用户信息和表单ID"
        except Exception as e:
            error_message = f"提取信息时出错: {str(e)}"
        
        return success, response, users, form_id, error_message
        
    except requests.exceptions.RequestException as e:
        return False, None, [], None, f"访问失败: {str(e)}"

# 获取QQ头像链接
def get_qq_avatar(qq_number):
    """生成QQ头像URL"""
    return f"http://q1.qlogo.cn/g?b=qq&nk={qq_number}&s=100"

# 保存数据到JSON文件
def save_data_to_json(data, credential=None):
    """
    将数据保存为指定的JSON格式
    
    参数:
    data: 包含所有必要信息的字典
    credential: 用户凭证（用于文件名生成）
    
    返回:
    bool: 保存是否成功
    str: 错误信息（如果保存失败）
    """
    try:
        # 转换数据为用户需要的格式
        formatted_data = {
            "cookie": data.get("cookie", ""),
            "name": data.get("remark_name", ""),
            "username": data.get("keep_username", ""),
            "avatar": data.get("qq_avatar", ""),
            "course_url": data.get("course_url", ""),
            "default_form_data": {
                "form_id": data.get("form_id", ""),
                "to_user_ida[]": data.get("selected_auditor", {}).get("user_id", ""),
                "_score": "0"
            },
            "schedule": {
                "enabled": data.get("schedule_enabled", False),
                "start_time": data.get("schedule_start_time", "08:00"),
                "end_time": data.get("schedule_end_time", "09:00"),
                "days": data.get("schedule_days", [1, 2, 3, 4, 5, 6, 7])
            }
        }
        
        # 生成文件名（优先使用凭证，否则使用时间戳）
        import json
        import os
        from datetime import datetime
        
        if credential:
            filename = f"data_{credential}.json"
        else:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"data_{timestamp}.json"
        
        file_path = os.path.join(os.getcwd(), "data", filename)
        
        # 确保data目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 保存数据到JSON文件
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(formatted_data, f, ensure_ascii=False, indent=4)
        
        return True, file_path
        
    except Exception as e:
        return False, str(e)

# 获取课程信息的路由
@app.route('/get_course_info', methods=['POST'])
@login_required
def get_course_info():
    try:
        # 获取请求数据
        data = request.get_json()
        course_url = data.get('course_url')
        cookie = data.get('cookie')
        
        if not course_url or not cookie:
            return jsonify({
                'success': False,
                'message': '请提供课程URL和Cookie'
            })
        
        # 校验课程URL格式
        course_url_pattern = re.compile(r'^https://k8n\.cn/student/profile/course/\d+/\d+$')
        if not course_url_pattern.match(course_url):
            return jsonify({
                'success': False,
                'message': '课程URL格式不正确，请输入类似 https://k8n.cn/student/profile/course/123456/789012 的格式'
            })
        
        # 获取课程信息
        success, response, users, form_id, error_message = access_course_page(course_url, cookie, verbose=False)
        
        if success:
            return jsonify({
                'success': True,
                'form_id': form_id,
                'users': users
            })
        else:
            return jsonify({
                'success': False,
                'message': error_message or '获取课程信息失败'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理请求时出错: {str(e)}'
        })

# 提交额外信息的路由
@app.route('/submit_extra_info', methods=['POST'])
@login_required
def submit_extra_info():
    try:
        # 获取请求数据
        data = request.get_json()
        
        # 验证必要字段
        required_fields = ['remark_name', 'keep_username', 'qq_number', 'course_url']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'请提供{field}字段'
                })
        
        # 生成QQ头像链接
        qq_number = data.get('qq_number')
        qq_avatar = get_qq_avatar(qq_number)
        
        # 整合所有信息
        all_info = {
            'remark_name': data.get('remark_name'),
            'keep_username': data.get('keep_username'),
            'qq_number': qq_number,
            'qq_avatar': qq_avatar,
            'course_url': data.get('course_url'),
            'form_id': data.get('form_id'),
            'users': data.get('users', []),
            'selected_auditor': data.get('selected_auditor', {}),
            'cookie': data.get('cookie'),
            'schedule_enabled': data.get('schedule_enabled', False),
            'schedule_start_time': data.get('schedule_start_time', '08:00'),
            'schedule_end_time': data.get('schedule_end_time', '09:00'),
            'schedule_days': data.get('schedule_days', [1, 2, 3, 4, 5, 6, 7])
        }
        
        # 这里可以添加数据处理或存储逻辑
        # 例如保存到数据库、写入文件等
        
        # 获取当前用户的凭证
        current_credential = session.get('credential')
        
        # 检查是否已经有提交记录
        existing_submission = get_user_submission(current_credential)
        if existing_submission:
            return jsonify({
                'success': False,
                'message': '您已经提交过信息，请先删除之前的提交内容再重新提交'
            })
        
        # 处理额外信息提交
        
        # 保存数据到JSON文件（传递凭证用于命名）
        save_success, result = save_data_to_json(all_info, current_credential)
        
        # 保存用户提交内容到submissions.json
        if current_credential:
            # 保存完整的提交信息
            submission_data = {
                'submitted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'data_file': os.path.basename(result),  # 获取文件名
                'remark_name': all_info['remark_name'],
                'keep_username': all_info['keep_username'],
                'qq_number': all_info['qq_number'],
                'course_url': all_info['course_url'],
                'form_id': all_info['form_id'],
                'selected_auditor': all_info['selected_auditor']
            }
            save_user_submission(current_credential, submission_data)
        
        if save_success:
            return jsonify({
                'success': True,
                'message': f'信息提交成功，数据已保存到: {result}'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'信息提交成功，但数据保存失败: {result}'
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理请求时出错: {str(e)}'
        })

# 删除提交内容的路由
@app.route('/delete_submission', methods=['POST'])
@login_required
def delete_submission():
    try:
        # 获取当前用户的凭证
        current_credential = session.get('credential')
        if not current_credential:
            return jsonify({'success': False, 'message': '未找到用户凭证'})
        
        # 获取用户提交内容
        submission = get_user_submission(current_credential)
        if submission:
            # 获取数据文件路径
            data_file_path = os.path.join(os.getcwd(), 'data', submission.get('data_file', ''))
            
            # 删除数据文件（如果存在）
            if os.path.exists(data_file_path):
                os.remove(data_file_path)
            
            # 删除提交记录
            delete_success = delete_user_submission(current_credential)
            if delete_success:
                return jsonify({'success': True, 'message': '提交内容已成功删除'})
            else:
                return jsonify({'success': False, 'message': '删除提交记录失败'})
        else:
            return jsonify({'success': False, 'message': '未找到提交内容'})
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理请求时出错: {str(e)}'
        })

# 定时任务管理API端点
@app.route('/api/schedule/jobs', methods=['GET'])
def get_schedule_jobs():
    """获取所有定时任务信息"""
    try:
        manager = schedule_manager.get_schedule_manager()
        jobs_info = manager.get_jobs_info()
        return jsonify({
            'success': True,
            'jobs': jobs_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取任务信息失败: {str(e)}'
        })

@app.route('/api/schedule/reload', methods=['GET'])
def reload_schedule():
    """重新加载定时任务配置"""
    try:
        manager = schedule_manager.get_schedule_manager()
        manager.load_user_configs()
        return jsonify({
            'success': True,
            'message': '定时任务配置已重新加载'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'重新加载配置失败: {str(e)}'
        })

if __name__ == '__main__':
    # 启动定时任务管理器
    try:
        schedule_manager.start_scheduler()
        logger.info("定时任务管理器已启动")
    except Exception as e:
        logger.error(f"启动定时任务管理器失败: {e}")
    
    app.run(debug=False, host='0.0.0.0', port=5000,use_reloader=False)
