#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HBase弹幕数据查询工具

功能：
- 按视频BV_ID查询所有弹幕
- 按时间范围查询弹幕
- 查询视频信息
- 词频统计查询

依赖：
- happybase: pip install happybase

使用方式：
    python hbase_query.py --mode video --bvid BV1jEAaz3E6K
    python hbase_query.py --mode danmaku --bvid BV1jEAaz3E6K
    python hbase_query.py --mode danmaku --bvid BV1jEAaz3E6K --start-ts 0 --end-ts 120
    python hbase_query.py --mode wordfreq --bvid BV1jEAaz3E6K --limit 50
"""

import json
import argparse
from typing import List, Dict, Any, Optional, Iterator

try:
    import happybase
    HAS_HBASE = True
except ImportError:
    HAS_HBASE = False


class HBaseQuery:
    """HBase数据查询器"""

    TABLE_VIDEO_INFO = 'video_info'
    TABLE_DANMAKU = 'danmaku_data'
    TABLE_WORDFREQ = 'wordfreq_data'

    def __init__(self, host='localhost', port=9090):
        """初始化HBase连接"""
        self.host = host
        self.port = port
        self.connection = None
        self.tables = {}

    def connect(self):
        """建立HBase连接"""
        if not HAS_HBASE:
            raise RuntimeError("happybase未安装，请执行: pip install happybase")

        self.connection = happybase.Connection(self.host, self.port)
        self.tables = {
            'video_info': self.connection.table(self.TABLE_VIDEO_INFO),
            'danmaku_data': self.connection.table(self.TABLE_DANMAKU),
            'wordfreq_data': self.connection.table(self.TABLE_WORDFREQ)
        }
        print(f"[INFO] 已连接到 HBase at {self.host}:{self.port}")

    def close(self):
        """关闭HBase连接"""
        if self.connection:
            self.connection.close()

    def _make_row_key(self, bvid: str, timestamp: float = None, dmid: str = None) -> str:
        """生成弹幕表RowKey前缀用于扫描"""
        if timestamp is not None:
            ts_str = str(int(timestamp * 100)).zfill(8)
            return f"{bvid}_{ts_str}"
        return bvid

    def query_video_info(self, bvid: str) -> Optional[Dict[str, Any]]:
        """查询视频信息

        Args:
            bvid: 视频BV号

        Returns:
            视频信息字典
        """
        table = self.tables.get('video_info')
        if not table:
            raise RuntimeError("未连接HBase或表不存在")

        row = table.row(bvid.encode('utf-8'))

        if not row:
            return None

        result = {}
        for key, value in row.items():
            col = key.decode('utf-8')
            # 解析列族:列
            if b':' in col:
                cf, column = col.split(':', 1)
                if cf not in result:
                    result[cf] = {}
                result[cf][column] = value.decode('utf-8')
            else:
                result[col] = value.decode('utf-8')

        return result

    def query_all_danmaku(self, bvid: str, limit: int = None) -> List[Dict[str, Any]]:
        """查询视频所有弹幕

        Args:
            bvid: 视频BV号
            limit: 限制返回条数

        Returns:
            弹幕列表
        """
        table = self.tables.get('danmaku_data')
        if not table:
            raise RuntimeError("未连接HBase或表不存在")

        # 构造扫描起始和结束RowKey
        start_row = f"{bvid}_"
        end_row = f"{bvid}_~"  # ~的ASCII码大于字母

        results = []
        count = 0

        for key, row in table.scan(row_start=start_row, row_stop=end_row):
            danmaku = {}
            for col, value in row.items():
                col_name = col.decode('utf-8')
                if ':' in col_name:
                    cf, column = col_name.split(':', 1)
                    if cf not in danmaku:
                        danmaku[cf] = {}
                    danmaku[cf][column] = value.decode('utf-8')

            # 提取原始RowKey信息
            danmaku['_rowkey'] = key.decode('utf-8')
            results.append(danmaku)

            count += 1
            if limit and count >= limit:
                break

        return results

    def query_danmaku_by_timerange(
        self,
        bvid: str,
        start_ts: float,
        end_ts: float,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """按时间范围查询弹幕

        Args:
            bvid: 视频BV号
            start_ts: 开始时间戳（秒）
            end_ts: 结束时间戳（秒）
            limit: 限制返回条数

        Returns:
            弹幕列表
        """
        table = self.tables.get('danmaku_data')
        if not table:
            raise RuntimeError("未连接HBase或表不存在")

        start_row = f"{bvid}_{str(int(start_ts * 100)).zfill(8)}"
        end_row = f"{bvid}_{str(int(end_ts * 100)).zfill(8)}~"

        results = []
        count = 0

        for key, row in table.scan(row_start=start_row, row_stop=end_row):
            danmaku = {}
            for col, value in row.items():
                col_name = col.decode('utf-8')
                if ':' in col_name:
                    cf, column = col_name.split(':', 1)
                    if cf not in danmaku:
                        danmaku[cf] = {}
                    danmaku[cf][column] = value.decode('utf-8')

            danmaku['_rowkey'] = key.decode('utf-8')
            results.append(danmaku)

            count += 1
            if limit and count >= limit:
                break

        return results

    def query_wordfreq(self, bvid: str, limit: int = 100) -> List[Dict[str, Any]]:
        """查询词频统计

        Args:
            bvid: 视频BV号
            limit: 限制返回条数

        Returns:
            词频列表
        """
        table = self.tables.get('wordfreq_data')
        if not table:
            raise RuntimeError("未连接HBase或表不存在")

        start_row = f"{bvid}_"
        end_row = f"{bvid}_~"

        results = []
        count = 0

        for key, row in table.scan(row_start=start_row, row_stop=end_row):
            item = {'word': key.decode('utf-8').split('_', 1)[-1]}
            for col, value in row.items():
                col_name = col.decode('utf-8')
                if ':' in col_name:
                    column = col_name.split(':', 1)[-1]
                    item[column] = value.decode('utf-8')

            results.append(item)
            count += 1

            if count >= limit:
                break

        # 按频率排序
        results.sort(key=lambda x: int(x.get('freq', 0)), reverse=True)

        return results[:limit]

    def query_danmaku_count(self, bvid: str) -> int:
        """统计视频弹幕总数

        Args:
            bvid: 视频BV号

        Returns:
            弹幕数量
        """
        table = self.tables.get('danmaku_data')
        if not table:
            raise RuntimeError("未连接HBase或表不存在")

        start_row = f"{bvid}_"
        end_row = f"{bvid}_~"

        count = 0
        for _ in table.scan(row_start=start_row, row_stop=end_row):
            count += 1

        return count

    def export_to_json(self, bvid: str, output_file: str):
        """导出视频所有数据到JSON文件

        Args:
            bvid: 视频BV号
            output_file: 输出文件路径
        """
        data = {
            'video_info': self.query_video_info(bvid),
            'danmaku_count': self.query_danmaku_count(bvid),
            'danmaku_list': self.query_all_danmaku(bvid, limit=10000),
            'wordfreq': self.query_wordfreq(bvid)
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[INFO] 数据已导出到: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='HBase弹幕数据查询工具')
    parser.add_argument('--host', default='localhost', help='HBase服务器地址')
    parser.add_argument('--port', type=int, default=9090, help='HBase服务器端口')
    parser.add_argument('--mode', choices=['video', 'danmaku', 'wordfreq', 'timerange', 'export', 'count'],
                        default='danmaku', help='查询模式')
    parser.add_argument('--bvid', default='BV1jEAaz3E6K', help='视频BV号')
    parser.add_argument('--start-ts', type=float, default=0, help='开始时间戳(秒)')
    parser.add_argument('--end-ts', type=float, default=99999, help='结束时间戳(秒)')
    parser.add_argument('--limit', type=int, default=100, help='限制返回条数')
    parser.add_argument('--output', help='输出文件路径(export模式)')

    args = parser.parse_args()

    query = HBaseQuery(host=args.host, port=args.port)

    try:
        query.connect()

        if args.mode == 'video':
            result = query.query_video_info(args.bvid)
            if result:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"[INFO] 未找到视频: {args.bvid}")

        elif args.mode == 'danmaku':
            results = query.query_all_danmaku(args.bvid, limit=args.limit)
            print(f"[INFO] 获取到 {len(results)} 条弹幕")
            print(json.dumps(results, ensure_ascii=False, indent=2))

        elif args.mode == 'timerange':
            results = query.query_danmaku_by_timerange(
                args.bvid, args.start_ts, args.end_ts, limit=args.limit
            )
            print(f"[INFO] 时间范围 [{args.start_ts}s - {args.end_ts}s] 内有 {len(results)} 条弹幕")
            print(json.dumps(results, ensure_ascii=False, indent=2))

        elif args.mode == 'wordfreq':
            results = query.query_wordfreq(args.bvid, limit=args.limit)
            print(f"[INFO] 获取到 {len(results)} 个词频统计")
            print(json.dumps(results, ensure_ascii=False, indent=2))

        elif args.mode == 'count':
            count = query.query_danmaku_count(args.bvid)
            print(f"[INFO] 视频 {args.bvid} 共有 {count} 条弹幕")

        elif args.mode == 'export':
            if not args.output:
                args.output = f"{args.bvid}_export.json"
            query.export_to_json(args.bvid, args.output)

    finally:
        query.close()


if __name__ == '__main__':
    main()