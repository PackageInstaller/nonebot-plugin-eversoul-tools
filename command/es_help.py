from ..library.utils import *


async def load_help_config():
    """加载帮助配置文件"""
    from ..config import HELP_CONFIG

    if not HELP_CONFIG.exists():
        logger.warning(f"帮助配置文件不存在: {HELP_CONFIG}")
        return None

    try:
        with open(HELP_CONFIG, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"加载帮助配置文件失败: {e}")
        return None


async def generate_help_html(config: dict) -> str:
    """根据配置生成帮助HTML"""
    commands = config.get("commands", [])
    category_colors = config.get("category_colors", {})

    # 按分类分组
    categories = {}
    for cmd in commands:
        category = cmd.get("category", "其他")
        if category not in categories:
            categories[category] = []
        categories[category].append(cmd)

    # 生成表格行
    table_rows = ""
    for category, cmds in categories.items():
        color = category_colors.get(category, "#666666")
        for i, cmd in enumerate(cmds):
            # 第一行显示分类标签
            category_cell = ""
            if i == 0:
                category_cell = f"""
                    <td rowspan="{len(cmds)}" class="category-cell" style="background-color: {color};">
                        <span class="category-tag">{category}</span>
                    </td>"""

            table_rows += f"""
                <tr>
                    {category_cell}
                    <td class="command-cell">{cmd.get("name", "")}</td>
                    <td class="desc-cell">{cmd.get("description", "")}</td>
                    <td class="example-cell"><code>{cmd.get("example", "")}</code></td>
                </tr>"""

    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EverSoul命令列表</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1000px;
                margin: 0 auto;
            }}
            
            .header {{
                text-align: center;
                padding: 30px 0;
                color: white;
            }}
            
            .header h1 {{
                font-size: 36px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                margin-bottom: 10px;
            }}
            
            .header p {{
                font-size: 16px;
                opacity: 0.9;
            }}
            
            .table-container {{
                background: white;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            
            .command-table {{
                width: 100%;
                border-collapse: collapse;
            }}
            
            .command-table th {{
                background: linear-gradient(135deg, #12B1F4 0%, #0984e3 100%);
                color: white;
                padding: 16px 12px;
                text-align: left;
                font-size: 15px;
                font-weight: 600;
            }}
            
            .command-table th:first-child {{
                width: 80px;
                text-align: center;
            }}
            
            .command-table td {{
                padding: 12px;
                border-bottom: 1px solid #eef2f7;
                vertical-align: middle;
            }}
            
            .command-table tr:hover td {{
                background-color: #f8fafc;
            }}
            
            .category-cell {{
                text-align: center;
                color: white;
                font-weight: bold;
                writing-mode: vertical-lr;
                text-orientation: mixed;
                letter-spacing: 2px;
                font-size: 14px;
            }}
            
            .category-tag {{
                padding: 8px 4px;
            }}
            
            .command-cell {{
                font-weight: 500;
                color: #2d3748;
                min-width: 280px;
            }}
            
            .desc-cell {{
                color: #4a5568;
                min-width: 200px;
            }}
            
            .example-cell {{
                min-width: 220px;
            }}
            
            .example-cell code {{
                background: linear-gradient(135deg, #e8f4fd 0%, #d4e8f7 100%);
                padding: 4px 10px;
                border-radius: 6px;
                font-family: "Consolas", "Monaco", monospace;
                font-size: 13px;
                color: #0984e3;
                display: inline-block;
            }}
            
            .footer {{
                text-align: center;
                padding: 20px;
                color: white;
                opacity: 0.8;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎮 EverSoul 命令列表</h1>
                <p>所有可用命令的完整指南</p>
            </div>
            
            <div class="table-container">
                <table class="command-table">
                    <thead>
                        <tr>
                            <th>分类</th>
                            <th>命令</th>
                            <th>用途</th>
                            <th>示例</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
            
            <div class="footer">
                <p>使用 "es命令列表" 或 "es帮助" 查看此列表</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html


@es_help.handle()
async def handle(bot: Bot, event: Event):
    # 加载配置
    config = await load_help_config()

    if config:
        # 从配置生成HTML
        html = await generate_help_html(config)
    else:
        # 如果配置加载失败，使用默认HTML
        html = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>EverSoul命令列表</title>
            <style>
                body {
                    font-family: "Microsoft YaHei", sans-serif;
                    padding: 20px;
                    background: #f5f7fa;
                }
                .error {
                    text-align: center;
                    padding: 40px;
                    color: #e74c3c;
                }
            </style>
        </head>
        <body>
            <div class="error">
                <h2>⚠️ 加载帮助配置失败</h2>
                <p>请检查配置文件是否存在</p>
            </div>
        </body>
        </html>
        """

    pic = await html_to_pic(html, viewport={"width": 1000, "height": 10})

    text_info = """【腾讯文档】永恒灵魂(空灵诗篇)攻略推广
https://docs.qq.com/doc/DY2VBTFFZUHVLZ25H
Powered by 少姜
欢迎推广，致力于做最好的es攻略机器人（实际上也确实是最好的）
"""

    await es_help.finish(
        Message([MessageSegment.image(pic), MessageSegment.text(text_info)])
    )
