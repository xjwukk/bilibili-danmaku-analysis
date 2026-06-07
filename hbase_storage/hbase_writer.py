#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HBase弹幕数据写入工具

功能：
- 从JSON文件读取弹幕数据并写入HBase
- 支持视频信息、弹幕内容、词频统计三类数据写入

依赖：
- happybase: pip install happybase
- thrift: pip install thrift

使用方式：
    python hbase_writer.py --mode danmaku --input ../nlp_processing/cleaned_danmaku.json
    python hbase_writer.py --mode video --input ../bilibili_crawler/bilibili_data.json
    python hbase_writer.py --mode wordfreq --input ../nlp_processing/wordfreq.json
"""

import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import happybase
    HAS_HBASE = True
except ImportError:
    HAS_HBASE = False


class HBaseWriter:
    """HBase数据写入器"""

    # 表名定义
    TABLE_VIDEO_INFO = 'video_info'
    TABLE_DANMAKU = 'danmaku_data'
    TABLE_WORDFREQ = 'wordfreq_data'

    def __init__(self, host='localhost', port=9090, namespace='bilibili'):
        """初始化HBase连接

        Args:
            host: HBase Thrift服务器地址
            port: HBase Thrift服务器端口
            namespace: 命名空间
        """
        self.host = host
        self.port = port
        self.namespace = namespace
        self.connection = None
        self.tables = {}

    def connect(self):
        """建立HBase连接"""
        if not HAS_HBASE:
            raise RuntimeError("happybase未安装，请执行: pip install happybase")

        self.connection = happybase.Connection(self.host, self.port)
        if self.namespace:
            self.connection.open_table(self.namespace)

        # 初始化表引用
        self.tables = {
            'video_info': self.connection.table(self.TABLE_VIDEO_INFO),
            'danmaku_data': self.connection.table(self.TABLE_DANMAKU),
            'wordfreq_data': self.connection.table(self.TABLE_WORDFREQ)
        }
        print(f"[INFO] 已连接到 HBase at {self.host}:{self.port}")

    def create_tables(self):
        """创建HBase表（如果不存在）"""
        if not self.connection:
            self.connect()

        existing_tables = set(self.connection.tables())

        # 创建视频信息表
        if self.TABLE_VIDEO_INFO.encode() not in existing_tables:
            self.connection.create_table(
                self.TABLE_VIDEO_INFO,
                {'info': dict(), 'stats': dict()}
            )
            print(f"[INFO] 创建表: {self.TABLE_VIDEO_INFO}")

        # 创建弹幕数据表
        if self.TABLE_DANMAKU.encode() not in existing_tables:
            self.connection.create_table(
                self.TABLE_DANMAKU,
                {'content': dict(), 'meta': dict()}
            )
            print(f"[INFO] 创建表: {self.TABLE_DANMAKU}")

        # 创建词频统计表
        if self.TABLE_WORDFREQ.encode() not in existing_tables:
            self.connection.create_table(
                self.TABLE_WORDFREQ,
                {'stats': dict()}
            )
            print(f"[INFO] 创建表: {self.TABLE_WORDFREQ}")

    def close(self):
        """关闭HBase连接"""
        if self.connection:
            self.connection.close()
            print("[INFO] HBase连接已关闭")

    def _generate_rowkey(self, bvid: str, timestamp: float = 0, dmid: str = "") -> str:
        """生成弹幕表RowKey

        RowKey格式: BV_ID + timestamp(8位零填充) + dmid
        例如: BV1jEAaz3E6K_00000001_2060848104261108480

        Args:
            bvid: 视频BV号
            timestamp: 弹幕出现时间（秒）
            dmid: 弹幕唯一ID

        Returns:
            RowKey字符串
        """
        ts_str = str(int(timestamp * 100)).zfill(8)
        dmid_str = dmid.split('_')[-1] if dmid else str(int(time.time() * 1000))
        return f"{bvid}_{ts_str}_{dmid_str}"

    def write_video_info(self, video_data: Dict[str, Any]) -> int:
        """写入视频信息

        Args:
            video_data: 视频信息字典

        Returns:
            写入的行数
        """
        table = self.tables.get('video_info')
        if not table:
            raise RuntimeError("未连接HBase或表不存在")

        bvid = video_data.get('bvid', video_data.get('BV_ID', ''))

        # 解析owner信息
        owner = video_data.get('owner', {})
        owner_name = owner.get('name', '') if isinstance(owner, dict) else ''
        owner_mid = owner.get('mid', '') if isinstance(owner, dict) else ''

        # 格式化发布时间
        publish_date = video_data.get('publish_date', '')
        if isinstance(publish_date, str):
            try:
                dt = datetime.strptime(publish_date, "%Y-%m-%d %H:%M:%S")
                publish_date = str(int(dt.timestamp()))
            except ValueError:
                publish_date = str(video_data.get('pubdate_timestamp', ''))

        rowkey = bvid.encode('utf-8')
        data = {
            'info:title': str(video_data.get('title', '')),
            'info:author': str(owner_name),
            'info:author_mid': str(owner_mid),
            'info:publish_date': str(publish_date),
            'info:duration': str(video_data.get('duration', 0)),
            'info:description': str(video_data.get('description', '')),
            'info:cid': str(video_data.get('cid', '')),
            'stats:view_count': str(video_data.get('view_count', 0)),
            'stats:like_count': str(video_data.get('like_count', 0)),
            'stats:coin_count': str(video_data.get('coin_count', 0)),
            'stats:favorite_count': str(video_data.get('favorite_count', 0)),
            'stats:danmaku_count': str(video_data.get('danmaku_count', 0)),
            'stats:reply_count': str(video_data.get('reply_count', 0)),
            'stats:share_count': str(video_data.get('share_count', 0)),
            'stats:last_updated': str(int(time.time()))
        }

        table.put(rowkey, data)
        print(f"[INFO] 写入视频信息: {bvid}")
        return 1

    def write_danmaku(self, danmaku_list: List[Dict[str, Any]], bvid: str) -> int:
        """批量写入弹幕数据

        Args:
            danmaku_list: 弹幕列表
            bvid: 视频BV号

        Returns:
            写入的行数
        """
        table = self.tables.get('danmaku_data')
        if not table:
            raise RuntimeError("未连接HBase或表不存在")

        count = 0
        batch = table.batch()

        for dm in danmaku_list:
            # 生成RowKey
            timestamp = dm.get('timestamp', 0)
            dmid = dm.get('row_id', dm.get('dmid', ''))
            rowkey = self._generate_rowkey(bvid, timestamp, dmid)

            # 准备数据
            data = {
                'content:text': str(dm.get('content', '')),
                'content:send_time': str(dm.get('send_time', 0)),
                'content:timestamp': str(timestamp),
                'meta:user_id': str(dm.get('sender', dm.get('user_id', ''))),
                'meta:is_upper': str(dm.get('is_up', dm.get('is_upper', 0))),
                'meta:color': str(dm.get('color', 16777215)),
                'meta:color_hex': str(dm.get('color_hex', '#ffffff')),
                'meta:mode': str(dm.get('type', dm.get('mode', 1))),
                'meta:font_size': str(dm.get('font_size', 25)),
                'meta:pool': str(dm.get('pool', 0))
            }

            batch.put(rowkey.encode('utf-8'), data)
            count += 1

            # 每1000条发送一次批量
            if count % 1000 == 0:
                batch.send()
                print(f"[INFO] 已写入 {count} 条弹幕...")

        # 发送剩余数据
        batch.send()
        print(f"[INFO] 完成写入弹幕: {count} 条")
        return count

    def write_wordfreq(self, wordfreq_data: Dict[str, Any], bvid: str) -> int:
        """写入词频统计数据

        Args:
            wordfreq_data: 词频统计数据
            bvid: 视频BV号

        Returns:
            写入的行数
        """
        table = self.tables.get('wordfreq_data')
        if not table:
            raise RuntimeError("未连接HBase或表不存在")

        # 处理top_100格式
        top_words = wordfreq_data.get('top_100', [])

        count = 0
        batch = table.batch()

        for word_item in top_words:
            word = word_item.get('word', '')
            freq = word_item.get('freq', 0)

            rowkey = f"{bvid}_{word}".encode('utf-8')
            data = {
                'stats:freq': str(freq)
            }

            batch.put(rowkey, data)
            count += 1

        batch.send()
        print(f"[INFO] 完成写入词频: {count} 条")
        return count

    def load_video_from_file(self, filepath: str) -> bool:
        """从文件加载视频信息

        Args:
            filepath: JSON文件路径

        Returns:
            是否成功
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 处理不同格式
            if 'video_info' in data:
                video_data = data['video_info']
            elif 'bvid' in data:
                video_data = data
            else:
                print(f"[ERROR] 未找到视频信息: {filepath}")
                return False

            self.write_video_info(video_data)
            return True

        except Exception as e:
            print(f"[ERROR] 读取文件失败: {filepath}, {e}")
            return False

    def load_danmaku_from_file(self, filepath: str, bvid: str = None) -> int:
        """从文件加载弹幕数据

        Args:
            filepath: JSON文件路径
            bvid: 视频BV号（可选，从数据中提取）

        Returns:
            写入的弹幕数量
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 处理不同格式
            if 'danmaku_list' in data:
                danmaku_list = data['danmaku_list']
            elif isinstance(data, list):
                danmaku_list = data
            else:
                print(f"[ERROR] 未找到弹幕数据: {filepath}")
                return 0

            # 提取BV号
            if not bvid:
                if 'video_info' in data and 'bvid' in data['video_info']:
                    bvid = data['video_info']['bvid']
                elif 'bvid' in data:
                    bvid = data['bvid']

            if not bvid:
                print("[ERROR] 未指定BV号")
                return 0

            return self.write_danmaku(danmaku_list, bvid)

        except Exception as e:
            print(f"[ERROR] 读取文件失败: {filepath}, {e}")
            return 0

    def load_wordfreq_from_file(self, filepath: str, bvid: str = None) -> int:
        """从文件加载词频数据

        Args:
            filepath: JSON文件路径
            bvid: 视频BV号

        Returns:
            写入的词频数量
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not bvid:
                if 'bvid' in data:
                    bvid = data['bvid']

            if not bvid:
                print("[ERROR] 未指定BV号")
                return 0

            return self.write_wordfreq(data, bvid)

        except Exception as e:
            print(f"[ERROR] 读取文件失败: {filepath}, {e}")
            return 0


def main():
    parser = argparse.ArgumentParser(description='HBase弹幕数据写入工具')
    parser.add_argument('--host', default='localhost', help='HBase服务器地址')
    parser.add_argument('--port', type=int, default=9090, help='HBase服务器端口')
    parser.add_argument('--mode', choices=['danmaku', 'video', 'wordfreq', 'all'],
                        default='all', help='写入模式')
    parser.add_argument('--input', help='输入JSON文件路径')
    parser.add_argument('--bvid', help='视频BV号（可选）')

    args = parser.parse_args()

    writer = HBaseWriter(host=args.host, port=args.port)

    try:
        # 连接并创建表
        writer.connect()

        # 如果指定了输入文件，直接加载
        if args.input:
            if args.mode in ['video', 'all']:
                writer.load_video_from_file(args.input)
            elif args.mode in ['danmaku', 'all']:
                writer.load_danmaku_from_file(args.input, args.bvid)
            elif args.mode in ['wordfreq', 'all']:
                writer.load_wordfreq_from_file(args.input, args.bvid)
        else:
            # 创建表结构
            writer.create_tables()
            print("[INFO] 表结构已创建")

    finally:
        writer.close()


if __name__ == '__main__':
    main()