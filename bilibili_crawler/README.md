# B站视频弹幕数据爬虫

## 功能说明

本程序用于爬取B站视频的基本信息和弹幕数据，支持保存为JSON格式。

## 文件列表

- `bilibili_crawler.py` - 主程序，包含完整的爬虫代码
- `requirements.txt` - Python依赖库

## 环境要求

- Python 3.7+
- requests 库

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 方式一：直接运行

```bash
python bilibili_crawler.py
```

### 方式二：导入模块使用

```python
from bilibili_crawler import crawl_bilibili_video

# 爬取指定视频
result = crawl_bilibili_video("BV1jEAaz3E6K", "output.json")
```

## 输出数据格式

```json
{
  "video_info": {
    "bvid": "BV1jEAaz3E6K",
    "title": "视频标题",
    "description": "视频简介",
    "aid": 123456789,
    "cid": 123456789,
    "duration": 300,
    "publish_date": "2024-01-01 12:00:00",
    "view_count": 1000000,
    "like_count": 50000,
    "coin_count": 10000,
    "favorite_count": 20000,
    "share_count": 5000,
    "danmaku_count": 5000,
    "reply_count": 3000,
    "owner": {
      "mid": 123456,
      "name": "UP主名称",
      "face": "UP主头像URL"
    },
    "tags": ["标签1", "标签2"]
  },
  "danmaku_list": [
    {
      "content": "弹幕内容",
      "timestamp": 12.5,
      "type": 1,
      "font_size": 25,
      "color": "16777215",
      "color_hex": "#ffffff",
      "sender": "发送者",
      "send_time": 1234567890,
      "pool": 0
    }
  ],
  "danmaku_count": 5000,
  "crawl_time": "2024-01-01 12:00:00"
}
```

## API接口说明

1. **视频信息API**: `https://api.bilibili.com/x/web-interface/view?bvid={BV_ID}`
2. **弹幕API**: `https://api.bilibili.com/x/v1/dm/list.so?oid={CID}`

## 注意事项

1. B站有反爬机制，爬取频率过高可能导致IP被封
2. 部分视频需要登录才能获取完整信息
3. 弹幕颜色使用十进制存储，已转换为十六进制格式
4. 请遵守B站robots.txt和相关使用协议