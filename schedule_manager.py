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
        # 用于存储每个时间段已分配的时间点，实现智能分散
        self.time_slots = {}
        
    def _get_time_slot_key(self, start_time, end_time):
        """生成时间段的唯一标识键（包含日期，每天重置）"""
        today = datetime.now().date()
        return f"{today}_{start_time}_{end_time}"
    
    def _cleanup_old_time_slots(self):
        """清理过期的时间槽记录（保留今天的）"""
        today = datetime.now().date()
        keys_to_remove = []
        for key in self.time_slots.keys():
            # 键格式: YYYY-MM-DD_HH:MM_HH:MM
            try:
                key_date = datetime.strptime(key.split('_')[0], '%Y-%m-%d').date()
                if key_date < today:
                    keys_to_remove.append(key)
            except:
                pass
        
        for key in keys_to_remove:
            del self.time_slots[key]
            logger.debug(f"清理过期时间槽: {key}")
    
    def _allocate_time_slot(self, start_time, end_time, user_name, min_interval=30):
        """
        智能分配时间槽，确保同一时间段内的任务均匀分散
        
        参数:
            start_time: 开始时间 (HH:MM)
            end_time: 结束时间 (HH:MM)
            user_name: 用户名
            min_interval: 任务之间的最小间隔（秒）
            
        返回:
            datetime: 分配的执行时间
        """
        slot_key = self._get_time_slot_key(start_time, end_time)
        
        # 解析时间
        s_h, s_m = map(int, start_time.split(':'))
        e_h, e_m = map(int, end_time.split(':'))
        
        # 计算时间区间总秒数
        total_seconds = (e_h * 60 + e_m - s_h * 60 - s_m) * 60
        
        # 获取或初始化该时间段的时间槽
        if slot_key not in self.time_slots:
            self.time_slots[slot_key] = []
        
        allocated_slots = self.time_slots[slot_key]
        
        # 计算当前已分配的任务数
        current_count = len(allocated_slots)
        
        # 计算理想的时间间隔
        if current_count == 0:
            # 第一个任务：随机分配
            delay_seconds = random.randint(0, total_seconds)
        else:
            # 后续任务：尝试均匀分布
            # 将时间段分成 (current_count + 1) 个区间
            slot_size = total_seconds // (current_count + 1)
            
            # 为当前用户选择一个区间（优先选择间隔最大的区间）
            best_slot = 0
            max_gap = 0
            
            # 计算所有已有时间点
            sorted_slots = sorted(allocated_slots)
            
            # 检查每个可能的插入位置
            for i in range(current_count + 1):
                if i == 0:
                    # 第一个区间 [0, first_slot]
                    gap = sorted_slots[0] if sorted_slots else total_seconds
                elif i == current_count:
                    # 最后一个区间 [last_slot, total_seconds]
                    gap = total_seconds - sorted_slots[-1]
                else:
                    # 中间区间
                    gap = sorted_slots[i] - sorted_slots[i-1]
                
                if gap > max_gap:
                    max_gap = gap
                    best_slot = i
            
            # 在选中的区间内随机选择一个时间点
            if best_slot == 0:
                slot_start = 0
                slot_end = sorted_slots[0] if sorted_slots else slot_size
            elif best_slot == current_count:
                slot_start = sorted_slots[-1]
                slot_end = total_seconds
            else:
                slot_start = sorted_slots[best_slot - 1]
                slot_end = sorted_slots[best_slot]
            
            # 在区间内随机选择，但确保与相邻任务有最小间隔
            safe_start = slot_start + min_interval
            safe_end = slot_end - min_interval
            
            if safe_start < safe_end:
                delay_seconds = random.randint(safe_start, safe_end)
            else:
                # 如果区间太小，就在整个时间段内随机
                delay_seconds = random.randint(0, total_seconds)
        
        # 记录分配的时间点
        self.time_slots[slot_key].append(delay_seconds)
        
        # 计算实际的执行时间
        today = datetime.now().date()
        start_datetime = datetime(today.year, today.month, today.day, s_h, s_m, 0)
        run_time = start_datetime + timedelta(seconds=delay_seconds)
        
        logger.info(f"智能分配时间槽: 用户 {user_name} 分配到 {run_time.strftime('%H:%M:%S')} "
                   f"(区间 {start_time}-{end_time}, 当前该区间共 {len(self.time_slots[slot_key])} 个任务)")
        
        return run_time
        
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
        # 清理过期的时间槽记录
        self._cleanup_old_time_slots()
        
        data_dir = os.path.join(os.getcwd(), 'data')
        if not os.path.exists(data_dir):
            logger.warning("data目录不存在，无法加载用户配置")
            return

        # 获取当前所有"母任务"ID（排除掉正在排队的临时随机任务和reload任务）
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
                        
                        config['config_file'] = file_path
                        user_name = config.get('name', 'unknown')
                        job_id = f"user_{user_name}_{filename}"
                        new_job_ids.add(job_id)
                        
                        if schedule_enabled:
                            # 用户开启了定时任务
                            if job_id in current_job_ids:
                                self.update_user_job(job_id, config)
                            else:
                                self.add_user_job(job_id, config)
                                logger.info(f"为用户 {user_name} 添加定时任务")
                        else:
                            # 用户未开启定时任务，使用保底机制
                            self._add_fallback_job(job_id, config)
                            logger.info(f"为用户 {user_name} 添加保底任务（未开启定时任务）")
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
    
    def _add_fallback_job(self, job_id, user_config):
        """
        为未开启定时任务的用户添加保底任务
        
        保底任务在 20:00-21:00 区间内随机执行，确保用户不会错过提交
        使用智能时间分散算法，避免多个用户同时执行
        """
        try:
            # 保底任务在 20:00-21:00 区间内随机执行
            fallback_start_time = "20:00"
            fallback_end_time = "21:00"
            
            fallback_hour, fallback_minute = map(int, fallback_start_time.split(':'))
            
            # 默认每天执行
            trigger = CronTrigger(
                day_of_week='mon,tue,wed,thu,fri,sat,sun',
                hour=fallback_hour,
                minute=fallback_minute,
                timezone='Asia/Shanghai'
            )
            
            self.scheduler.add_job(
                func=self.run_user_task_within_range,
                trigger=trigger,
                args=[user_config],
                id=job_id,
                name=f"保底任务: {user_config.get('name', '未知')}",
                replace_existing=True
            )
            logger.info(f"添加保底任务成功: {job_id} (执行区间: {fallback_start_time}-{fallback_end_time})")
        except Exception as e:
            logger.error(f"添加保底任务失败: {e}")
            
    def update_user_job(self, job_id, user_config):
        """更新用户任务（支持定时任务和保底任务之间的切换）"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                schedule_enabled = user_config.get('schedule', {}).get('enabled', False)
                
                if schedule_enabled:
                    # 用户开启了定时任务
                    new_trigger = self._build_cron_trigger(user_config)
                    if str(job.trigger) != str(new_trigger):
                        self.scheduler.reschedule_job(job_id, trigger=new_trigger)
                        logger.info(f"更新任务为定时任务: {job_id}")
                else:
                    # 用户关闭了定时任务，切换为保底任务
                    self._add_fallback_job(job_id, user_config)
                    logger.info(f"更新任务为保底任务: {job_id}")
        except Exception as e:
            logger.error(f"更新用户任务失败: {e}")

    def run_user_task_within_range(self, user_config):
        """
        核心优化：在时间区间内预约一个随机执行点
        使用智能时间槽分配算法，确保同一时间段内的任务均匀分散
        不再使用 time.sleep，避免占用线程池
        
        对于保底任务（未开启定时任务），在 20:00-21:00 区间内随机执行
        """
        try:
            # 参数验证
            if not user_config or not isinstance(user_config, dict):
                logger.error("无效的用户配置")
                return
            
            schedule_info = user_config.get('schedule', {})
            schedule_enabled = schedule_info.get('enabled', False)
            
            # 保底任务：在 20:00-21:00 区间内随机执行
            if not schedule_enabled:
                user_name = user_config.get('name', 'unknown')
                fallback_start_time = "20:00"
                fallback_end_time = "21:00"
                
                # 使用智能时间槽分配算法
                run_time = self._allocate_time_slot(fallback_start_time, fallback_end_time, user_name, min_interval=60)
                
                # 添加一个临时的一次性任务 ID
                exec_job_id = f"exec_{user_name}_{int(run_time.timestamp())}"
                
                self.scheduler.add_job(
                    func=self.run_user_task,
                    trigger=DateTrigger(run_date=run_time, timezone='Asia/Shanghai'),
                    args=[user_config, exec_job_id],
                    id=exec_job_id,
                    name=f"保底随机执行: {user_name}",
                    replace_existing=True
                )
                logger.info(f"保底任务已预约：用户 {user_name} 将在 {run_time.strftime('%H:%M:%S')} 执行")
                return
            
            # 定时任务：在时间区间内随机执行
            start_time = schedule_info.get('start_time', '08:00')
            end_time = schedule_info.get('end_time', '09:00')
            
            s_h, s_m = map(int, start_time.split(':'))
            e_h, e_m = map(int, end_time.split(':'))
            total_minutes = (e_h * 60 + e_m) - (s_h * 60 + s_m)
            
            # 限制时间区间最大值为1小时（60分钟）
            max_minutes = 60
            if total_minutes > max_minutes:
                logger.warning(f"时间区间过长（{total_minutes}分钟），已限制为{max_minutes}分钟")
                total_minutes = max_minutes
            
            if total_minutes <= 0:
                # 开始时间和结束时间相同，在固定时间点执行
                user_name = user_config.get('name', 'unknown')
                today = datetime.now().date()
                run_time = datetime(today.year, today.month, today.day, s_h, s_m, 0)
                
                # 添加一个临时的一次性任务 ID
                exec_job_id = f"exec_{user_name}_{int(run_time.timestamp())}"
                
                self.scheduler.add_job(
                    func=self.run_user_task,
                    trigger=DateTrigger(run_date=run_time, timezone='Asia/Shanghai'),
                    args=[user_config, exec_job_id],
                    id=exec_job_id,
                    name=f"固定时间执行: {user_name}",
                    replace_existing=True
                )
                logger.info(f"固定时间任务已预约：用户 {user_name} 将在 {run_time.strftime('%H:%M:%S')} 执行")
                return
            
            # 使用智能时间槽分配算法
            user_name = user_config.get('name', 'unknown')
            run_time = self._allocate_time_slot(start_time, end_time, user_name, min_interval=60)
            
            # 添加一个临时的一次性任务 ID
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