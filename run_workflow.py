#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Name: run_workflow.py
About: 程序主文件，用于生成Keep跑步截图并且上传到提交系统
Author: LynxFrost
AuthorBlog: https://blog.itrf.cn

功能：
1. 读取参数（支持命令行参数或JSON配置文件，支持多用户）
2. 执行KeepSultan.py生成跑步截图
3. 将生成的图片上传到提交系统
4. 成功后删除生成的图片
5. 支持批量处理多个用户

使用方法：

1. 使用命令行参数（单用户）：
   python run_workflow.py -c "YOUR_COOKIE" -n "备注" --username "keep用户名"

2. 使用单用户JSON配置文件：
   python run_workflow.py --json user_config.json

3. 使用多用户JSON配置文件：
   python run_workflow.py --json config_multi_user.json

4. 混合使用（命令行参数优先，仅影响第一个用户）：
   python run_workflow.py --json config_multi_user.json -c "OVERRIDE_COOKIE"

"""

import argparse
import datetime
import os
import logging
import sys
import importlib.util

# 确保当前目录在Python路径中
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 动态导入模块
def import_module(name, file_path):
    """动态导入模块"""
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

# 导入需要的模块
try:
    KeepSultan = import_module("KeepSultan", "KeepSultan.py")
    integrated_script = import_module("integrated_script", "integrated_script.py")
except Exception as e:
    logging.error(f"导入模块失败: {e}")
    sys.exit(1)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_args():
    """
    解析命令行参数
    
    返回:
        args: 解析后的参数对象
    """
    parser = argparse.ArgumentParser(description="运行KeepSultan工作流")
    
    # 添加JSON配置文件参数
    parser.add_argument("-j", "--json", type=str, 
                      help="JSON配置文件路径，用于读取参数")
    
    # 添加命令行参数
    parser.add_argument("-c", "--cookie", type=str, 
                      help="账号Cookie")
    parser.add_argument("-n", "--name", type=str, 
                      help="提交备注")
    parser.add_argument("--username", type=str, default="", 
                      help="Keep用户名")
    
    return parser.parse_args()


def read_json_config(json_path):
    """
    从JSON文件读取配置参数
    
    参数:
        json_path: JSON配置文件路径
        
    返回:
        list: 用户配置数组（单用户或多用户）
        None: 如果读取失败
    """
    try:
        import json
        
        with open(json_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查是否是多用户配置
        if 'users' in config and isinstance(config['users'], list):
            users = config['users']
            logger.info(f"成功从JSON文件读取 {len(users)} 个用户配置: {json_path}")
            return users
        else:
            # 单用户配置，转换为数组格式
            logger.info(f"成功从JSON文件读取单用户配置: {json_path}")
            return [config]
    except FileNotFoundError:
        logger.error(f"JSON配置文件不存在: {json_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON配置文件格式错误: {e}")
        return None
    except Exception as e:
        logger.error(f"读取JSON配置文件失败: {e}")
        return None


def get_config_from_args(args):
    """
    从命令行参数和JSON配置文件获取最终配置
    
    参数:
        args: 命令行参数对象
        
    返回:
        list: 用户配置数组（单用户或多用户）
        None: 如果配置不完整或错误
    """
    # 1. 处理命令行参数（如果有）
    has_cli_args = args.cookie or args.name
    
    # 2. 从JSON文件读取配置（如果提供）
    users_config = None
    if args.json:
        users_config = read_json_config(args.json)
        if not users_config:
            return None
    
    # 3. 确定最终的用户配置数组
    if has_cli_args:
        # 有命令行参数，只处理单用户情况
        user_config = {}
        
        # 如果有JSON配置，使用第一个用户的配置作为基础
        if users_config and users_config:
            user_config.update(users_config[0])
        
        # 用命令行参数覆盖
        if args.cookie:
            user_config['cookie'] = args.cookie
        if args.name:
            user_config['name'] = args.name
        if args.username:
            user_config['username'] = args.username
        
        # 检查必要的参数
        if 'cookie' not in user_config or 'name' not in user_config:
            logger.error("缺少必要参数: cookie和name必须提供（通过命令行或JSON文件）")
            return None
        
        # 设置默认值
        if 'username' not in user_config:
            user_config['username'] = ''
        
        logger.info(f"最终配置: cookie={'*' * len(user_config['cookie'])}, name={user_config['name']}, username={user_config['username']}")
        return [user_config]
    else:
        # 没有命令行参数，使用JSON配置
        if not users_config:
            logger.error("缺少配置: 必须提供JSON配置文件或命令行参数")
            return None
        
        # 验证每个用户的配置
        valid_users = []
        for i, user_config in enumerate(users_config):
            # 检查必要的参数
            if 'cookie' not in user_config or 'name' not in user_config:
                logger.error(f"用户 {i+1} 缺少必要参数: cookie和name必须提供")
                continue
            
            # 设置默认值
            if 'username' not in user_config:
                user_config['username'] = ''
            
            valid_users.append(user_config)
        
        if not valid_users:
            logger.error("没有有效的用户配置")
            return None
        
        logger.info(f"最终配置: {len(valid_users)} 个有效用户")
        for i, user_config in enumerate(valid_users):
            # logger.info(f"用户 {i+1}: name={user_config['name']}, username={user_config['username']}, cookie={user_config['cookie']}")
            logger.info(f"用户 {i+1}: name={user_config['name']}, username={user_config['username']}, cookie=保密")
        
        return valid_users


def run_keepsultan(output_dir="images", username=""):
    """
    执行KeepSultan.py生成跑步截图
    
    参数:
        output_dir: 输出目录
        username: Keep用户名
        
    返回:
        str: 生成的图片路径
        None: 如果生成失败
    """
    try:
        # 生成带时间戳的文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"keep_run_{timestamp}.png")
        
        logger.info(f"执行KeepSultan生成图片: {output_path}")
        
        # 使用KeepSultan模块直接生成图片
        try:
            # 构建参数命名空间
            import argparse
            args = argparse.Namespace(
                config="config.json",
                save=output_path,
                template=None,
                map=None,
                avatar=None,
                username=username,
                date=None,
                end_time=None,
                seed=None
            )
            
            # 设置随机种子（如果有）
            if args.seed is not None:
                import random
                random.seed(args.seed)
            
            # 加载配置
            cfg = KeepSultan.KeepConfig.from_json(args.config)
            
            # 应用覆盖参数
            cfg = KeepSultan.apply_overrides(cfg, args)
            
            # 创建应用实例并处理
            app = KeepSultan.KeepSultanApp(cfg)
            app.process()
            app.save(args.save)
            
            logger.info(f"图片生成成功: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"KeepSultan内部错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    except Exception as e:
        logger.error(f"执行KeepSultan时发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def run_integrated_script(cookie, image_path, form_data_b):
    """
    执行integrated_script.py上传图片并提交表单
    
    参数:
        cookie: Cookie信息
        image_path: 要上传的图片路径
        form_data_b: 班级姓名信息
        
    返回:
        bool: 是否执行成功
    """
    try:
        logger.info(f"执行integrated_script上传图片: {image_path}")
        
        # 直接调用integrated_script模块的main函数
        try:
            # 保存原始的全局变量值
            original_cookie = integrated_script.COOKIE_STRING
            original_image = integrated_script.IMAGE_PATH
            original_form_data = integrated_script.FORM_DATA_B
            original_debug = integrated_script.DEBUG
            
            try:
                # 设置全局变量
                integrated_script.COOKIE_STRING = cookie
                integrated_script.IMAGE_PATH = image_path
                integrated_script.FORM_DATA_B = form_data_b
                integrated_script.DEBUG = False
                
                # 调用main函数
                result = integrated_script.main(
                    cookie=cookie,
                    image_path=image_path,
                    form_data_b=form_data_b,
                    debug=False
                )
                
                # integrated_script.main没有返回值，成功执行就返回True
                logger.info("图片上传和表单提交成功")
                return True
            finally:
                # 恢复原始的全局变量值
                integrated_script.COOKIE_STRING = original_cookie
                integrated_script.IMAGE_PATH = original_image
                integrated_script.FORM_DATA_B = original_form_data
                integrated_script.DEBUG = original_debug
        except Exception as e:
            logger.error(f"integrated_script内部错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    except Exception as e:
        logger.error(f"执行integrated_script时发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """
    主函数，运行完整工作流
    """
    # 解析命令行参数
    args = parse_args()
    
    # 获取最终配置（从JSON文件和命令行参数）
    users_config = get_config_from_args(args)
    if not users_config:
        logger.error("配置获取失败，无法继续执行")
        return
    
    logger.info(f"开始执行KeepSultan工作流，共处理 {len(users_config)} 个用户")
    
    # 跟踪执行结果
    success_count = 0
    failed_count = 0
    
    # 循环处理每个用户
    for i, user_config in enumerate(users_config):
        user_index = i + 1
        logger.info(f"\n{'='*60}")
        logger.info(f"开始处理用户 {user_index}/{len(users_config)}: {user_config['name']}")
        logger.info(f"{'='*60}")
        
        try:
            # 步骤1: 生成跑步截图
            image_path = run_keepsultan(
                username=user_config['username']
            )
            
            if not image_path:
                logger.error(f"用户 {user_index} 工作流失败: 图片生成失败")
                failed_count += 1
                continue
            
            # 步骤2: 上传图片并提交表单
            success = run_integrated_script(
                cookie=user_config['cookie'],
                image_path=image_path,
                form_data_b=user_config['name']
            )
            
            if success:
                try:
                    # 删除生成的图片
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        logger.info(f"用户 {user_index} 已删除生成的图片: {image_path}")
                    logger.info(f"用户 {user_index} 工作流执行完成")
                    success_count += 1
                except Exception as e:
                    logger.warning(f"用户 {user_index} 删除图片失败: {e}")
                    logger.info(f"用户 {user_index} 工作流执行完成，但图片删除失败")
                    success_count += 1
            else:
                logger.error(f"用户 {user_index} 工作流失败: 图片上传或表单提交失败")
                failed_count += 1
        except Exception as e:
            logger.error(f"用户 {user_index} 工作流异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            failed_count += 1
    
    # 输出汇总信息
    logger.info(f"\n{'='*60}")
    logger.info(f"工作流执行完成")
    logger.info(f"总用户数: {len(users_config)}")
    logger.info(f"成功: {success_count}")
    logger.info(f"失败: {failed_count}")
    logger.info(f"\n{'='*60}")


if __name__ == "__main__":
    main()
