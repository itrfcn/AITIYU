# 爱体育自动化工作流

## 项目简介

- 爱体育自动化工作流是一个用于自动生成跑步截图并自动上传到提交系统的工具，支持多用户批量处理。
- 本项目的主要功能是生成keep跑步截图并自动提交到班级魔方。
- 写这个项目的初衷是为了方便自己完成每个学期的跑步任务。
- 现已支持Web界面和定时任务功能，提供更便捷的用户体验。

## 功能特点

1. **自动路径生成**：通过 `map.py` 自动生成Keep风格的运动轨迹路径，支持路径平滑处理
2. **自动生成跑步截图**：通过 `KeepSultan.py` 生成模拟的跑步运动截图
3. **自动上传提交系统**：通过 `integrated_script.py` 将生成的图片上传到指定提交系统
4. **多用户批量处理**：支持通过 JSON 配置文件批量处理多个用户，每个用户可单独配置参数
5. **文件夹批量处理**：支持读取指定文件夹下的所有JSON配置文件，实现批量任务管理
6. **灵活的参数配置**：支持命令行参数或 JSON 配置文件，支持参数覆盖，配置优先级：命令行参数 > 用户单独配置 > 全局配置 > 代码默认值
7. **自动清理**：上传成功后自动删除生成的图片和地图文件，避免磁盘占用
8. **Cookie保活**：通过有效期5年的Cookie，自动获取有效期只有2小时的Cookie，确保Cookie有效
9. **详细的日志记录**：执行过程中生成详细的日志信息，便于调试和追踪
10. **可配置的课程URL和表单参数**：支持每个用户或全局配置课程提交URL和表单参数
11. **Web界面**：提供友好的Web界面，支持微信扫码登录和信息提交
12. **凭证管理**：支持凭证系统，每个凭证对应一个用户名额
13. **定时任务**：支持定时自动执行，可设置执行时间区间和执行日期
14. **时间区间随机执行**：在设定的时间区间内随机选择执行时间，避免固定时间执行
15. **自动配置重载**：支持手动和自动重载配置，定时任务设置立即生效

## 安装说明

### 1. 克隆或下载项目

将项目文件下载到本地：

```bash
git clone https://github.com/itrfcn/AITIYU
cd AITIYU-main
```

### 2. 安装依赖

项目依赖已记录在 `requirements.txt` 文件中，使用以下命令安装：

```bash
pip install -r requirements.txt
```

依赖包包括：
- Pillow (图像处理)
- opencv-python (图像处理和路径生成)
- numpy (数值计算)
- requests (HTTP 请求)
- scipy (可选，提高路径生成性能)
- Flask (Web框架)
- Flask-APScheduler (定时任务调度)
- beautifulsoup4 (HTML解析)

## 配置说明

### 1. 配置方式概述

现在支持多种配置方式，优先级从高到低为：
1. **命令行参数**：直接在运行命令中指定
2. **JSON配置文件中的用户单独配置**：在`users`数组中为每个用户单独设置
3. **JSON配置文件中的全局配置**：在`global_config`中设置，所有用户共享
4. **代码默认值**：如果以上都没有设置，则使用代码中的默认值

### 2. 核心配置参数

#### 2.1 课程URL和表单参数

这些参数可以通过多种方式配置：

- **全局默认值**：在`integrated_script.py`中设置（兼容性考虑）
- **命令行参数**：`--course-url`和`--form-data`
- **JSON配置文件**：在`global_config`或用户单独配置中设置
- **Web界面**：通过Web界面填写和提交

**示例**：
```json
{
  "global_config": {
    "course_url": "https://k8n.cn/student/profile/course/111/111",
    "default_form_data": {
      "form_id": "12345",
      "to_user_ida[]": "67890",
      "_score": "0"
    }
  },
  "users": [
    {
      "cookie": "remember_student_xxxx",
      "name": "张三",
      "username": "keep用户名",
      "avatar": "src/avatar.png",
      "course_url": "单独的课程URL（可选）",
      "default_form_data": {"单独的表单参数（可选）"}
    }
  ]
}
```

