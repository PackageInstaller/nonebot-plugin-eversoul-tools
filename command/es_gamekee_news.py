from ..library.utils import *

seen_posts = set()

URL = "https://www.gamekee.com/eversoul/list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Referer": "https://www.gamekee.com/eversoul/",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9"
}

# 这是gamekee永恒灵魂玩家交流群,欢迎加入!
PUSH_GROUP_ID = 645741432

async def build_post_message(index, post):
    message = [
        f"【{index}】{post['title']}\n",
        f"类型: {post['tag_text']}\n" if post.get('tag_text') else "",
        f"作者: {post['author']}\n",
        f"发布时间: {post['date']}\n",
    ]
    
    if post.get('read_count'):
        message.append(f"阅读数: {post['read_count']}\n")
    if post.get('comments_count'):
        message.append(f"评论数: {post['comments_count']}\n")

    message.append(f"链接: {post['url']}\n")
    
    msg = Message("".join(message))
    
    if post.get('content_text') and post['content_text'].strip():
        content_preview = post['content_text'].strip()
        if content_preview:
            msg.append(f"\n帖子内容：\n{content_preview}\n")
    
    # 添加帖子图片（所有图片）
    if post.get('content_images') and post['content_images']:
        msg.append("\n帖子图片：\n")
        for i, img_url in enumerate(post['content_images']):
            try:
                msg.append(MessageSegment.image(img_url))
            except Exception as e:
                logger.error(f"添加帖子图片失败: {e}")
    
    # 添加评论（最多10条）
    if post.get('comments') and post['comments']:
        msg.append("\n热门评论：\n")
        for i, comment in enumerate(post['comments'][:10]):  # 最多展示10条评论
            comment_text = f"{comment['author']}: {comment['content']}\n"
            msg.append(comment_text)
    
    return msg

