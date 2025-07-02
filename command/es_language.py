"""
Eversoul语言设置命令
"""

from ..library.utils import *
from ..library.utils.es_i18n_utils import (
    t, set_group_language, get_group_language, normalize_language,
    get_i18n_manager, SUPPORTED_LANGUAGES, LANGUAGE_ALIASES
)

@es_language.handle()
async def handle_language(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取群组ID
        group_id = 0
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        
        # 获取参数
        arg_text = args.extract_plain_text().strip()
        
        if not arg_text:
            # 显示当前语言设置和可用语言
            current_lang = get_group_language(group_id)
            
            msg_parts = []
            msg_parts.append(t("language.current", group_id=group_id, default="当前语言: {lang}", lang=current_lang))
            msg_parts.append("")
            msg_parts.append(t("language.available", group_id=group_id, default="可用语言:"))
            
            for lang in SUPPORTED_LANGUAGES:
                aliases = ', '.join(LANGUAGE_ALIASES[lang][:3])  # 只显示前3个别名
                msg_parts.append(f"• {lang}: {aliases}")
            
            msg_parts.append("")
            msg_parts.append(t("language.usage", group_id=group_id, default="使用方法: es语言 <语言代码>"))
            
            await es_language.finish('\n'.join(msg_parts))
        
        # 标准化语言代码
        new_lang = normalize_language(arg_text)
        
        if not new_lang:
            available_langs = []
            for lang, aliases in LANGUAGE_ALIASES.items():
                available_langs.append(f"{lang}: {', '.join(aliases[:2])}")
            
            error_msg = t("language.invalid", group_id=group_id, 
                         default="无效的语言代码: {input}\n\n可用语言:\n{langs}", 
                         input=arg_text, langs='\n'.join(available_langs))
            await es_language.finish(error_msg)
        
        # 设置语言
        if set_group_language(group_id, new_lang):
            success_msg = t("language.set_success", group_id=group_id, 
                           default="语言已设置为: {lang}", lang=new_lang)
            await es_language.finish(success_msg)
        else:
            error_msg = t("language.set_failed", group_id=group_id, 
                         default="设置语言失败")
            await es_language.finish(error_msg)
            
    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback
            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理语言设置时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_language.finish(f"处理语言设置时发生错误: {str(e)}") 