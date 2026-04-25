#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MapReduce词频统计程序

功能：
- 对HBase中的弹幕数据进行词频统计
- 支持情感分析和词频聚合

输入：HBase danmaku_data表
输出：HBase wordfreq_data表

使用方式：
    # 本地测试模式（无需Hadoop）
    python wordfreq_mapreduce.py --mode local --input ../agent2_nlp/cleaned_danmaku.json

    # Hadoop集群模式
    hadoop jar /path/to/hadoop-streaming.jar \
        -input danmaku_data \
        -output wordfreq_output \
        -mapper wordfreq_mapper.py \
        -reducer wordfreq_reducer.py

    # 直接写入HBase模式
    python wordfreq_mapreduce.py --mode hbase --bvid BV1jEAaz3E6K
"""

import json
import re
import sys
from collections import defaultdict
from typing import Iterator, List, Dict, Any, Tuple

# Python MapReduce兼容接口
# 在Hadoop Streaming中，stdin/stdout用于mapper/reducer通信


class WordFreqMapper:
    """词频统计Mapper"""

    # 停用词列表
    STOP_WORDS = {
        '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '自己', '这', '他', '什么', '之', '而', '与', '其', '及', '或', '等', '被',
        '把', '那', '能', '下', '过', '里', '个', '来', '对', '起', '让', '给', '为',
        '从', '但', '却', '更', '被', '以', '及', '于', '中', '大', '小', '多', '少',
        '2333', '666', '哈哈哈', '笑死', '233', 'hh', '？？', '???', '???', '...',
        '啊', '呢', '吧', '呀', '哦', '额', '嗯', '哇', '诶', '嘿', '哈', '哼', '咦'
    }

    def __init__(self):
        self.word_counts = defaultdict(int)

    def tokenize(self, text: str) -> List[str]:
        """中文分词（简单实现）"""
        if not text:
            return []

        # 移除非汉字字符（保留中文）
        text = re.sub(r'[^\u4e00-\u9fff\u0000-\u007F]', ' ', text)

        # 简单按长度分割
        words = []
        current_word = ''

        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                if current_word:
                    words.append(current_word)
                    current_word = ''
                # 单独的中文字符
                if len(char) > 1:
                    words.append(char)
            else:
                current_word += char

        if current_word:
            words.append(current_word)

        # 过滤停用词和短字符
        result = []
        for word in words:
            word = word.strip()
            if word and word not in self.STOP_WORDS and len(word) >= 2:
                result.append(word)

        return result

    def map(self, key: str, value: str) -> Iterator[Tuple[str, int]]:
        """Map函数

        Args:
            key: 弹幕RowKey或弹幕ID
            value: 弹幕JSON数据或文本

        Yields:
            (word, count) 元组
        """
        try:
            # 尝试解析JSON
            if isinstance(value, str):
                try:
                    data = json.loads(value)
                except json.JSONDecodeError:
                    data = {'text': value}
            else:
                data = value

            # 获取弹幕文本
            text = data.get('content', data.get('text', ''))
            if not text:
                return

            # 分词
            words = self.tokenize(text)
            for word in words:
                yield (word, 1)

        except Exception as e:
            # 出错时跳过
            sys.stderr.write(f"[ERROR] Map failed: {e}\n")
            return

    def process_stdin(self):
        """从stdin读取数据进行处理（Hadoop Streaming模式）"""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            # Hadoop Streaming格式：key\tvalue
            parts = line.split('\t', 1)
            if len(parts) == 2:
                key, value = parts
            else:
                key = ''
                value = line

            for word, count in self.map(key, value):
                print(f"{word}\t{count}")


class WordFreqReducer:
    """词频统计Reducer"""

    def __init__(self):
        self.word_counts = defaultdict(int)

    def reduce(self, word: str, counts: Iterator[int]) -> Iterator[Tuple[str, int]]:
        """Reduce函数

        Args:
            word: 单词
            counts: 计数迭代器

        Yields:
            (word, total_count) 元组
        """
        total = sum(counts)
        yield (word, total)

    def process_stdin(self):
        """从stdin读取数据进行处理（Hadoop Streaming模式）"""
        current_word = None
        current_counts = []

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            parts = line.split('\t')
            if len(parts) != 2:
                continue

            word, count_str = parts
            try:
                count = int(count_str)
            except ValueError:
                continue

            if current_word == word:
                current_counts.append(count)
            else:
                if current_word is not None:
                    for word, total in self.reduce(current_word, iter(current_counts)):
                        print(f"{word}\t{total}")

                current_word = word
                current_counts = [count]

        # 处理最后一批
        if current_word is not None:
            for word, total in self.reduce(current_word, iter(current_counts)):
                print(f"{word}\t{total}")


class LocalWordFreqAnalyzer:
    """本地词频分析器（无需Hadoop环境）"""

    def __init__(self):
        self.mapper = WordFreqMapper()

    def analyze_file(self, filepath: str) -> Dict[str, int]:
        """分析JSON文件中的弹幕

        Args:
            filepath: 弹幕JSON文件路径

        Returns:
            词频统计字典
        """
        word_counts = defaultdict(int)

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 处理弹幕列表
        danmaku_list = data.get('danmaku_list', [])

        for danmaku in danmaku_list:
            text = danmaku.get('content', '')
            for word, count in self.mapper.map('', text):
                word_counts[word] += count

        return dict(word_counts)

    def analyze_sentiment(self, danmaku_list: List[Dict], sentiment_data: Dict) -> Dict[str, Any]:
        """结合情感分析进行词频统计

        Args:
            danmaku_list: 弹幕列表
            sentiment_data: 情感分析结果

        Returns:
            带情感标签的词频统计
        """
        word_sentiment_stats = defaultdict(lambda: {'pos': 0, 'neg': 0, 'neu': 0})

        # 创建弹幕索引
        danmaku_dict = {dm.get('content', ''): dm for dm in danmaku_list}

        # 处理情感详情
        for item in sentiment_data.get('details', []):
            content = item.get('content', '')
            sentiment = item.get('sentiment', 'neutral')

            # 分词
            words = self.mapper.tokenize(content)
            for word in words:
                word_sentiment_stats[word][sentiment] += 1

        return dict(word_sentiment_stats)

    def get_top_words(self, word_counts: Dict[str, int], top_n: int = 100) -> List[Dict[str, Any]]:
        """获取Top N高频词

        Args:
            word_counts: 词频统计
            top_n: 返回数量

        Returns:
            按频率排序的词列表
        """
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {'word': word, 'freq': freq}
            for word, freq in sorted_words[:top_n]
        ]


def main():
    import argparse

    parser = argparse.ArgumentParser(description='MapReduce词频统计工具')
    parser.add_argument('--mode', choices=['mapper', 'reducer', 'local', 'hbase'],
                        default='local', help='运行模式')
    parser.add_argument('--input', help='输入文件路径（local模式）')
    parser.add_argument('--output', help='输出文件路径')
    parser.add_argument('--bvid', help='视频BV号（hbase模式）')
    parser.add_argument('--limit', type=int, default=100, help='Top N词频')

    args = parser.parse_args()

    if args.mode == 'mapper':
        mapper = WordFreqMapper()
        mapper.process_stdin()

    elif args.mode == 'reducer':
        reducer = WordFreqReducer()
        reducer.process_stdin()

    elif args.mode == 'local':
        if not args.input:
            print("[ERROR] 请指定输入文件路径 --input")
            return

        analyzer = LocalWordFreqAnalyzer()
        word_counts = analyzer.analyze_file(args.input)

        top_words = analyzer.get_top_words(word_counts, top_n=args.limit)

        result = {
            'total_words': sum(word_counts.values()),
            'unique_words': len(word_counts),
            'top_100': top_words
        }

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"[INFO] 结果已保存到: {args.output}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.mode == 'hbase':
        print("[INFO] HBase模式需要配置Hadoop环境")
        # 这里可以集成HBase写入功能
        if args.bvid:
            print(f"[INFO] 准备处理视频: {args.bvid}")


if __name__ == '__main__':
    main()