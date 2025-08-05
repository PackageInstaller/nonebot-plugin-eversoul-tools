from ..library.utils import *


@es_auto_push_control.handle()
async def handle_auto_push_control(bot: Bot, event: Event):
    """处理自动推送控制命令"""
    raw_message = event.get_plaintext().strip()
    
    # 解析命令参数
    if "开启" in raw_message or "启动" in raw_message:
        action = "start"
    elif "关闭" in raw_message or "停止" in raw_message:
        action = "stop"
    elif "状态" in raw_message or "查看" in raw_message:
        action = "status"
    else:
        await es_auto_push_control.finish(
            "使用方法：\n"
            "es自动推送 开启 - 启动自动推送\n"
            "es自动推送 关闭 - 停止自动推送\n"
            "es自动推送 状态 - 查看当前状态"
        )
        return
    
    if action == "start":
        try:
            # 检查任务是否已存在
            existing_job = scheduler.get_job("eversoul_update_check")
            if existing_job:
                await es_auto_push_control.finish("自动推送功能已经在运行中")
            else:
                # 导入定时任务函数
                from .es_update_check import scheduled_update_check
                # 重新添加任务
                scheduler.add_job(
                    func=scheduled_update_check,
                    trigger="interval",
                    minutes=1,
                    id="eversoul_update_check",
                    replace_existing=True
                )
                await es_auto_push_control.finish("✅ 已启动自动推送功能，每分钟检查一次更新")
        except FinishedException:
            raise
        except Exception as e:
            await es_auto_push_control.finish(f"启动自动推送失败: {e}")
    
    elif action == "stop":
        try:
            # 删除定时任务
            scheduler.remove_job("eversoul_update_check")
            await es_auto_push_control.finish("✅ 已停止自动推送功能")
        except FinishedException:
            raise
        except Exception as e:
            await es_auto_push_control.finish("❌ 停止自动推送失败，可能任务已经停止")
    
    elif action == "status":
        try:
            existing_job = scheduler.get_job("eversoul_update_check")
            if existing_job:
                next_run = existing_job.next_run_time
                status_msg = f"✅ 自动推送功能正在运行\n下次检查时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                status_msg = "❌ 自动推送功能已停止"
            await es_auto_push_control.finish(status_msg)
        except FinishedException:
            raise
        except Exception as e:
            await es_auto_push_control.finish(f"查看状态失败: {e}")

