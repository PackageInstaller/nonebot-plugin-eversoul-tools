import json
import yaml
from pathlib import Path

# JSON文件路径
LIVE_JSON_PATH = Path("/home/rikka/Eversoul/live_jsons")
REVIEW_JSON_PATH = Path("/home/rikka/Eversoul/review_jsons")

def process_json_files(json_path: Path, output_prefix: str):
    # 加载所需的JSON文件
    with open(json_path / "Hero.json", "r", encoding="utf-8") as f:
        hero_data = json.load(f)
    
    with open(json_path / "StringCharacter.json", "r", encoding="utf-8") as f:
        string_char_data = json.load(f)
    
    # 创建英雄名称字典
    hero_names = {}
    for string in string_char_data["json"]:
        if "no" in string:
            if string["no"] not in hero_names:
                hero_names[string["no"]] = {
                    "zh_tw": string.get("zh_tw", ""),
                    "zh_cn": string.get("zh_cn", ""),
                    "kr": string.get("kr", ""),
                    "en": string.get("en", "")
                }
    
    # 用于去重的集合
    seen_hero_ids = set()
    
    # 尝试读取现有的YAML文件
    existing_data = {}
    yaml_file = Path(f"{output_prefix}_hero_aliases.yaml")
    if yaml_file.exists():
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                existing_data = yaml.safe_load(f)
    
            # 创建现有别名和中文名的查找字典
            existing_aliases = {}
            existing_zh_cn_names = {}
            if existing_data and "names" in existing_data:
                for hero in existing_data["names"]:
                    if "hero_id" in hero:
                        hero_id = hero["hero_id"]
                        if "aliases" in hero:
                            existing_aliases[hero_id] = hero.get("aliases", [])
                        if "zh_cn_name" in hero and hero["zh_cn_name"]:  # 保存非空的中文名
                            existing_zh_cn_names[hero_id] = hero["zh_cn_name"]
        except Exception as e:
            print(f"读取现有别名文件时出错: {e}")
            existing_aliases = {}
            existing_zh_cn_names = {}
    else:
        existing_aliases = {}
        existing_zh_cn_names = {}
    
    # 用于去重的字典，键为名称，值为最小的hero_id
    name_to_min_id = {}
    
    # 遍历英雄数据，找出7000以上ID的最小值
    for hero in hero_data["json"]:
        if ("hero_id" in hero and 
            "name_sno" in hero and 
            hero["hero_id"] >= 7000):
            
            name_data = hero_names.get(hero["name_sno"], {
                "zh_tw": "未知",
                "zh_cn": "",
                "kr": "",
                "en": ""
            })
            current_id = hero["hero_id"]
            
            # 使用繁体中文名称作为键
            zh_tw_name = name_data["zh_tw"]
            if zh_tw_name in name_to_min_id:
                # 如果已存在该名称，保留较小的ID
                name_to_min_id[zh_tw_name] = min(name_to_min_id[zh_tw_name], current_id)
            else:
                name_to_min_id[zh_tw_name] = current_id
    
    # 准备两个数据结构
    new_data = {"names": []}
    monster_data = {"names": []}
    
    # 用于记录怪物名称出现次数的字典
    monster_name_count = {}
    
    # 遍历英雄数据
    for hero in hero_data["json"]:
        if ("hero_id" in hero and 
            "name_sno" in hero and 
            hero["hero_id"] not in seen_hero_ids):
            
            hero_id = hero["hero_id"]
            name_data = hero_names.get(hero["name_sno"], {
                "zh_tw": "未知",
                "zh_cn": "",
                "kr": "",
                "en": ""
            })
            
            # 处理中文名称 - 如果JSON中为空但现有文件中有非空值，则使用现有值
            zh_cn_name = name_data["zh_cn"]
            if not zh_cn_name and hero_id in existing_zh_cn_names:
                zh_cn_name = existing_zh_cn_names[hero_id]
            
            # 创建基础条目
            hero_entry = {
                "zh_tw_name": name_data["zh_tw"],
                "zh_cn_name": zh_cn_name,  # 使用处理后的中文名
                "kr_name": name_data["kr"],
                "en_name": name_data["en"],
                "aliases": existing_aliases.get(hero_id, []),  # 确保包含现有别名
                "hero_id": hero_id
            }
            
            # 区分处理7000以上和以下的ID
            if hero_id >= 7000:
                # 处理重复名称
                if name_data["zh_tw"] in monster_name_count:
                    monster_name_count[name_data["zh_tw"]] += 1
                    hero_entry["zh_tw_name"] = f"{name_data['zh_tw']}{monster_name_count[name_data['zh_tw']]}"
                else:
                    monster_name_count[name_data["zh_tw"]] = 0
                
                monster_data["names"].append(hero_entry)
            else:
                new_data["names"].append(hero_entry)
            
            seen_hero_ids.add(hero_id)
    
    # 调整YAML输出格式
    class CustomDumper(yaml.SafeDumper):
        def increase_indent(self, flow=False, indentless=False):
            return super().increase_indent(flow, False)

        def represent_scalar(self, tag, value, style=None):
            if isinstance(value, str):
                style = None  # No quotes for strings
            return super().represent_scalar(tag, value, style)

        def represent_sequence(self, tag, sequence, flow_style=None):
            """对于字符串列表使用flow风格（单行）"""
            if len(sequence) > 0 and isinstance(sequence[0], str):
                flow_style = True
            return super().represent_sequence(tag, sequence, flow_style=flow_style)

    # 保存普通英雄别名
    with open(f"{output_prefix}_hero_aliases.yaml", "w", encoding="utf-8") as f:
        yaml.dump(new_data, f, 
                 Dumper=CustomDumper,
                 allow_unicode=True, 
                 sort_keys=False,
                 default_flow_style=False,
                 indent=2)
    
    # 保存怪物别名
    with open(f"{output_prefix}_monster_aliases.yaml", "w", encoding="utf-8") as f:
        yaml.dump(monster_data, f, 
                 Dumper=CustomDumper,
                 allow_unicode=True, 
                 sort_keys=False,
                 default_flow_style=False,
                 indent=2)
    
    return len(new_data['names']), len(monster_data['names'])

def generate_aliases():
    # 处理live文件
    try:
        live_hero_count, live_monster_count = process_json_files(LIVE_JSON_PATH, "live")
        print(f"Live版本处理完成！")
        print(f"总共生成 {live_hero_count} 个英雄条目")
        print(f"总共生成 {live_monster_count} 个怪物条目")
    except Exception as e:
        print(f"处理live文件时出错: {e}")
    
    # 处理review文件
    try:
        review_hero_count, review_monster_count = process_json_files(REVIEW_JSON_PATH, "review")
        print(f"\nReview版本处理完成！")
        print(f"总共生成 {review_hero_count} 个英雄条目")
        print(f"总共生成 {review_monster_count} 个怪物条目")
    except Exception as e:
        print(f"处理review文件时出错: {e}")

if __name__ == "__main__":
    generate_aliases()