#### 2.2 KeepSultan配置

- 修改`KeepSultan.py`中的城市和其他参数（第107行的城市，第177-209行的运动参数）

#### 2.3 地图配置

- 修改`src/map1.png`为自己的地图背景图片
- 修改`src/map2.png`为自己的地图路径掩码图片
- 地图将自动生成并保存到`src/map`文件夹

#### 2.4 定时任务配置

定时任务配置支持以下参数：

```json
{
  "schedule": {
    "enabled": true,
    "start_time": "08:00",
    "end_time": "09:00",
    "days": [1, 2, 3, 4, 5, 6, 7]
  }
}
```

参数说明：
- `enabled`: 是否启用定时任务（true/false）
- `start_time`: 执行开始时间（格式：HH:MM）
- `end_time`: 执行结束时间（格式：HH:MM，时间区间最大2小时）
- `days`: 执行日期（1-7，分别代表周一到周日）

### 3. 配置文件格式

支持两种格式的JSON配置文件：

#### 3.1 单用户配置

```json
{
  "cookie": "remember_student_xxxx",
  "name": "张三",
  "username": "keep用户名",
  "avatar": "src/avatar.png",
  "course_url": "课程URL",
  "default_form_data": {
    "form_id": "12345",
    "to_user_ida[]": "67890",
    "_score": "0"
  },
  "schedule": {
    "enabled": true,
    "start_time": "08:00",
    "end_time": "09:00",
    "days": [1, 2, 3, 4, 5, 6, 7]
  }
}
```

#### 3.2 多用户配置

```json
{
  "global_config": {
    "course_url": "全局课程URL",
    "default_form_data": {
      "form_id": "12345",
      "to_user_ida[]": "67890",
      "_score": "0"
    }
  },
  "users": [
    {
      "cookie": "remember_student_user1",
      "name": "张三",
      "username": "keep用户1"
    },
    {
      "cookie": "remember_student_user2",
      "name": "李四",
      "username": "keep用户2",
      "course_url": "用户2的单独课程URL"
    }
  ]
}
```

## 使用方法

### 1. 主工作流脚本 `run_workflow.py`

主脚本 `run_workflow.py` 提供了多种使用方式，支持单用户、多用户和文件夹批量处理。

#### 1.1 命令行参数说明

参数说明：
- `-j/--json`：JSON配置文件路径（与`-f/--folder`互斥）
- `-f/--folder`：包含JSON配置文件的文件夹路径（与`-j/--json`互斥）
- `-c/--cookie`：指定要使用的 Cookie 字符串
- `-n/--name`：指定要使用的备注名称
- `-u/--username`：指定要使用的 Keep 用户名（默认：`用户`）
- `-a/--avatar`：指定要使用的 Keep 头像 URL（默认：`src/avatar.png`）
- `--course-url`：指定课程页面URL（可选，覆盖默认值）
- `--form-data`：默认表单参数JSON字符串（可选，覆盖默认值）

#### 1.2 单用户模式

**命令行参数方式**：

```bash
python run_workflow.py -c "remember_student_xxxx" -n "张三" --username "keep用户名" --avatar "src/avatar.png"
```

**带课程参数的命令行方式**：

```bash
python run_workflow.py -c "remember_student_xxxx" -n "张三" --course-url "https://k8n.cn/student/profile/course/111/111" --form-data '{"form_id":"12345","to_user_ida[]":"67890","_score":"0"}'
```

**JSON 配置文件方式**：

创建 `user_config.json` 文件：

```json
{
  "cookie": "remember_student_xxxx",
  "name": "张三",
  "username": "keep用户名",
  "avatar": "src/avatar.png",
  "course_url": "https://k8n.cn/student/profile/course/111/111",
  "default_form_data": {
    "form_id": "12345",
    "to_user_ida[]": "67890",
    "_score": "0"
  }
}
```

执行命令：

```bash
python run_workflow.py --json user_config.json
```

