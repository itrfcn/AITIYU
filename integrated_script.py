#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Name: integrated_script.py
About: 整合图片上传和表单提交功能的脚本，用于自动提交跑步截图
Author: LynxFrost
AuthorBlog: https://blog.itrf.cn


整合图片上传和表单提交功能的脚本
1. 上传图片到OSS并获取file URL
2. 将file URL填入表单数据
3. 提交表单到课程页面
"""

import requests
import json
import os
import random
import string
import argparse
import hashlib
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ========================== 配置参数 ==========================
# 调试模式（True=打印详细信息，False=只打印关键信息）
DEBUG = False

# 课程页面URL（可自定义）
COURSE_URL = ""

# Cookie信息（字符串格式，只需要remember_student部分，s=部分会自动获取）
COOKIE_STRING = ""

# 要上传的图片路径（可自定义）
IMAGE_PATH = ""  # 已确认存在的图片路径

# 表单数据配置（可自定义）
FORM_DATA_B = ""  # 班级姓名信息

# 默认表单参数
DEFAULT_FORM_DATA = {
    "form_id": "",  # 表单ID（可自定义）
    "to_user_ida[]": "",  # 接收人ID（可自定义）
    "_score": "0"
}

# 支持的图片格式 ，网站默认的是.png，这里保持一致
SUPPORTED_IMAGE_FORMATS = ['.png']
# =============================================================

# 定义获取s=部分cookie的函数
def get_session_cookie(remember_cookie=None, course_url=COURSE_URL):
    """
    获取s=部分的session cookie
    
    参数:
        remember_cookie: remember_student部分的cookie（可选）
        course_url: 课程页面URL（可选）
    
    返回:
        s=部分的cookie字符串
    """
    url = course_url
    
    # 构建基础请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "max-age=0"
    }
    
    # 如果提供了remember_cookie，添加到请求头中
    if remember_cookie:
        headers["cookie"] = remember_cookie
    
    try:
        # 发送GET请求获取Set-Cookie头
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # 获取Set-Cookie头
        cookie_header = response.headers.get('Set-Cookie')
        if cookie_header:
            # 查找s=部分的cookie
            import re
            s_cookie_match = re.search(r's=([^;]+);', cookie_header)
            if s_cookie_match:
                s_cookie = f"s={s_cookie_match.group(1)}"
                logger.info(f"成功获取session cookie: {s_cookie}")
                return s_cookie
        
        logger.warning("未找到s=部分的cookie")
        return ""
        
    except requests.exceptions.RequestException as e:
        logger.error(f"获取session cookie失败: {e}")
        return ""

# 定义获取OSS上传密钥的函数
def get_oss_key(cookies=None, course_url=COURSE_URL):
    """
    获取OSS上传密钥
    
    参数:
        cookies: Cookie信息，字符串格式（可选）
        course_url: 课程页面URL（可选）
    
    返回:
        OSS配置字典
    """
    url = "https://k8n.cn/student/oss-upload-key"
    
    # 构建基础请求头
    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9",
        "priority": "u=1, i",
        "referer": course_url,
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "Windows",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest"
    }
    
    # 设置Cookie
    if cookies:
        headers["cookie"] = cookies
    else:
        # 使用默认cookie
        headers["cookie"] = COOKIE_STRING
    
    try:
        # 发送GET请求获取OSS密钥
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 检查请求是否成功
        
        # 解析响应
        oss_config = response.json()
        logger.info("成功获取OSS上传密钥")
        return oss_config
        
    except requests.exceptions.RequestException as e:
        logger.error(f"获取OSS密钥失败: {e}")
        return None

# 生成唯一文件名的函数
def generate_random_filename(file_extension):
    """
    生成随机文件名，格式：哈希值 + 原扩展名
    示例：a1b2c3d4e5f6g7h8i9j0.png
    """
    
    # 生成包含时间戳和随机字符串的哈希值
    timestamp = str(time.time())
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    hash_input = f"{timestamp}{random_str}".encode('utf-8')
    
    # 使用SHA-256哈希算法生成文件名
    hash_name = hashlib.sha256(hash_input).hexdigest()[:19]  # 取前19位
    
    # 组合成完整的哈希文件名
    hash_filename = f"{hash_name}{file_extension}"
    
    return hash_filename

# 定义上传图片到OSS的函数
def upload_image_to_oss(oss_config, image_path):
    """
    上传图片到OSS
    
    参数:
        oss_config: OSS配置字典
        image_path: 图片本地路径
    
    返回:
        成功返回文件信息字典，失败返回None
    """
    if not oss_config:
        logger.error("OSS配置无效，无法上传图片")
        return None
    
    # 检查图片文件是否存在
    if not os.path.exists(image_path):
        logger.error(f"图片文件不存在: {image_path}")
        return None
    
    # 检查文件是否为图片
    file_extension = os.path.splitext(image_path)[1].lower()
    if file_extension not in SUPPORTED_IMAGE_FORMATS:
        logger.error(f"文件不是支持的图片格式: {file_extension}")
        logger.error(f"  支持的格式: {', '.join(SUPPORTED_IMAGE_FORMATS)}")
        return None
    
    # 获取OSS配置参数
    accessid = oss_config['accessid']
    host = oss_config['host']
    policy = oss_config['policy']
    signature = oss_config['signature']
    expire = oss_config['expire']
    callback = oss_config['callback']
    dir = oss_config['dir']
    
    # 生成随机文件名
    filename = generate_random_filename(file_extension)
    
    # 构建上传URL
    upload_url = host
    
    # 构建表单数据
    form_data = {
        'key': dir + '/' + filename,  # 完整的文件路径
        'OSSAccessKeyId': accessid,
        'policy': policy,
        'Signature': signature,
        'success_action_status': '200',  # 成功返回的状态码
        'callback': callback
    }
    
    try:
        # 打开文件并发送POST请求
        with open(image_path, 'rb') as f:
            # 添加文件到表单数据
            files = {
                'file': (filename, f, f'image/{file_extension[1:]}')
            }
            
            # 发送上传请求
            logger.info(f"正在上传图片: {filename}")
            logger.info(f"  目标路径: {dir}/{filename}")
            response = requests.post(upload_url, data=form_data, files=files)
            response.raise_for_status()  # 检查请求是否成功
            
            # 打印响应信息
            logger.info("上传成功！")
            if DEBUG:
                logger.debug(f"  响应状态码: {response.status_code}")
            
            # 解析响应内容（如果是JSON格式）
            try:
                response_json = response.json()
                if DEBUG:
                    logger.debug("  响应内容:")
                    logger.debug(f"  - 成功: {response_json.get('success')}")
                    if response_json.get('data'):
                        data = response_json['data']
                        logger.debug(f"  - 文件名称: {data.get('name')}")
                        logger.debug(f"  - 文件大小: {data.get('size')} 字节")
                        logger.debug(f"  - 文件类型: {data.get('type')}")
                if response_json.get('data') and response_json['data'].get('file'):
                    data = response_json['data']
                    if DEBUG:
                        logger.debug(f"  - 访问URL: {data.get('file')}")
                    # 返回文件信息
                    return {
                        'name': data.get('name'),
                        'file': data.get('file'),
                        'size': data.get('size'),
                        'type': data.get('type')
                    }
            except json.JSONDecodeError:
                if DEBUG:
                    logger.debug(f"  响应内容: {response.text}")
                # 尝试从响应文本中提取文件信息
                # 注意：这可能需要根据实际响应格式进行调整
                return {
                    'name': filename,
                    'file': f"{host}/{dir}/{filename}",
                    'size': os.path.getsize(image_path),
                    'type': f"image/{file_extension[1:]}"
                }
            
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"上传失败: {e}")
        return None
    except Exception as e:
        logger.error(f"上传过程中发生错误: {e}")
        return None

# 定义提交表单的函数
def submit_course_form(form_data, cookies=None, custom_headers=None, course_url=COURSE_URL):
    """
    向课程页面提交表单
    
    参数:
        form_data: 表单数据，字典格式
        cookies: Cookie信息，字符串格式或字典格式（可选）
        custom_headers: 自定义请求头，字典格式（可选）
        course_url: 课程页面URL（可选）
    
    返回:
        response: 最终响应对象
    """
    # 基础请求URL
    url = course_url
    
    # 基础请求头
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "max-age=0",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://k8n.cn",
        "referer": course_url,
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    }
    
    # 处理Cookie
    cookies_dict = None
    if cookies:
        if isinstance(cookies, str):
            # 如果是字符串格式的Cookie，添加到请求头中
            headers["cookie"] = cookies
        elif isinstance(cookies, dict):
            # 如果是字典格式的Cookie，直接使用
            cookies_dict = cookies
    
    # 更新自定义请求头
    if custom_headers:
        headers.update(custom_headers)
    
    # 发送POST请求
    try:
        # 只在调试模式下打印详细的开始信息
        if DEBUG:
            logger.debug("正在发送表单提交请求...")
        
        # 发送请求，允许重定向
        response = requests.post(
            url,
            headers=headers,
            data=form_data,
            cookies=cookies_dict,
            allow_redirects=True
        )
        
        # 只在调试模式下打印详细的请求和响应信息
        if DEBUG:
            # 打印请求信息
            logger.debug("请求信息")
            logger.debug(f"请求URL: {url}")
            logger.debug(f"请求方法: POST")
            logger.debug("请求头:")
            for key, value in headers.items():
                logger.debug(f"  {key}: {value}")
            
            logger.debug("表单数据:")
            for key, value in form_data.items():
                # 解析URL编码的JSON字符串
                if isinstance(value, str) and (key == "formdata[a]" or key == "formdata[b]"):
                    try:
                        # 尝试解析JSON
                        parsed_value = json.loads(value)
                        logger.debug(f"  {key}: {json.dumps(parsed_value, indent=4, ensure_ascii=False)}")
                    except json.JSONDecodeError:
                        logger.debug(f"  {key}: {value}")
                else:
                    logger.debug(f"  {key}: {value}")
            
            if cookies:
                logger.debug("Cookie:")
                if isinstance(cookies, dict):
                    for key, value in cookies.items():
                        logger.debug(f"  {key}: {value}")
                elif isinstance(cookies, str):
                    logger.debug(f"  {cookies}")
            
            # 打印响应信息
            logger.debug("响应信息")
            
            # 打印所有响应历史
            if response.history:
                logger.debug("重定向历史:")
                for i, hist in enumerate(response.history):
                    logger.debug(f"  [{i+1}] {hist.status_code} -> {hist.headers.get('location')}")
            
            # 打印最终响应
            logger.debug("最终响应:")
            logger.debug(f"  状态码: {response.status_code}")
            logger.debug(f"  响应URL: {response.url}")
            logger.debug("  响应头:")
            for key, value in response.headers.items():
                logger.debug(f"    {key}: {value}")
        
        return response
        
    except requests.exceptions.RequestException as e:
        logger.error(f"请求失败: {e}")
        return None

# 定义解析命令行参数的函数
def parse_args():
    """
    解析命令行参数
    
    返回:
        args: 解析后的参数对象
    """
    parser = argparse.ArgumentParser(description="整合图片上传和表单提交功能的脚本")
    
    # 添加命令行参数
    parser.add_argument("-c", "--cookie", type=str, default=COOKIE_STRING, 
                      help="Cookie信息（字符串格式，只需要remember_student部分）")
    parser.add_argument("-i", "--image", type=str, default=IMAGE_PATH, 
                      help="要上传的图片路径")
    parser.add_argument("-d", "--data", type=str, default=FORM_DATA_B, 
                      help="表单数据（班级姓名信息）")
    parser.add_argument("--debug", action="store_true", default=DEBUG, 
                      help="启用调试模式")
    
    return parser.parse_args()

# 修改main函数以接受参数
def main(cookie=COOKIE_STRING, image_path=IMAGE_PATH, form_data_b=FORM_DATA_B, debug=DEBUG, course_url=COURSE_URL, default_form_data=DEFAULT_FORM_DATA):
    """
    主函数，整合图片上传和表单提交流程
    
    参数:
        cookie: Cookie信息（字符串格式，只需要remember_student部分）
        image_path: 图片本地路径
        form_data_b: 表单数据b（班级姓名信息）
        debug: 是否启用调试模式
        course_url: 课程页面URL（可选）
        default_form_data: 默认表单参数（可选）
    """
    # 使用传入的参数或默认值
    global COOKIE_STRING, IMAGE_PATH, FORM_DATA_B, DEBUG, COURSE_URL, DEFAULT_FORM_DATA
    COOKIE_STRING = cookie or COOKIE_STRING
    IMAGE_PATH = image_path or IMAGE_PATH
    FORM_DATA_B = form_data_b or FORM_DATA_B
    DEBUG = debug or DEBUG
    COURSE_URL = course_url or COURSE_URL
    DEFAULT_FORM_DATA = default_form_data or DEFAULT_FORM_DATA
    

    
    # 检查remember_student Cookie是否为空
    remember_cookie = COOKIE_STRING.strip()
    if not remember_cookie:
        logger.error("错误：Cookie配置为空，请在脚本顶部设置有效的COOKIE_STRING或使用--cookie参数")
        logger.info("提示：只需要输入 remember_student_xxxxx 部分即可")
        return
    
    # 检查是否已经包含s=部分
    if "s=" in remember_cookie and "remember_student" in remember_cookie:
        # 已经是完整的cookie字符串
        cookies = remember_cookie
    else:
        # 只包含remember_student部分，需要获取s=部分
        s_cookie = get_session_cookie(remember_cookie, course_url=COURSE_URL)
        
        # 合并两部分cookie
        if s_cookie:
            cookies = f"{remember_cookie}; {s_cookie}"
        else:
            # 如果获取不到s=部分，仍然使用remember_cookie尝试
            cookies = remember_cookie
            logger.warning("未获取到s=部分cookie，仅使用remember_student部分继续尝试")
    
    # 步骤3: 获取OSS上传密钥
    oss_config = get_oss_key(cookies, course_url=COURSE_URL)
    if not oss_config:
        return
    
    # 步骤4: 上传图片到OSS
    image_path = IMAGE_PATH
    
    # 处理相对路径
    if not os.path.isabs(image_path):
        image_path = os.path.abspath(image_path)
    
    file_info = upload_image_to_oss(oss_config, image_path)
    
    if not file_info:
        logger.error("图片上传失败，无法继续提交表单")
        return
    
    # 生成随机的_tms值
    random_tms = str(random.randint(1, 500))
    
    # 构建formdata[a] - 包含上传的图片信息
    formdata_a = [
        {
            # 网站默认的是附件1.png，这里保持一致
            "name": "附件1.png",
            "file": file_info['file'],
            "size": file_info['size'],
            "type": file_info['type']
        }
    ]
    
    # 转换为JSON字符串
    formdata_a_json = json.dumps(formdata_a)
    
    # 使用配置的formdata[b]值
    formdata_b = FORM_DATA_B
    
    # 构建完整的表单数据
    form_data = DEFAULT_FORM_DATA.copy()
    form_data.update({
        "formdata[a]": formdata_a_json,
        "formdata[b]": formdata_b,
        "_tms": random_tms
    })
    
    # 只在调试模式下打印详细配置
    if DEBUG:
        logger.debug("当前表单配置")
        logger.debug(f"表单数据: {json.dumps(form_data, indent=2, ensure_ascii=False)}")
        logger.debug(f"Cookie: {cookies}")
    
    # 直接提交表单（非交互式）
    response = submit_course_form(form_data, cookies, course_url=COURSE_URL)
    
    # 处理响应
    if response:
        # 检查是否有重定向历史
        has_redirect = any(hist.status_code in [302, 301] for hist in response.history)
        
        if has_redirect:
            # 如果有重定向，获取最后一个重定向的location
            last_redirect = response.history[-1]
        elif response.status_code == 200:
            # 检查响应内容是否包含失败信息
            response_text = response.text
            if "1分钟内只能提交1次" in response_text:
                logger.error("表单提交失败：操作过于频繁，1分钟内只能提交1次")
            elif "一天最多只能新增1份" in response_text or "明天再填吧" in response_text:
                logger.error("表单提交失败：该资料今日已提交，一天最多只能新增1份")
            elif "新增失败" in response_text:
                logger.error("表单提交失败：操作失败，请稍后重试")
    else:
        logger.error("表单提交失败")

if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()
    
    # 调用main函数
    main(cookie=args.cookie, image_path=args.image, form_data_b=args.data, debug=args.debug)