# 解析GameKee日期字符串为datetime对象
def parse_gamekee_date(date_str):
    try:
        # 处理"几分钟前"、"几小时前"这种时间格式
        if "刚刚" in date_str:
            return datetime.now()
        elif "秒前" in date_str:
            seconds = int(date_str.replace("秒前", "").strip())
            return datetime.now() - datetime.timedelta(seconds=seconds)
        elif "分钟前" in date_str:
            minutes = int(date_str.replace("分钟前", "").strip())
            return datetime.now() - datetime.timedelta(minutes=minutes)
        elif "小时前" in date_str:
            hours = int(date_str.replace("小时前", "").strip())
            return datetime.now() - datetime.timedelta(hours=hours)
        elif "天前" in date_str:
            days = int(date_str.replace("天前", "").strip())
            return datetime.now() - datetime.timedelta(days=days)
        elif "个月前" in date_str:
            months = int(date_str.replace("个月前", "").strip())
            # 近似计算，一个月按30天计算
            return datetime.now() - datetime.timedelta(days=30*months)
        elif "年前" in date_str:
            years = int(date_str.replace("年前", "").strip())
            # 近似计算，一年按365天计算
            return datetime.now() - datetime.timedelta(days=365*years)
        else:
            # 处理常规日期格式（例如"2023/12/15"）
            current_year = datetime.now().year
            if "/" in date_str:
                # 假设格式为 YYYY/MM/DD 或 MM/DD
                parts = date_str.split('/')
                if len(parts) == 3:
                    # 完整日期格式 YYYY/MM/DD
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2].replace("日", "").strip())
                    return datetime(year, month, day)
                elif len(parts) == 2:
                    # 简略日期格式 MM/DD，默认当前年份
                    month = int(parts[0])
                    day = int(parts[1].replace("日", "").strip())
                    return datetime(current_year, month, day)
            
            # 处理其他格式
            if "日" in date_str:
                # 去掉"日"字，避免解析错误
                date_str = date_str.replace("日", "")
            
            # 尝试几种常见的日期格式
            date_formats = [
                "%Y/%m/%d", 
                "%Y-%m-%d",
                "%Y年%m月%d"
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            logger.warning(f"无法解析日期格式: {date_str}，将使用当前日期")
            return datetime.now()
            
    except Exception as e:
        logger.error(f"解析日期时出错: {e}, 原始日期: {date_str}")
        return datetime.now()

# 定义一个异步函数来获取帖子列表
async def fetch_posts():
    try:
        # 使用同步请求库，在实际使用中应该使用aiohttp
        response = requests.get(URL, headers=HEADERS)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            logger.error(f"获取失败: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        post_elements = soup.select("div.article-list-item")

        posts = []
        # 计算一个月前的日期
        one_day_ago = datetime.now()
        
        for el in post_elements:
            # 标题
            title_span = el.select_one("div.title span:nth-child(2)")
            title = title_span.get_text(strip=True) if title_span else "无标题"

            # 链接
            href_el = el.select_one("a")
            href = "https://www.gamekee.com" + href_el.get("href") if href_el else None

            # 标签类型
            tag_el = el.select_one("div.title span.tag")
            tag_text = tag_el.get_text(strip=True) if tag_el else ""
            
            # 作者
            author_el = el.select_one("div.username")
            author = author_el.get_text(strip=True) if author_el else "未知作者"

            # 头像
            avatar_el = el.select_one("img.avatar")
            avatar = avatar_el["src"] if avatar_el else None

            # 发布时间
            date_el = el.select_one("div.date")
            date = date_el.get_text(strip=True) if date_el else "未知时间"
            
            # 解析发布时间
            post_date = parse_gamekee_date(date)
            
            # 过滤掉超过一个月的帖子
            if post_date < one_day_ago:
                logger.info(f"跳过过期帖子: {title}, 发布时间: {date}")
                continue
            
            # 评论数
            comment_el = el.select_one("div.comment")
            comments = comment_el.get_text(strip=True) if comment_el else "0"

            posts.append({
                "title": title,
                "url": href,
                "tag_text": tag_text,
                "author": author,
                "avatar": avatar,
                "date": date,
                "post_date": post_date,
                "comments": comments
            })

        return posts
    except Exception as e:
        logger.error(f"获取GameKee社区信息时出错: {e}")
        return []

# 获取帖子详细内容
async def fetch_post_detail(url):
    if not url:
        return None
        
    try:
        # 使用同步请求库
        response = requests.get(url, headers=HEADERS)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            logger.error(f"获取帖子详情失败: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        
        # 获取阅读数
        read_count_el = soup.select_one("div.wiki-detail-desc span.yds-num:nth-child(2)")
        read_count = "0"
        if read_count_el:
            read_count_text = read_count_el.get_text(strip=True)
            read_count = re.search(r'阅读数：(\d+)', read_count_text)
            read_count = read_count.group(1) if read_count else "0"
        
        # 获取帖子内容 - 支持多种可能的内容容器
        content_text = ""
        content_images = []
        
        # 尝试多种可能的内容容器格式
        content_containers = [
            soup.select_one("div.wiki-detail-content"),  # 第一种格式
            soup.select_one("div.wiki-editor-content"),  # 第二种格式
            soup.select_one("div.content div.wiki-editor-content"),  # 用户示例中的格式
            soup.select_one("div.detail-content-comp")   # 备用格式
        ]
        
        # 查找第一个非空的内容容器
        content_el = None
        for container in content_containers:
            if container and len(container.text.strip()) > 0:
                content_el = container
                break
        
        # 提取文本内容
        if content_el:
            # 获取所有文本节点
            for text_node in content_el.stripped_strings:
                if text_node and len(text_node.strip()) > 0:
                    content_text += text_node + " "
        
        # 提取图片 - 尝试多种可能的图片选择器
        if content_el:
            # 尝试第一种格式的图片
            image_elements = content_el.select("img.w_e_network_image_success")
            if not image_elements:
                # 尝试第二种格式的图片
                image_elements = content_el.select("img.preview-image")
            if not image_elements:
                # 尝试通用图片选择器
                image_elements = content_el.select("img")
                
            for img in image_elements:
                if img.get("src"):
                    # 确保图片URL完整
                    img_url = img["src"]
                    if img_url.startswith("//"):
                        img_url = "https:" + img_url
                    content_images.append(img_url)
        
        # 获取评论数和评论
        comments_el = soup.select_one("div.comment-box .title")
        comments_count = "0"
        if comments_el:
            comments_match = re.search(r'评论（(\d+)）', comments_el.get_text(strip=True))
            comments_count = comments_match.group(1) if comments_match else "0"
        
        # 获取具体评论
        comments = []
        comment_elements = soup.select("div.userAnswer")
        for comment_el in comment_elements:
            author_el = comment_el.select_one("p.user-name span.user")
            author = author_el.get_text(strip=True) if author_el else "未知用户"
            
            content_el = comment_el.select_one("div.content span")
            content = content_el.get_text(strip=True) if content_el else ""
            
            date_el = comment_el.select_one("p.time-area span.time")
            date = date_el.get_text(strip=True) if date_el else ""
            
            if author and content:  # 只添加有作者和内容的评论
                comments.append({
                    "author": author,
                    "content": content,
                    "date": date
                })

        # 如果没有获取到内容和图片，添加调试日志
        if not content_text.strip() and not content_images:
            logger.warning(f"未能获取到帖子内容和图片: {url}")
            # 尝试记录页面结构，帮助调试
            main_content = soup.select_one("div.main-content")
            if main_content:
                logger.info(f"页面主内容结构: {main_content.name}")
                for child in main_content.find_all(recursive=False):
                    logger.info(f"子元素: {child.name}, 类: {child.get('class')}")
        
        return {
            "read_count": read_count,
            "content_text": content_text,
            "content_images": content_images,
            "comments_count": comments_count,
            "comments": comments
        }
    except Exception as e:
        logger.error(f"获取帖子详情时出错: {e}")
        return None

# 定义定时任务，每10分钟检查新帖子
# @scheduler.scheduled_job("cron", minute="*/10", id="gamekee_news_check")
# async def check_gamekee_news():
#     try:
#         logger.info("检查 GameKee 社区新帖子...")
#         posts = await fetch_posts()
        
#         new_posts = []
#         for post in posts:
#             url = post['url']
#             if url and url not in seen_posts:
#                 seen_posts.add(url)
#                 new_posts.append(post)
        
#         # 如果有新帖子且机器人已连接，则推送到群
#         if new_posts:
#             try:
#                 bot = get_bot()  # 获取当前的机器人实例
                
#                 # 先发送总标题
#                 await bot.send_group_msg(group_id=PUSH_GROUP_ID, message="【GameKee社区新帖子推送】")
                
#                 # 为每个帖子获取详细信息并单独发送
#                 for i, post in enumerate(new_posts, 1):
#                     # 获取帖子详情（使用异步等待以避免阻塞）
#                     post_detail = await fetch_post_detail(post['url'])
#                     if post_detail:
#                         # 合并详情信息
#                         post.update(post_detail)
                    
#                     # 构建消息
#                     msg = await build_post_message(i, post)
                    
#                     # 发送帖子信息
#                     await bot.send_group_msg(group_id=PUSH_GROUP_ID, message=msg)
                    
#                     # 添加延时避免过快发送
#                     await asyncio.sleep(1)
                
#                 logger.info(f"成功推送 {len(new_posts)} 个新帖子到群 {PUSH_GROUP_ID}")
#             except Exception as e:
#                 logger.error(f"推送GameKee新帖子时出错: {e}")
#     except Exception as e:
#         logger.error(f"检查GameKee新帖子定时任务出错: {e}") 