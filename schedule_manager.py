#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Name: schedule_manager.py
About: 定时任务管理器，使用Flask-APScheduler实现
Author: LynxFrost (Optimized)

功能：
1. 读取用户配置文件中的定时任务设置
2. 管理定时任务的执行（支持区间内随机执行）
3. 支持动态添加、删除、修改任务
4. 提供任务状态监控
"""

import os
import json
import logging
import random
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入主工作流模块
import run_workflow

class ScheduleManager:
    def __init__(self):
        self.scheduler = None
        self.job_ids = set()
        
    def init_scheduler(self):
        """初始化调度器"""
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(20)
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 5,
            'misfire_grace_time': 600
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Shanghai'
        )
        logger.info("调度器初始化完成")
        
    def start(self):
        """启动调度器"""
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            logger.info("调度器已启动")
            
            # 初始加载用户配置
            self.load_user_configs()
            
            # 添加定时重新加载配置的任务（每小时）
            self.scheduler.add_job(
                func=self.load_user_configs,
                trigger='interval',
                minutes=60,
                id='reload_configs',
                replace_existing=True
            )
            logger.info("已设置每小时重新加载配置的任务")
            
    def stop(self):
        """停止调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("调度器已停止")
            
    def load_user_configs(self):
        """加载所有用户配置并更新定时任务"""
        data_dir = os.path.join(os.getcwd(), 'data')
        if not os.path.exists(data_dir):
            logger.warning("data目录不存在，无法加载用户配置")
            return

        # 获取当前所有“母任务”ID（排除掉正在排队的临时随机任务和reload任务）
        current_job_ids = set(job.id for job in self.scheduler.get_jobs() 
                            if not job.id.startswith('exec_') and job.id != 'reload_configs')
        
        new_job_ids = set()
        
        files = os.listdir(data_dir)
        for filename in files:
            if filename.endswith('.json'):
                file_path = os.path.join(data_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        schedule_enabled = config.get('schedule', {}).get('enabled', False)
                        
                        if schedule_enabled:
                            config['config_file'] = file_path
                            user_name = config.get('name', 'unknown')
                            job_id = f"user_{user_name}_{filename}"
                            new_job_ids.add(job_id)
                            
                            if job_id in current_job_ids:
                                self.update_user_job(job_id, config)
                            else:
                                self.add_user_job(job_id, config)
                except Exception as e:
                    logger.error(f"加载配置文件 {filename} 失败: {e}")
        
        # 删除不再需要的母任务
        jobs_to_remove = current_job_ids - new_job_ids
        for job_id in jobs_to_remove:
            try:
                self.scheduler.remove_job(job_id)
                logger.info(f"已删除任务: {job_id}")
            except Exception as e:
                logger.error(f"删除任务 {job_id} 失败: {e}")
        
        self.job_ids = new_job_ids
        logger.info(f"当前活跃母任务数: {len(new_job_ids)}")

    def _build_cron_trigger(self, user_config):
        """内部工具：根据用户配置构建Cron触发器"""
        schedule_info = user_config.get('schedule', {})
        start_time = schedule_info.get('start_time', '08:00')
        exec_days = schedule_info.get('days', [1, 2, 3, 4, 5, 6, 7])
        
        start_hour, start_minute = map(int, start_time.split(':'))
        day_map = {1:'mon', 2:'tue', 3:'wed', 4:'thu', 5:'fri', 6:'sat', 7:'sun'}
        days_of_week = [day_map.get(day) for day in exec_days if day in day_map]
        
        return CronTrigger(
            day_of_week=','.join(days_of_week),
            hour=start_hour,
            minute=start_minute,
            timezone='Asia/Shanghai'
        )

    def add_user_job(self, job_id, user_config):
        """添加用户任务"""
        try:
            trigger = self._build_cron_trigger(user_config)
            self.scheduler.add_job(
                func=self.run_user_task_within_range,
                trigger=trigger,
                args=[user_config],
                id=job_id,
                name=f"母任务: {user_config.get('name', '未知')}",
                replace_existing=True
            )
            logger.info(f"添加任务成功: {job_id}")
        except Exception as e:
            logger.error(f"添加用户任务失败: {e}")
            
    def update_user_job(self, job_id, user_config):
        """更新用户任务"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                new_trigger = self._build_cron_trigger(user_config)
                if str(job.trigger) != str(new_trigger):
                    self.scheduler.reschedule_job(job_id, trigger=new_trigger)
                    logger.info(f"更新任务触发器: {job_id}")
        except Exception as e:
            logger.error(f"更新用户任务失败: {e}")

    def run_user_task_within_range(self, user_config):
        """
        核心优化：在时间区间内预约一个随机执行点
        不再使用 time.sleep，避免占用线程池
        """
        try:
            # 参数验证
            if not user_config or not isinstance(user_config, dict):
                logger.error("无效的用户配置")
                return
            
            schedule_info = user_config.get('schedule', {})
            start_time = schedule_info.get('start_time', '08:00')
            end_time = schedule_info.get('end_time', '09:00')
            
            s_h, s_m = map(int, start_time.split(':'))
            e_h, e_m = map(int, end_time.split(':'))
            total_minutes = (e_h * 60 + e_m) - (s_h * 60 + s_m)
            
            # 限制时间区间最大值为2小时（120分钟）
            max_minutes = 120
            if total_minutes > max_minutes:
                logger.warning(f"时间区间过长（{total_minutes}分钟），已限制为{max_minutes}分钟")
                total_minutes = max_minutes
            
            if total_minutes <= 0:
                # 区间无效则立即执行
                self.run_user_task(user_config)
                return
            
            # 计算当天的开始时间点
            today = datetime.now().date()
            start_datetime = datetime(today.year, today.month, today.day, s_h, s_m, 0)
            
            # 计算随机延迟并预约
            delay_seconds = random.randint(0, total_minutes * 60)
            run_time = start_datetime + timedelta(seconds=delay_seconds)
            
            # 添加一个临时的一次性任务 ID
            user_name = user_config.get('name', 'unknown')
            exec_job_id = f"exec_{user_name}_{int(run_time.timestamp())}"
            
            self.scheduler.add_job(
                func=self.run_user_task,
                trigger=DateTrigger(run_date=run_time, timezone='Asia/Shanghai'),
                args=[user_config, exec_job_id],
                id=exec_job_id,
                name=f"随机执行: {user_name}",
                replace_existing=True
            )
            logger.info(f"任务已预约：用户 {user_name} 将在 {run_time.strftime('%H:%M:%S')} 执行")
            
        except Exception as e:
            logger.error(f"预约随机任务失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def run_user_task(self, user_config, exec_job_id=None):
        """真正执行业务工作流"""
        try:
            user_name = user_config.get('name', '未知用户')
            logger.info(f"开始执行工作流: {user_name}")
            import argparse
            args = argparse.Namespace(
                json=user_config['config_file'],
                folder=None, cookie=None, name=None, username=None,
                avatar=None, course_url=None, form_data=None
            )
            run_workflow.main(args)
            logger.info(f"工作流执行完成: {user_name}")
        except Exception as e:
            logger.error(f"工作流运行异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # 清理临时任务
            if exec_job_id:
                try:
                    self.scheduler.remove_job(exec_job_id)
                    logger.info(f"已清理临时任务: {exec_job_id}")
                except Exception as e:
                    logger.warning(f"清理临时任务失败: {e}")

    def get_jobs_info(self):
        """获取所有任务信息"""
        jobs_info = []
        for job in self.scheduler.get_jobs():
            if job.id != 'reload_configs':
                jobs_info.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
        return jobs_info
        
    def get_job_info(self, job_id):
        """获取指定任务信息"""
        job = self.scheduler.get_job(job_id)
        if job:
            return {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            }
        return None

# 全局单例
schedule_manager = ScheduleManager()

def start_scheduler():
    schedule_manager.init_scheduler()
    schedule_manager.start()

def get_schedule_manager():
    return schedule_manager

if __name__ == "__main__":
    manager = ScheduleManager()
    manager.init_scheduler()
    manager.start()
    
    try:
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        manager.stop()