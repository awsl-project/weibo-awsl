# weibo 爬虫

> 本爬虫仅供学习交流，请不要非法使用（后果自负

自动爬取某个微博博主转发的微博，根据关键词匹配，记录匹配到的微博的图片

创建 .env 文件

```env
headers={}
max_page=50
db_url=mysql+mysqlconnector://xxx:xxx/xxx
pika_url=xxx://:xxx@localhost:6379/0
bot_queue=xxx
```

运行

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
python3 main.py
```
