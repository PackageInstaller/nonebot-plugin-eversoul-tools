# Eversoul QQ机器人插件

## 📖 介绍

Eversoul QQ机器人插件是为永恒灵魂游戏玩家开发的一款多功能辅助工具，基于 Nonebot2 框架。通过此插件，可以方便地：

- 自动批量兑换游戏礼包码（不支持国服）
- 查询角色、关卡、BOSS、活动等游戏攻略数据
- 支持多数据源切换（国服 live/review、国际服、日服）
- 自动检查并更新游戏数据表

## 💿 安装

```bash
git clone --depth=1 https://github.com/PackageInstaller/nonebot-plugin-eversoul-tools

cd nonebot-plugin-eversoul-tools
pip install -r requirements.txt
```

将插件目录放入 NoneBot 项目的 `plugins` 目录下。

## ⚙️ 配置

在 NoneBot 项目的 `.env` 文件中添加以下配置：

|      配置项       | 必填 |  默认值  |           说明           |
| :---------------: | :--: | :------: | :----------------------: |
| eversoul_auto_update |  否  |   true   | 是否自动检查并更新数据表 |

数据源（国服/国际服/日服、live/review）按群组配置，首次使用时通过 `es数据源` 命令切换，配置将持久化至 `data/config/data_source_config.yaml`。

## 🎉 使用

### 指令表

|  指令  |  权限  | 需要@ |   范围   |       说明       |
| :----: | :----: | :---: | :------: | :--------------: |
| es命令列表 | 所有人 |  否  | 群聊/私聊 | 显示所有可用命令 |
| es帮助 | 所有人 |  否  | 群聊/私聊 | 查看插件帮助信息 |

更多指令请使用 `es命令列表` 查看完整列表，涵盖角色、关卡、BOSS、活动、养成、礼品、排行、账号、系统等分类。