#### 1.3 多用户模式

创建多用户配置文件 `config_multi_user.json`：

```json
{
  "global_config": {
    "course_url": "https://k8n.cn/student/profile/course/111/111",
    "default_form_data": {
      "form_id": "12345",
      "to_user_ida[]": "67890",
      "_score": "0"
    }
  },
  "users": [
    {
      "cookie": "remember_student_user1",
      "name": "张三",
      "username": "keep用户1",
      "avatar": "src/avatar.png"
    },
    {
      "cookie": "remember_student_user2",
      "name": "李四",
      "username": "keep用户2",
      "course_url": "https://k8n.cn/student/profile/course/111/111"  // 单独的课程URL
    }
  ]
}
```

执行命令：

```bash
python run_workflow.py --json config_multi_user.json
```

#### 1.4 文件夹批量处理模式

将多个JSON配置文件放在一个文件夹中，例如 `configs` 文件夹：

```
configs/
├── user1.json
├── user2.json
└── multi_users.json
```

执行命令：

```bash
python run_workflow.py --folder configs
```

这将读取文件夹中所有JSON配置文件，合并全局配置和用户配置，并批量处理所有用户。

### 2. Web界面使用

#### 2.1 启动Web服务器

```bash
python app.py
```

服务器将在 `http://127.0.0.1:5000` 启动。

#### 2.2 登录流程

1. 使用管理员提供的凭证登录系统
2. 每个凭证代表一个用户名额
3. 支持重复登录，凭证可重复使用

#### 2.3 微信扫码登录

1. 点击"获取二维码"按钮
2. 使用微信扫码登录
3. 登录成功后系统自动获取Cookie
4. Cookie会自动保存到配置文件

#### 2.4 信息提交流程

1. 输入课程页面URL
2. 点击"获取表单信息"按钮
3. 选择审核员
4. 填写备注、keep名称和QQ号（用于生成头像）
5. 可选：启用定时任务并设置执行时间
6. 点击"提交信息"按钮完成提交

#### 2.5 定时任务设置

- **启用定时任务**：勾选"启用定时任务"复选框
- **设置时间区间**：选择开始时间和结束时间（最大间隔2小时）
- **选择执行日期**：选择周一到周日的执行日期
- **快捷选择**：提供"全选"、"工作日"、"周末"快捷按钮

### 3. 定时任务管理

#### 3.1 定时任务特性

- **时间区间随机执行**：在设定的时间区间内随机选择执行时间
- **多用户支持**：支持多个用户同时设置不同的定时任务
- **自动配置重载**：提交信息后自动重载配置，设置立即生效
- **任务状态监控**：提供API接口查看任务状态
- **临时任务清理**：任务执行完成后自动清理临时任务

#### 3.2 定时任务API

**获取任务列表**（需要密码）：
```bash
curl http://127.0.0.1:5000/api/schedule/jobs?password=admin123
```

**重载配置**（需要登录或密码）：
```bash
# 已登录用户
curl http://127.0.0.1:5000/api/schedule/reload

# 未登录用户（需要密码）
curl http://127.0.0.1:5000/api/schedule/reload?password=admin123
```

**说明**：
- 默认管理密码为 `admin123`，可在 `app.py` 文件中修改
- `/api/schedule/jobs` 接口只支持密码验证
- `/api/schedule/reload` 接口支持登录验证或密码验证

#### 3.3 定时任务执行流程

1. 母任务在设定的开始时间触发
2. 系统计算时间区间内的随机延迟
3. 创建临时任务在随机时间执行
4. 临时任务执行完整的工作流
5. 任务完成后自动清理临时任务

## 文件结构

