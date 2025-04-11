# Eversoul QQ机器人插件

## 📖 介绍

Eversoul QQ机器人插件是为永恒灵魂游戏玩家开发的一款多功能辅助工具，基于Nonebot2框架。通过此插件，玩家可以方便地：

- 管理多个服务器账号（亚服、韩服、欧美服、日服）
- 自动批量兑换游戏礼包码
- 查询角色信息、游戏数据
- 计算升级所需资源
- 获取各种游戏攻略数据

## 💿 安装

<details>
<summary>git</summary>

    `git clone https://github.com/PackageInstaller/nonebot-plugin-eversoul-tools`
</details>

## ⚙️ 配置

在 nonebot2 项目的`.env`文件中添加下表中的必填配置

| 配置项 | 必填 | 默认值 | 说明 |
|:-----:|:----:|:----:|:----:|
| eversoul_live_path | 是 | 无 | live数据源json路径 |
| eversoul_review_path | 否 | 无 | review数据源json路径，可选 |

## 🎉 使用

### 指令表

| 指令 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----:|
| es帮助 | 所有人 | 否 | 群聊/私聊 | 查看插件帮助信息 |

### 兑换码功能说明

1. 将礼包码添加到 `resources/data/coupons.yaml` 文件中
2. 发送 `es兑换码` 指令，机器人会自动为您所有绑定的账号兑换所有礼包码
3. 已经兑换过的礼包码会自动跳过，避免重复请求
4. 系统会尝试兑换已过期的兑换码，如果兑换成功则自动延长过期日期
