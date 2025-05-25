from ..library.utils import *


@es_help.handle()
async def handle_es_help(bot: Bot, event: Event):
    html = """
    <html>
    <head>
        <style>
            body {
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                padding: 20px;
                background: #f5f5f5;
                color: #333;
            }
            .container {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            h1 {
                color: #2c3e50;
                font-size: 24px;
                margin-bottom: 20px;
                text-align: center;
            }
            .command {
                margin-bottom: 20px;
                padding: 10px;
                border-left: 4px solid #3498db;
                background: #f8f9fa;
            }
            .command-name {
                font-weight: bold;
                color: #2980b9;
                margin-bottom: 5px;
            }
            .usage, .example {
                margin: 5px 0;
                color: #666;
            }
            .example {
                font-style: italic;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>EverSoul 命令列表</h1>
            
            <div class="command">
                <div class="command-name">es角色信息 + 角色名</div>
                <div class="usage">用途：查询角色的详细信息</div>
                <div class="example">示例：es角色信息大帝</div>
            </div>

            <div class="command">
                <div class="command-name">es角色列表</div>
                <div class="usage">用途：查询所有角色以及别名</div>
                <div class="example">示例：es角色列表</div>
            </div>
            
            <div class="command">
                <div class="command-name">es主线信息 + 章节-关卡</div>
                <div class="usage">用途：查询主线关卡的详细信息</div>
                <div class="example">示例：es主线信息31-60</div>
            </div>
            
            <div class="command">
                <div class="command-name">es x 月事件</div>
                <div class="usage">用途：查询x月的所有事件</div>
                <div class="example">示例：es1月事件</div>
            </div>
            
            <div class="command">
                <div class="command-name">es身高/体重排行</div>
                <div class="usage">用途：查询身高/体重排行</div>
                <div class="example">示例：es身高排行</div>
            </div>
            
            <div class="command">
                <div class="command-name">es升级消耗 + 等级</div>
                <div class="usage">用途：查询指定等级的升级消耗</div>
                <div class="example">示例：es升级消耗1000</div>
            </div>
            
            <div class="command">
                <div class="command-name">es方舟等级信息 + 等级</div>
                <div class="usage">用途：查询指定方舟等级的信息</div>
                <div class="example">示例：es方舟等级信息500</div>
            </div>
            
            <div class="command">
                <div class="command-name">es超频消耗 + 等级</div>
                <div class="usage">用途：查询方舟超频到指定等级的消耗</div>
                <div class="example">示例：es超频消耗10</div>
            </div>
            
            <div class="command">
                <div class="command-name">es人类/野兽/妖精/不死/自由传送门信息 + 层数</div>
                <div class="usage">用途：查询传送门信息</div>
                <div class="example">示例：es人类传送门信息10</div>
            </div>
            <div class="command">
                <div class="command-name">es突发礼包信息主线[章节]/[种类]传送门/起源塔/升阶</div>
                <div class="usage">用途：查询突发礼包信息</div>
                <div class="example">示例：es突发礼包信息主线31</div>
            </div>
            <div class="command">
                <div class="command-name">es礼品信息[品质][类型][种类]</div>
                <div class="usage">用途：查询礼品信息</div>
                <div class="example">示例：es礼品信息粉1智力加速</div>
            </div>
            <div class="command">
                <div class="command-name">es潜能信息</div>
                <div class="usage">用途：查询潜能信息</div>
                <div class="example">示例：es潜能信息</div>
            </div>
            <div class="command">
                <div class="command-name">es恶灵信息 + 恶灵ID</div>
                <div class="usage">用途：查询恶灵讨伐BOSS的详细信息</div>
                <div class="example">示例：es恶灵信息66009</div>
            </div>
            <div class="command">
                <div class="command-name">es数据源 + [review/live]</div>
                <div class="usage">用途：切换数据源，仅限超管，群主以及管理员可用</div>
                <div class="example">示例：es数据源review</div>
            </div>
            <div class="command">
                <div class="command-name">es兑换码</div>
                <div class="usage">用途：兑换游戏礼包码，支持多个兑换码同时兑换（空格分隔）</div>
                <div class="example">示例：es兑换码 CODE1 CODE2 CODE3</div>
            </div>
            <div class="command">
                <div class="command-name">es解绑账号</div>
                <div class="usage">用途：解除当前绑定的游戏账号</div>
                <div class="example">示例：es解绑账号</div>
            </div>
            <div class="command">
                <div class="command-name">es绑定账号 + [地区+ID]</div>
                <div class="usage">用途：手动绑定游戏账号，支持重新绑定</div>
                <div class="example">示例：es绑定账号 kr123456789012</div>
            </div>
            <div class="command">
                <div class="command-name">es账号信息</div>
                <div class="usage">用途：查看当前绑定的所有游戏账号信息</div>
                <div class="example">示例：es账号信息</div>
            </div>
            <div class="command">
                <div class="command-name">es公告</div>
                <div class="usage">用途：查询游戏公告</div>
                <div class="example">示例：es公告</div>
            </div>
            
            <div class="command">
                <div class="command-name">es故事信息 + 数字ID</div>
                <div class="usage">用途：查询活动故事的详细信息</div>
                <div class="example">示例：es故事信息12044</div>
            </div>
        </div>
    </body>
    </html>
    """
    
    pic = await html_to_pic(html, viewport={"width": 800, "height": 10})
    await es_help.finish(MessageSegment.image(pic))