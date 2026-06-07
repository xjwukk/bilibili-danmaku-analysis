#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HBase环境检查和模拟测试工具

功能：
- 检查HBase连接
- 使用内存模拟HBase操作（无需真实HBase环境）
- 本地测试数据写入和查询流程

使用方式：
    python hbase_simulator.py --mode demo
    python hbase_simulator.py --mode test --input ../nlp_processing/cleaned_danmaku.json
"""

import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict


class SimulatedHBaseTable:
    """模拟HBase表（内存实现，用于测试）"""

    def __init__(self, name: str):
        self.name = name
        self.data = {}  # rowkey -> {column: value}
        self.column_families = {}

    def put(self, rowkey: bytes, data: Dict[str, bytes]):
        """写入一行数据"""
        key = rowkey.decode('utf-8') if isinstance(rowkey, bytes) else rowkey
        self.data[key] = {k.decode('utf-8'): v.decode('utf-8') for k, v in data.items()}

    def row(self, rowkey: bytes) -> Dict[bytes, bytes]:
        """获取一行数据"""
        key = rowkey.decode('utf-8') if isinstance(rowkey, bytes) else rowkey
        if key not in self.data:
            return {}
        return {k.encode('utf-8'): v.encode('utf-8') for k, v in self.data[key].items()}

    def scan(self, row_start: str = None, row_stop: str = None, limit: int = None):
        """扫描表数据"""
        keys = sorted(self.data.keys())

        if row_start:
            keys = [k for k in keys if k >= row_start]
        if row_stop:
            keys = [k for k in keys if k < row_stop]

        count = 0
        for key in keys:
            if limit and count >= limit:
                break
            yield key.encode('utf-8'), self.row(key.encode('utf-8'))
            count += 1

    def count(self) -> int:
        """统计数据行数"""
        return len(self.data)


class SimulatedHBaseConnection:
    """模拟HBase连接"""

    def __init__(self):
        self.tables = {
            'video_info': SimulatedHBaseTable('video_info'),
            'danmaku_data': SimulatedHBaseTable('danmaku_data'),
            'wordfreq_data': SimulatedHBaseTable('wordfreq_data')
        }
        self._open = True

    def table(self, name: str):
        return self.tables.get(name)

    def tables_list(self) -> List[str]:
        return list(self.tables.keys())

    def close(self):
        self._open = False


class HBaseSimulator:
    """HBase模拟器（用于本地测试）"""

    TABLE_VIDEO_INFO = 'video_info'
    TABLE_DANMAKU = 'danmaku_data'
    TABLE_WORDFREQ = 'wordfreq_data'

    def __init__(self):
        self.connection = SimulatedHBaseConnection()
        self.tables = self.connection.tables

    def create_tables(self):
        """创建表结构"""
        print("[INFO] 创建模拟表结构:")
        print("  - video_info (info, stats)")
        print("  - danmaku_data (content, meta)")
        print("  - wordfreq_data (stats)")

    def write_video_info(self, video_data: Dict[str, Any]) -> int:
        """写入视频信息"""
        bvid = video_data.get('bvid', video_data.get('BV_ID', ''))
        table = self.tables['video_info']

        owner = video_data.get('owner', {})
        owner_name = owner.get('name', '') if isinstance(owner, dict) else ''

        rowkey = bvid
        data = {
            'info:title': video_data.get('title', ''),
            'info:author': str(owner_name),
            'info:publish_date': str(video_data.get('pubdate_timestamp', '')),
            'info:duration': str(video_data.get('duration', 0)),
            'stats:view_count': str(video_data.get('view_count', 0)),
            'stats:like_count': str(video_data.get('like_count', 0)),
            'stats:danmaku_count': str(video_data.get('danmaku_count', 0))
        }

        table.put(rowkey.encode('utf-8'), {k.encode('utf-8'): v.encode('utf-8') for k, v in data.items()})
        print(f"[INFO] 写入视频: {bvid}")
        return 1

    def write_danmaku(self, danmaku_list: List[Dict], bvid: str) -> int:
        """批量写入弹幕"""
        table = self.tables['danmaku_data']
        count = 0

        for dm in danmaku_list:
            timestamp = dm.get('timestamp', 0)
            dmid = dm.get('row_id', str(int(time.time() * 1000)))
            ts_str = str(int(timestamp * 100)).zfill(8)
            rowkey = f"{bvid}_{ts_str}_{dmid.split('_')[-1]}"

            data = {
                'content:text': dm.get('content', ''),
                'content:timestamp': str(timestamp),
                'meta:user_id': str(dm.get('sender', '')),
                'meta:color_hex': dm.get('color_hex', '#ffffff')
            }

            table.put(rowkey.encode('utf-8'), {k.encode('utf-8'): v.encode('utf-8') for k, v in data.items()})
            count += 1

        print(f"[INFO] 写入弹幕: {count} 条")
        return count

    def query_video_info(self, bvid: str) -> Optional[Dict]:
        """查询视频信息"""
        table = self.tables['video_info']
        row = table.row(bvid.encode('utf-8'))
        if not row:
            return None

        result = {}
        for col, value in row.items():
            cf, column = col.decode('utf-8').split(':', 1)
            if cf not in result:
                result[cf] = {}
            result[cf][column] = value.decode('utf-8')

        return result

    def query_danmaku(self, bvid: str, limit: int = 10) -> List[Dict]:
        """查询弹幕"""
        table = self.tables['danmaku_data']
        start_row = f"{bvid}_"
        end_row = f"{bvid}_~"

        results = []
        for key, row in table.scan(row_start=start_row, row_stop=end_row, limit=limit):
            dm = {'_rowkey': key.decode('utf-8')}
            for col, value in row.items():
                cf, column = col.decode('utf-8').split(':', 1)
                if cf not in dm:
                    dm[cf] = {}
                dm[cf][column] = value.decode('utf-8')
            results.append(dm)

        return results

    def run_demo(self):
        """运行演示"""
        print("\n" + "=" * 60)
        print("HBase 模拟器演示")
        print("=" * 60)

        # 1. 创建表
        self.create_tables()

        # 2. 写入视频信息
        demo_video = {
            'bvid': 'BV1jEAaz3E6K',
            'title': '一个视频搞懂OpenClaw！',
            'owner': {'name': '林亦LYi'},
            'duration': 593,
            'view_count': 5180838,
            'like_count': 135089,
            'danmaku_count': 5432,
            'pubdate_timestamp': 1772282360
        }
        self.write_video_info(demo_video)

        # 3. 写入弹幕
        demo_danmaku = [
            {'content': '赛博闹鬼', 'timestamp': 64.488, 'row_id': '12345', 'sender': '1772763438'},
            {'content': '经典程序员为了偷懒做工具2333', 'timestamp': 41.971, 'row_id': '12346', 'sender': '1772763439'},
            {'content': '说白了就是大众需要低代码平台', 'timestamp': 542.936, 'row_id': '12347', 'sender': '1772763440'},
        ]
        self.write_danmaku(demo_danmaku, 'BV1jEAaz3E6K')

        # 4. 查询演示
        print("\n[查询视频信息]")
        info = self.query_video_info('BV1jEAaz3E6K')
        if info:
            print(f"  标题: {info.get('info', {}).get('title', 'N/A')}")
            print(f"  作者: {info.get('info', {}).get('author', 'N/A')}")
            print(f"  播放: {info.get('stats', {}).get('view_count', 'N/A')}")

        print("\n[查询弹幕列表]")
        danmaku = self.query_danmaku('BV1jEAaz3E6K', limit=5)
        for dm in danmaku:
            text = dm.get('content', {}).get('text', 'N/A')
            ts = dm.get('content', {}).get('timestamp', 'N/A')
            print(f"  [{ts}s] {text}")

        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)

    def test_from_file(self, danmaku_file: str):
        """从文件加载测试数据"""
        print(f"\n[INFO] 从文件加载测试数据: {danmaku_file}")

        try:
            with open(danmaku_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 提取视频信息
            if 'video_info' in data:
                self.write_video_info(data['video_info'])

            # 提取弹幕列表
            danmaku_list = data.get('danmaku_list', [])
            bvid = data.get('video_info', {}).get('bvid', 'BV1jEAaz3E6K') if 'video_info' in data else 'BV1jEAaz3E6K'

            if danmaku_list:
                self.write_danmaku(danmaku_list, bvid)

            print(f"\n[INFO] 弹幕总数: {len(danmaku_list)}")

            # 验证查询
            print("\n[查询前5条弹幕]")
            results = self.query_danmaku(bvid, limit=5)
            for dm in results:
                text = dm.get('content', {}).get('text', 'N/A')
                print(f"  - {text}")

        except Exception as e:
            print(f"[ERROR] 处理失败: {e}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='HBase模拟器测试工具')
    parser.add_argument('--mode', choices=['demo', 'test'],
                        default='demo', help='运行模式')
    parser.add_argument('--input', help='弹幕JSON文件路径')

    args = parser.parse_args()

    simulator = HBaseSimulator()

    if args.mode == 'demo':
        simulator.run_demo()
    elif args.mode == 'test':
        if args.input:
            simulator.test_from_file(args.input)
        else:
            print("[ERROR] 请指定 --input 参数")


if __name__ == '__main__':
    main()