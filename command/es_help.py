from ..library.utils import *


@es_help.handle()
async def handle(bot: Bot, event: Event):
    html = """
    <!DOCTYPE html>
    <html lang="zh-CN">

    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EverSoul命令列表</title>
        <style>
            /* 基础样式 */
            body {
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f7fa;
                color: #333;
                line-height: 1.6;
            }

            /* 页面布局 */
            .container {
                width: 80%;
                margin: 0 auto;
                padding: 0 20px;
            }



            /* 表格样式 */
            .table-container {
                background-color: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
                margin: 40px 0 60px;
            }

            .table-container h1 {
                text-align: center;
                color: #fff;
                background-color: #12B1F4;
                margin: 0;
                padding: 10px 0;
            }



            .command-table {
                width: 100%;
                border-collapse: collapse;
            }

            .command-table th,
            .command-table td {
                padding: 15px 20px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }

            .command-table th {
                background-color: #12B1F4;
                color: white;
                font-weight: bold;
                font-size: 18px;
                border-bottom: 2px solid white;
            }

            .command-table tr:nth-child(even) {
                background-color: rgba(18, 177, 244, 0.1);
            }


            /* 图标样式 */
            .icon {
                display: inline-block;
                width: 24px;
                height: 24px;
                margin-right: 20px;
                vertical-align: middle;
                background-size: contain;
                background-repeat: no-repeat;
            }

            .icon-example {
                background-image: url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0iIzZBNkE2QSIgZD0iTTEyIDJDNi40OCAyIDIgNi40OCAyIDEyczQuNDggMTAgMTAgMTAgMTAtNC40OCAxMC0xMFMxNy41MiAyIDEyIDJ6bTAtMkM1LjM3NCAwIDAgNS4zNzQgMCAxMnM1LjM3NCAxMiAxMiAxMiAxMi01LjM3NCAxMi0xMlMwIDUuMzc0IDAgMTIgNS4zNzQgMCAxMiAweiIvPjxwYXRoIGZpbGw9IiMyQzNFNTAiIGQ9Ik0xNi41IDE1LjVMMTAgOS41bC0xLjUgMS41TDkgMTBsMyAzIDYtNi0xLjUtMS41eiIvPjwvc3ZnPg==');
            }
        </style>
    </head>

    <body>

        <!-- 主要内容 -->
        <main class="container">
            <!-- 表格容器 -->
            <div class="table-container">
                <table class="command-table">
                    <thead>
                        <tr class="titltTop">
                            <h1>EverSoul
                                命令列表所有可用命令的完整指南</h1>
                        </tr>
                        <tr style="border-top:solid 1px #fff">
                            <th>
                                <span class="icon icon-command" style="background-image: url('');"></span>
                                命令
                            </th>
                            <th>
                                <span class="icon icon-info" style="background-image: url('');"></span>
                                用途
                            </th>
                            <th>
                                <span class="icon icon-example" style="background-image: url('');"></span>
                                示例
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>
                                es角色信息
                                + 角色名</td>
                            <td>查询角色的详细信息</td>
                            <td>es角色信息大帝</td>
                        </tr>
                        <tr>
                            <td>
                                es技能信息
                                + 角色名</td>
                            <td>查询角色的技能信息</td>
                            <td>es技能信息大帝</td>
                        </tr>
                        <tr>
                            <td>
                                es角色列表
                            </td>
                            <td>查询所有角色以及别名</td>
                            <td>es角色列表</td>
                        </tr>
                        <tr>
                            <td>
                                es主线信息
                                + 章节-关卡</td>
                            <td>查询主线关卡的详细信息</td>
                            <td>es主线信息31-60</td>
                        </tr>
                        <tr>
                            <td>
                                esx月事件
                            </td>
                            <td>查询x月的所有事件</td>
                            <td>es1月事件</td>
                        </tr>
                        <tr>
                            <td>
                                es身高/体重排行
                            </td>
                            <td>查询身高/体重排行</td>
                            <td>es身高排行</td>
                        </tr>
                        <tr>
                            <td>
                                es升级消耗
                                + 等级</td>
                            <td>查询指定等级的升级消耗</td>
                            <td>es升级消耗1000</td>
                        </tr>
                        <tr>
                            <td>
                                es方舟等级信息
                                + 等级</td>
                            <td>查询指定方舟等级的信息</td>
                            <td>es方舟等级信息500</td>
                        </tr>
                        <tr>
                            <td>
                                es超频消耗
                                + 等级</td>
                            <td>查询方舟超频到指定等级的消耗</td>
                            <td>es超频消耗10</td>
                        </tr>
                        <tr>
                            <td>
                                es人类/野兽/妖精/不死/自由传送门信息
                                + 层数</td>
                            <td>查询传送门信息</td>
                            <td>es人类传送门信息10</td>
                        </tr>
                        <tr>
                            <td>
                                es突发礼包信息主线[章节]/[种类]传送门/起源塔/升阶
                            </td>
                            <td>查询突发礼包信息</td>
                            <td>es突发礼包信息主线31</td>
                        </tr>
                        <tr>
                            <td>
                                es礼品信息[品质][类型][种类]
                            </td>
                            <td>查询礼品信息</td>
                            <td>es礼品信息粉1智力加速</td>
                        </tr>
                        <tr>
                            <td>
                                es潜能信息
                            </td>
                            <td>查询潜能信息</td>
                            <td>es潜能信息</td>
                        </tr>
                        <tr>
                            <td>
                                es恶灵信息
                                + 恶灵ID</td>
                            <td>查询恶灵讨伐BOSS的详细信息</td>
                            <td>es恶灵信息66009</td>
                        </tr>
                        <tr>
                            <td>
                                es数据源
                                + [review/live]</td>
                            <td>切换数据源，仅限超管，群主以及管理员可用</td>
                            <td>es数据源review</td>
                        </tr>
                        <tr>
                            <td>
                                es兑换码
                            </td>
                            <td>兑换游戏礼包码</td>
                            <td>es兑换码</td>
                        </tr>
                        <tr>
                            <td>
                                es解绑账号
                            </td>
                            <td>解除当前绑定的游戏账号</td>
                            <td>es解绑账号</td>
                        </tr>
                        <tr>
                            <td>
                                es绑定账号
                                + [地区+ID]</td>
                            <td>手动绑定游戏账号，支持重新绑定</td>
                            <td>es绑定账号 kr123456789012</td>
                        </tr>
                        <tr>
                            <td>
                                es账号信息
                            </td>
                            <td>查看当前绑定的所有游戏账号信息</td>
                            <td>es账号信息</td>
                        </tr>
                        <tr>
                            <td>
                                es公告
                            </td>
                            <td>查询游戏公告</td>
                            <td>es公告</td>
                        </tr>
                        <tr>
                            <td>
                                es故事信息
                                + 数字ID</td>
                            <td>查询活动故事的详细信息</td>
                            <td>es故事信息12044</td>
                        </tr>
                        <tr>
                            <td>
                                es攻击范围排行
                            </td>
                            <td>查询攻击范围排行</td>
                            <td>es攻击范围排行</td>
                        </tr>
                        <tr>
                            <td>
                                es检查更新
                            </td>
                            <td>手动检查服务器更新状态</td>
                            <td>es检查更新</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </main>
    </body>

    </html>
    """
    
    pic = await html_to_pic(html, viewport={"width": 800, "height": 10})
    await es_help.finish(MessageSegment.image(pic))