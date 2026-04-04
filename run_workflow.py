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
   python run_workflow.py -c "YOUR_COOKIE" -n "备注" --username "keep用户名" --avatar "头像路径或URL"

2. 使用单用户JSON配置文件：
   python run_workflow.py --json user_config.json

3. 使用多用户JSON配置文件：
   python run_workflow.py --json config_multi_user.json


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

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入需要的模块
try:
    KeepSultan = import_module("KeepSultan", "KeepSultan.py")
    integrated_script = import_module("integrated_script", "integrated_script.py")
    # 导入map模块用于生成地图
    import map
    logger.info("map模块导入成功")
except Exception as e:
    logger.error(f"导入模块失败: {e}")
    sys.exit(1)


def parse_args():
    """
    解析命令行参数
    
    返回:
        args: 解析后的参数对象
    """
    parser = argparse.ArgumentParser(description="运行KeepSultan工作流")
    
    # 添加配置源参数（互斥）
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument("-j", "--json", type=str, 
                             help="JSON配置文件路径，用于读取参数")
    config_group.add_argument("-f", "--folder", type=str, 
                             help="包含JSON配置文件的文件夹路径")
    
    # 添加命令行参数
    parser.add_argument("-c", "--cookie", type=str, 
                      help="账号Cookie")
    parser.add_argument("-n", "--name", type=str, 
                      help="提交备注")
    parser.add_argument("-u", "--username", type=str, default="用户", 
                      help="Keep用户名")
    parser.add_argument("-a", "--avatar", type=str, default="src/avatar.png", 
                      help="Keep头像URL或路径(可选)")
    parser.add_argument("--course-url", type=str, 
                      help="课程页面URL(可选，覆盖默认值)")
    parser.add_argument("--form-data", type=str, 
                      help="默认表单参数JSON字符串(可选，覆盖默认值)")
    
    return parser.parse_args()


