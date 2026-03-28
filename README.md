#  爱体育自动化工作流

## 项目简介

爱体育自动化工作流是一个用于自动生成跑步截图并自动上传到提交系统的工具，支持多用户批量处理。
本项目的主要功能是生成keep跑步截图并自动提交到班级魔方。
写这个项目的初衷是为了方便自己完成每个学期的跑步任务，避免自己忘记提交。
如果你是青岛科技大学的学生，那这个项目可能会对你有帮助。

如果你单纯的只是想生成keep截图，请去看KeepSultan.py。
或者访问[keep截图生成](https://github.com/itrfcn/Keep)本人之前写的这个项目。

## 功能特点

1. **自动生成跑步截图**：通过 `KeepSultan.py` 生成模拟的跑步运动截图
2. **自动上传提交系统**：通过 `integrated_script.py` 将生成的图片上传到指定提交系统
3. **多用户批量处理**：支持通过 JSON 配置文件批量处理多个用户
4. **灵活的参数配置**：支持命令行参数或 JSON 配置文件，支持参数覆盖
5. **自动清理**：上传成功后自动删除生成的图片文件
6. **Cookie保活**：通过有效期5年的Cookie，自动获取有效期只有2小时的`s=`部分，确保Cookie有效
7. **详细的日志记录**：执行过程中生成详细的日志信息，便于调试和追踪

## 安装说明

### 1. 克隆或下载项目

将项目文件下载到本地：

```bash
git clone https://github.com/itrfcn/AITIYU
cd AITIYU
``` 

### 2. 安装依赖

项目依赖已记录在 `requirements.txt` 文件中，使用以下命令安装：

```bash
pip install -r requirements.txt
```

依赖包包括：
- Pillow (图像处理)
- requests (HTTP 请求)

## 配置说明

### 1. 修改integrated_script.py文件
第28行的 COURSE_URL 改成你自己的班级魔方提交的URL。
第40行的 DEFAULT_FORM_DATA 改成你自己的班级魔方提交的表单参数。
自己F12提交一次，抓全参数，包括表单ID、接收人ID等。
其他的参数不要修改。

### 2. 修改KeepSultan.py文件
第107行的城市 改成你自己的城市。
第184-208行的参数 按照你的需要修改。


## 使用方法

### 1. 主工作流脚本 `run_workflow.py`

主脚本 `run_workflow.py` 提供了多种使用方式，支持单用户和多用户处理。

#### 1.1 单用户模式

**命令行参数方式**：

```bash
python run_workflow.py -c "YOUR_COOKIE" -n "备注" --username "keep用户名"
```

**JSON 配置文件方式**：

创建 `user_config.json` 文件：

```json
{
    "cookie": "YOUR_COOKIE_STRING_HERE",
    "name": "备注",
    "username": "keep用户名"
}
```

执行命令：

```bash
python run_workflow.py --json user_config.json
```

#### 1.2 多用户模式

创建多用户配置文件 `config_multi_user.json`：

```json
{
    "users": [
        {
            "cookie": "USER1_COOKIE_STRING_HERE",
            "name": "备注",
            "username": "keep用户名"
        },
        {
            "cookie": "USER2_COOKIE_STRING_HERE",
            "name": "备注",
            "username": "keep用户名"    
        }
    ]
}
```

执行命令：

```bash
python run_workflow.py --json config_multi_user.json
```

## 文件结构

```
├── fonts                    # 字体文件目录
├── images                   # 临时图片文件目录
├── src                      # 资源文件目录
├── run_workflow.py          # 主工作流脚本
├── KeepSultan.py            # 跑步截图生成工具
├── integrated_script.py     # 图片上传脚本
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

## 注意事项

1. **Cookie 有效性**：请确保提供的 Cookie 是有效的，否则无法完成上传操作
2. **网络连接**：执行过程中需要保持网络连接畅通
3. **操作频率**：系统可能有提交频率限制，请避免过于频繁的操作
4. **配置文件格式**：JSON 配置文件必须符合指定的格式，否则可能导致解析失败
5. **目录权限**：请确保脚本有足够的权限读取配置文件和写入图片文件


## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！