```
├── fonts                    # 字体文件目录
├── images                   # 临时图片文件目录（存放生成的跑步截图）
├── src                      # 资源文件目录
│   ├── map                  # 地图相关资源目录（自动生成的地图存放于此）
│   ├── map1.png             # 地图背景图片
│   ├── map2.png             # 地图路径掩码图片
│   ├── avatar.png           # 默认头像图片
│   └── ...                  # 其他资源文件
├── data                     # 用户配置文件目录
├── templates                 # Web界面模板目录
│   ├── index.html           # 主页面模板
│   └── login.html           # 登录页面模板
├── run_workflow.py          # 主工作流脚本
├── KeepSultan.py            # 跑步截图生成工具
├── integrated_script.py     # 图片上传脚本
├── map.py                   # 运动轨迹地图生成工具
├── app.py                   # Flask Web应用
├── schedule_manager.py      # 定时任务管理器
├── requirements.txt         # 项目依赖
└── README.md                # 项目说明文档
```

## Cookie 处理说明

### 如何获取 Cookie

1. 登录课程系统网站
2. 打开浏览器开发者工具（F12）
3. 切换到 "网络" 或 "Network" 标签页
4. 刷新页面，找到任意请求
5. 在请求头中找到 "Cookie" 字段
6. 复制其中的 `remember_student_xxxxx` 部分即可

**注意**：不需要复制完整的 Cookie 字符串，只需要 `remember_student_xxxxx` 部分即可，脚本会自动获取 `s=` 部分。

### Web界面自动获取Cookie

Web界面支持微信扫码登录，自动获取Cookie：
1. 点击"获取二维码"按钮
2. 使用微信扫码登录
3. 系统自动获取并保存Cookie
4. Cookie会保存到data目录的配置文件中

## 注意事项

1. **Cookie 有效性**：请确保提供的 Cookie 是有效的，否则无法完成上传操作
2. **网络连接**：执行过程中需要保持网络连接畅通
3. **操作频率**：系统可能有提交频率限制，请避免过于频繁的操作
4. **配置文件格式**：JSON 配置文件必须符合指定的格式，否则可能导致解析失败
5. **目录权限**：请确保脚本有足够的权限读取配置文件和写入图片文件
6. **资源文件**：请确保 `src` 目录中包含必要的资源文件，如地图图片、图标等
7. **配置优先级**：命令行参数 > 用户单独配置 > 全局配置 > 代码默认值
8. **表单参数完整性**：请确保提供完整的表单参数，包括form_id、to_user_ida[]等，可通过浏览器开发者工具获取
9. **文件夹批量处理**：文件夹中的JSON文件必须符合指定格式，否则将被跳过
10. **地图生成**：确保src/map目录存在且有写入权限，用于存放自动生成的地图
11. **定时任务时间区间**：时间区间最大为2小时，超出限制会自动调整
12. **Web服务器端口**：默认使用5000端口，确保端口未被占用
13. **凭证管理**：每个凭证代表一个用户名额，请妥善保管凭证

## 系统架构

### 1. 前端架构

- **技术栈**：HTML5 + Bootstrap 5 + jQuery
- **功能模块**：
  - 登录模块
  - 二维码显示模块
  - 课程信息获取模块
  - 信息提交模块
  - 定时任务设置模块
  - QQ头像预览模块

### 2. 后端架构

- **技术栈**：Flask + Flask-APScheduler
- **核心模块**：
  - 用户认证模块
  - 微信登录模块
  - 课程信息提取模块
  - 数据存储模块
  - 定时任务管理模块
  - 工作流执行模块

### 3. 定时任务架构

- **调度器**：Flask-APScheduler BackgroundScheduler
- **任务类型**：
  - 母任务：Cron触发器，在设定时间触发
  - 临时任务：Date触发器，在随机时间执行
- **线程池**：20个线程的ThreadPoolExecutor
- **任务清理**：自动清理已执行的临时任务

## 类似项目

- [Keep](https://github.com/itrfcn/Keep)：一个用于生成 Keep 风格运动截图的在线工具。
- [KeepSultan-Web](https://github.com/itrfcn/KeepSultan-Web)：一个生成新版Keep截图的Web界面的项目。

## 鸣谢

- [KeepSultan](https://github.com/Carzit/KeepSultan)提供的keep截图生成相关代码。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！