def generate_new_map(output_dir="src/map", map_name=None):
    """
    生成新的Keep风格地图并保存到指定目录
    
    参数:
        output_dir: 输出目录，默认是src/map
        map_name: 地图文件名，None则生成带时间戳的文件名
        
    返回:
        str: 生成的地图图片路径
        None: 如果生成失败
    """
    try:
        # 生成带时间戳的文件名（包含微秒，确保多线程环境下唯一性）
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        if map_name is None:
            map_name = f"keep_map_{timestamp}.png"
        
        output_path = os.path.join(output_dir, map_name)
        
        logger.info(f"开始生成新地图: {output_path}")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 使用map模块生成地图
        generated_map = map.generate_keep_style_path(
            bg_path="src/map1.png",
            path_mask_path="src/map2.png",
            sample_rate=5,  # 提高采样率，减少处理点数
            max_steps=3000,  # 限制最大步数
            completion_threshold=0.2,  # 降低完成度阈值
            target_length=400  # 限制路径长度
        )
        
        # 保存生成的地图
        generated_map.save(output_path)
        logger.info(f"新地图生成成功: {output_path}")
        
        return output_path
    except Exception as e:
        logger.error(f"生成新地图失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def read_json_config(json_path):
    """
    从JSON文件读取配置参数
    
    参数:
        json_path: JSON配置文件路径
        
    返回:
        tuple: (用户配置数组, 全局配置字典) 或 (None, None) 如果读取失败
    """
    try:
        import json
        
        with open(json_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 初始化返回值
        users = []
        global_config = {}
        
        # 提取全局配置（如果有）
        if 'global_config' in config and isinstance(config['global_config'], dict):
            global_config = config['global_config']
            logger.info(f"成功从JSON文件读取全局配置")
        
        # 检查是否是多用户配置
        if 'users' in config and isinstance(config['users'], list):
            users = config['users']
            logger.info(f"成功从JSON文件读取 {len(users)} 个用户配置: {json_path}")
        else:
            # 单用户配置，转换为数组格式
            users = [config]
            logger.info(f"成功从JSON文件读取单用户配置: {json_path}")
        
        return users, global_config
    except FileNotFoundError:
        logger.error(f"JSON配置文件不存在: {json_path}")
        return None, None
    except json.JSONDecodeError as e:
        logger.error(f"JSON配置文件格式错误: {e}")
        return None, None
    except Exception as e:
        logger.error(f"读取JSON配置文件失败: {e}")
        return None, None


def get_config_from_args(args):
    """
    从命令行参数和JSON配置文件获取最终配置
    
    参数:
        args: 命令行参数对象
        
    返回:
        tuple: (用户配置数组, 全局配置字典) 或 (None, None) 如果配置不完整或错误
    """
    # 1. 处理命令行参数（如果有）
    has_cli_args = args.cookie or args.name
    
    # 2. 处理全局命令行参数
    global_config = {}
    if args.course_url:
        global_config['course_url'] = args.course_url
    if args.form_data:
        try:
            import json
            global_config['default_form_data'] = json.loads(args.form_data)
        except json.JSONDecodeError as e:
            logger.error(f"表单参数JSON解析错误: {e}")
            return None, None
    
    # 3. 从JSON文件或文件夹读取配置（如果提供）
    users_config = []
    json_global_config = {}
    
    if args.json:
        # 从单个JSON文件读取配置
        single_users_config, single_json_global_config = read_json_config(args.json)
        if not single_users_config:
            return None, None
        users_config = single_users_config
        json_global_config = single_json_global_config
    
    elif args.folder:
        # 从文件夹读取所有JSON配置文件
        import glob
        
        # 获取文件夹下所有JSON文件
        json_files = glob.glob(os.path.join(args.folder, "*.json"))
        
        if not json_files:
            logger.error(f"文件夹 {args.folder} 中没有JSON文件")
            return None, None
        
        logger.info(f"从文件夹 {args.folder} 中找到 {len(json_files)} 个JSON配置文件")
        
        # 读取每个JSON文件
        for json_file in json_files:
            try:
                file_users_config, file_global_config = read_json_config(json_file)
                if file_users_config:
                    # 添加用户配置
                    users_config.extend(file_users_config)
                    
                    # 合并全局配置（如果有）
                    for key, value in file_global_config.items():
                        if key not in json_global_config:
                            json_global_config[key] = value
                    
                    logger.info(f"成功读取配置文件: {os.path.basename(json_file)}")
                else:
                    logger.warning(f"跳过无效的配置文件: {os.path.basename(json_file)}")
            except Exception as e:
                logger.error(f"读取配置文件 {os.path.basename(json_file)} 时发生错误: {e}")
                continue
        
        if not users_config:
            logger.error("没有从文件夹中读取到有效的用户配置")
            return None, None
    
    # 合并全局配置，命令行参数优先
    for key, value in json_global_config.items():
        if key not in global_config:
            global_config[key] = value
    
    if json_global_config:
        logger.info(f"合并后的全局配置: {global_config}")
    
    # 4. 确定最终的用户配置数组
    if has_cli_args:
        # 有命令行参数，只处理单用户情况
        user_config = {}
        
        # 如果有从文件或文件夹读取的配置，使用第一个用户的配置作为基础
        if users_config:
            user_config.update(users_config[0])
        
        # 用命令行参数覆盖
        if args.cookie:
            user_config['cookie'] = args.cookie
        if args.name:
            user_config['name'] = args.name
        if args.username:
            user_config['username'] = args.username
        if args.avatar:
            user_config['avatar'] = args.avatar
        
        # 检查必要的参数
        if 'cookie' not in user_config or 'name' not in user_config:
            logger.error("缺少必要参数: cookie和name必须提供（通过命令行或配置文件）")
            return None, None
        
        # 设置默认值
        if 'username' not in user_config:
            user_config['username'] = ''
        
        logger.info(f"最终配置: cookie={'*' * len(user_config['cookie'])}, name={user_config['name']}, username={user_config['username']}")
        return [user_config], global_config
    else:
        # 没有命令行参数，使用从文件或文件夹读取的配置
        if not users_config:
            logger.error("缺少配置: 必须提供JSON配置文件、配置文件夹或命令行参数")
            return None, None
        
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
            return None, None
        
        logger.info(f"最终配置: {len(valid_users)} 个有效用户")
        for i, user_config in enumerate(valid_users):
            logger.info(f"用户 {i+1}: name={user_config['name']}, username={user_config['username']}, cookie=保密")
        
        return valid_users, global_config


def run_keepsultan(output_dir="images", username="", avatar=None, generate_new_map_flag=True):
    """
    执行KeepSultan.py生成跑步截图
    
    参数:
        output_dir: 输出目录
        username: Keep用户名
        avatar: 头像图片路径或URL（可选）
        generate_new_map_flag: 是否生成新地图，默认为True
        
    返回:
        tuple: (生成的图片路径, 生成的地图路径)
        None: 如果生成失败
    """
    try:
        # 生成带时间戳的文件名（包含微秒，确保多线程环境下唯一性）
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_path = os.path.join(output_dir, f"keep_run_{timestamp}.png")
        
        logger.info(f"执行KeepSultan生成图片: {output_path}")
        
        selected_map = None
        generated_map_path = None
        
        # 生成新地图或随机选择现有地图
        if generate_new_map_flag:
            # 生成新地图
            generated_map_path = generate_new_map()
            if generated_map_path:
                selected_map = generated_map_path
                logger.info(f"使用新生成的地图: {selected_map}")
            else:
                logger.warning("新地图生成失败，将尝试使用现有地图")
        
        # 如果没有生成新地图或生成失败，则随机选择现有地图
        if not selected_map:
            import random
            import glob
            
            # 扫描src/map目录中的所有图片文件
            map_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "map")
            map_files = glob.glob(os.path.join(map_dir, "*.png")) + glob.glob(os.path.join(map_dir, "*.jpg")) + glob.glob(os.path.join(map_dir, "*.jpeg"))
            
            # 随机选择一张地图图片，如果没有则使用None（使用默认值）
            selected_map = random.choice(map_files) if map_files else None
            if selected_map:
                logger.info(f"随机选择地图图片: {selected_map}")
                generated_map_path = None  # 不是生成的地图，不需要删除
        
        # 使用KeepSultan模块直接生成图片
        try:
            # 构建参数命名空间
            import argparse
            args = argparse.Namespace(
                config="config.json",
                save=output_path,
                template=None,
                map=selected_map,
                avatar=avatar,
                username=username,
                date=None,
                end_time=None,
                seed=None,
                location=None,
                weather=None,
                temperature=None,
                map_bg_path=None,
                map_mask_path=None
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
            return output_path, generated_map_path
        except Exception as e:
            logger.error(f"KeepSultan内部错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None, None
    except Exception as e:
        logger.error(f"执行KeepSultan时发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None


def run_integrated_script(cookie, image_path, form_data_b, course_url=None, default_form_data=None):
    """
    执行integrated_script.py上传图片并提交表单
    
    参数:
        cookie: Cookie信息
        image_path: 要上传的图片路径
        form_data_b: 班级姓名信息
        course_url: 课程页面URL（可选，覆盖默认值）
        default_form_data: 默认表单参数（可选，覆盖默认值）
        
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
            original_course_url = integrated_script.COURSE_URL
            original_default_form_data = integrated_script.DEFAULT_FORM_DATA
            
            try:
                # 设置全局变量
                integrated_script.COOKIE_STRING = cookie
                integrated_script.IMAGE_PATH = image_path
                integrated_script.FORM_DATA_B = form_data_b
                integrated_script.DEBUG = False
                if course_url:
                    integrated_script.COURSE_URL = course_url
                if default_form_data:
                    integrated_script.DEFAULT_FORM_DATA = default_form_data
                
                # 调用main函数
                kwargs = {
                    'cookie': cookie,
                    'image_path': image_path,
                    'form_data_b': form_data_b,
                    'debug': False
                }
                if course_url:
                    kwargs['course_url'] = course_url
                if default_form_data:
                    kwargs['default_form_data'] = default_form_data
                    
                result = integrated_script.main(**kwargs)
                
                # integrated_script.main没有返回值，成功执行就返回True
                logger.info("图片上传和表单提交成功")
                return True
            finally:
                # 恢复原始的全局变量值
                integrated_script.COOKIE_STRING = original_cookie
                integrated_script.IMAGE_PATH = original_image
                integrated_script.FORM_DATA_B = original_form_data
                integrated_script.DEBUG = original_debug
                integrated_script.COURSE_URL = original_course_url
                integrated_script.DEFAULT_FORM_DATA = original_default_form_data
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


def main(args=None):
    """
    主函数，运行完整工作流
    
    参数:
        args: 可选，命令行参数对象。如果不提供，将从命令行解析
    """
    # 解析命令行参数
    if args is None:
        args = parse_args()
    
    # 获取最终配置（从JSON文件和命令行参数）
    users_config, global_config = get_config_from_args(args)
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
            image_path, generated_map_path = run_keepsultan(
                username=user_config['username'],
                avatar=user_config.get('avatar')
            )
            
            if not image_path:
                logger.error(f"用户 {user_index} 工作流失败: 图片生成失败")
                failed_count += 1
                continue
            
            # 步骤2: 上传图片并提交表单
            # 使用用户单独配置（如果有），否则使用全局配置
            user_course_url = user_config.get('course_url', global_config.get('course_url'))
            user_form_data = user_config.get('default_form_data', global_config.get('default_form_data'))
            
            success = run_integrated_script(
                cookie=user_config['cookie'],
                image_path=image_path,
                form_data_b=user_config['name'],
                course_url=user_course_url,
                default_form_data=user_form_data
            )
            
            if success:
                try:
                    # 删除生成的图片
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        logger.info(f"用户 {user_index} 已删除生成的跑步截图: {image_path}")
                    
                    # 删除生成的地图（如果有）
                    if generated_map_path and os.path.exists(generated_map_path):
                        os.remove(generated_map_path)
                        logger.info(f"用户 {user_index} 已删除生成的地图: {generated_map_path}")
                    
                    logger.info(f"用户 {user_index} 工作流执行完成")
                    success_count += 1
                except Exception as e:
                    logger.warning(f"用户 {user_index} 删除文件失败: {e}")
                    logger.info(f"用户 {user_index} 工作流执行完成，但文件删除失败")
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
