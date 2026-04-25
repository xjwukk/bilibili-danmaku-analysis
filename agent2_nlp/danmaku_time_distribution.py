# -*- coding: utf-8 -*-
"""
弹幕时间分布分析
分析弹幕在视频各时间段的分布密度，识别弹幕高发时段
"""

import json
import os
from collections import defaultdict
from datetime import datetime

# ============================================================
# 配置路径
# ============================================================
BASE_DIR = 'F:/Claude project/大数据应用系统开发实践'
NLP_DIR = os.path.join(BASE_DIR, 'agent2_nlp')
CLEANED_DATA_PATH = os.path.join(NLP_DIR, 'cleaned_danmaku.json')
OUTPUT_PATH = os.path.join(NLP_DIR, 'danmaku_time_distribution.json')


def load_cleaned_data():
    """加载清洗后的弹幕数据"""
    with open(CLEANED_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['danmaku_list']


def analyze_time_distribution(danmaku_list, bucket_size=30):
    """
    分析弹幕时间分布

    参数:
        danmaku_list: 弹幕列表
        bucket_size: 时间桶大小（秒），默认30秒

    返回:
        time_distribution: 时间分布分析结果
    """
    print('\n[弹幕时间分布分析]')

    # 按时间戳分桶统计
    time_buckets = defaultdict(list)

    for d in danmaku_list:
        timestamp = d.get('timestamp', 0)
        if timestamp <= 0:
            continue

        # 计算所属时间桶
        bucket_idx = int(timestamp / bucket_size)

        # 收集该时间桶的弹幕
        time_buckets[bucket_idx].append({
            'content': d.get('content', ''),
            'timestamp': timestamp,
            'pool': d.get('pool', 0),
            'mode': d.get('mode', 0),
        })

    # 计算每个时间桶的弹幕数量
    bucket_counts = {k: len(v) for k, v in time_buckets.items()}

    # 排序
    sorted_buckets = sorted(bucket_counts.items(), key=lambda x: x[0])

    # 找出高密度时段（top 20%）
    if sorted_buckets:
        counts = [c for _, c in sorted_buckets]
        threshold = sorted(counts, reverse=True)[len(counts) // 5] if len(counts) > 5 else counts[0]
        high_density_buckets = [
            {'time_bucket': bucket_idx, 'count': count, 'time_seconds': bucket_idx * bucket_size}
            for bucket_idx, count in sorted_buckets if count >= threshold
        ]
    else:
        high_density_buckets = []

    # 计算统计信息
    total_buckets = len(sorted_buckets)
    total_danmaku = sum(c for _, c in sorted_buckets)
    avg_per_bucket = total_danmaku / total_buckets if total_buckets > 0 else 0

    # 时间分布直方图数据（每60秒一个桶，便于前端显示）
    histogram_buckets = defaultdict(int)
    for d in danmaku_list:
        timestamp = d.get('timestamp', 0)
        if timestamp <= 0:
            continue
        bucket_idx = int(timestamp / 60)  # 60秒桶
        histogram_buckets[bucket_idx] += 1

    # 转换为前端可用格式
    histogram_data = [
        {'time_bucket': k * 60, 'count': v, 'time_label': f"{k//60}:{k%60:02d}"}
        for k, v in sorted(histogram_buckets.items())
    ]

    # 按时长分组统计
    video_segments = {
        '0-5min': 0,
        '5-10min': 0,
        '10-15min': 0,
        '15-20min': 0,
        '20min+': 0
    }

    for bucket_idx, count in sorted_buckets:
        seconds = bucket_idx * bucket_size
        minutes = seconds / 60
        if minutes < 5:
            video_segments['0-5min'] += count
        elif minutes < 10:
            video_segments['5-10min'] += count
        elif minutes < 15:
            video_segments['10-15min'] += count
        elif minutes < 20:
            video_segments['15-20min'] += count
        else:
            video_segments['20min+'] += count

    result = {
        'total_danmaku': total_danmaku,
        'bucket_size_seconds': bucket_size,
        'total_buckets': total_buckets,
        'avg_per_bucket': round(avg_per_bucket, 2),
        'high_density_buckets': high_density_buckets[:20],  # 最多20个高密度时段
        'time_segments': video_segments,
        'histogram_data': histogram_data,
        'peak_bucket': {
            'time_seconds': sorted_buckets[0][0] * bucket_size if sorted_buckets else 0,
            'count': sorted_buckets[0][1] if sorted_buckets else 0
        } if sorted_buckets else None
    }

    # 打印分析结果
    print(f'    总弹幕数: {total_danmaku}')
    print(f'    时间桶数: {total_buckets}')
    print(f'    平均每桶: {avg_per_bucket:.1f}条')
    print(f'    高密度时段数: {len(high_density_buckets)}')
    print(f'    时段分布: {video_segments}')
    if sorted_buckets:
        peak = sorted_buckets[0]
        peak_time = peak[0] * bucket_size
        print(f'    弹幕最密集: {peak_time//60:.0f}分{peak_time%60:.0f}秒 ({peak[1]}条)')

    return result


def main():
    print('=' * 70)
    print('弹幕时间分布分析')
    print('=' * 70)

    # 加载数据
    print('\n[1] 加载弹幕数据...')
    danmaku_list = load_cleaned_data()
    print(f'    弹幕数量: {len(danmaku_list)}')

    # 分析时间分布
    result = analyze_time_distribution(danmaku_list)

    # 保存结果
    print(f'\n[2] 保存结果...')
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'    结果已保存: {OUTPUT_PATH}')

    print('\n' + '=' * 70)
    print('时间分布分析完成!')
    print('=' * 70)

    return result


if __name__ == '__main__':
    main()
