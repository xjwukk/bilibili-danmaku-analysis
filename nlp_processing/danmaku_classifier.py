# -*- coding: utf-8 -*-
"""
弹幕类型分类
基于规则识别祝福类、玩梗类、刷屏类、提问类等不同类型弹幕
"""

import json
import os
import re
from collections import defaultdict

# ============================================================
# 配置路径
# ============================================================
BASE_DIR = 'F:/Claude project/大数据应用系统开发实践'
NLP_DIR = os.path.join(BASE_DIR, 'nlp_processing')
CLEANED_DATA_PATH = os.path.join(NLP_DIR, 'cleaned_danmaku.json')
OUTPUT_PATH = os.path.join(NLP_DIR, 'danmaku_classified.json')


# 弹幕类型关键词定义
DANMAKU_TYPE_KEYWORDS = {
    'bless': {
        'keywords': ['祝', '祝福', '生日', '好运', '顺利', '成功', '加油', '好运', '安康', '幸福',
                    '快乐', '发财', '金榜题名', '考研', '高考', '顺利', '健康', '平安'],
        'weight': 1.0
    },
    'meme': {
        'keywords': ['梗', '笑死', '哈哈', '233', '2333', '23333', '笑', '太秀', '秀', '优秀',
                    '骚操作', '离谱', '离谱', '神了', '绝了', '这也太', '真有你的', '绷不住'],
        'weight': 1.0
    },
    'spam': {
        'keywords': ['+1', '+2', '+3', '同上', '刷屏', '打卡', '占楼', '前排', '留名',
                    '来了', '报到', '签到', '路过', '刷', '刷屏', '疯狂', '一直'],
        'weight': 1.0
    },
    'question': {
        'keywords': ['？', '?', '为什么', '怎么', '如何', '啥意思', '什么意思', '这是',
                    '干嘛', '干什么', '谁', '哪里', '哪个', '怎样', '怎么样'],
        'weight': 1.0
    },
    'exclaim': {
        'keywords': ['太', '真', '好', '牛', '厉害', '强', '绝', '赞', '棒', '帅', '酷',
                    '哇', '呀', '啊', '哦', '噢', '天哪', '我的天', '我靠', '牛蛙'],
        'weight': 0.8  # 单独出现时权重降低
    },
    'idol': {
        'keywords': ['老婆', '老公', '喜欢', '爱', '男神', '女神', '宝贝', '宝贝', '我婆',
                    '我老公', '表白', '恋爱', '心动', ' crush'],
        'weight': 1.0
    },
    'learn': {
        'keywords': ['学习', '记', '笔记', '抄', '码住', '收藏', '记下了', '记住', '背',
                    '知识点', '重点', '考点', '干货', '有用', '实用'],
        'weight': 1.0
    },
    'negative': {
        'keywords': ['垃圾', '烂', '差', '无聊', '难看', '尴尬', '无语', '失望', '什么玩意',
                     '服了', '醉了', '呵呵', '弱', '废物', '智障'],
        'weight': 1.0
    }
}


def load_cleaned_data():
    """加载清洗后的弹幕数据"""
    with open(CLEANED_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['danmaku_list']


def classify_danmaku(content):
    """
    分类单条弹幕

    返回:
        弹幕类型列表（可能同时属于多种类型）
    """
    content = str(content).lower()
    matched_types = []

    for danmaku_type, type_info in DANMAKU_TYPE_KEYWORDS.items():
        keywords = type_info['keywords']
        weight = type_info['weight']

        match_count = 0
        for keyword in keywords:
            if keyword.lower() in content:
                match_count += 1

        if match_count > 0:
            matched_types.append({
                'type': danmaku_type,
                'match_count': match_count,
                'confidence': min(match_count * weight / 2, 1.0)  # 归一化置信度
            })

    # 如果没有匹配任何类型，默认为'normal'
    if not matched_types:
        matched_types.append({
            'type': 'normal',
            'match_count': 0,
            'confidence': 1.0
        })

    # 按置信度排序
    matched_types.sort(key=lambda x: x['confidence'], reverse=True)

    return matched_types


def analyze_danmaku_types(danmaku_list):
    """
    分析弹幕类型分布

    参数:
        danmaku_list: 弹幕列表

    返回:
        type_analysis: 弹幕类型分析结果
    """
    print('\n[弹幕类型分类分析]')

    # 分类每条弹幕
    type_counts = defaultdict(int)
    type_details = defaultdict(list)

    for d in danmaku_list:
        content = d.get('content', '')
        timestamp = d.get('timestamp', 0)

        classifications = classify_danmaku(content)

        # 取最高置信度的类型作为主类型
        primary_type = classifications[0]['type']
        type_counts[primary_type] += 1

        # 记录部分详情
        if len(type_details[primary_type]) < 10:
            type_details[primary_type].append({
                'content': content,
                'timestamp': timestamp,
                'confidence': classifications[0]['confidence']
            })

    # 计算分布比例
    total = len(danmaku_list)
    type_distribution = {}
    for danmaku_type, count in type_counts.items():
        type_distribution[danmaku_type] = {
            'count': count,
            'ratio': round(count / total * 100, 2) if total > 0 else 0
        }

    # 按数量排序
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)

    # 类型标签映射
    type_labels = {
        'bless': '祝福类',
        'meme': '玩梗类',
        'spam': '刷屏类',
        'question': '提问类',
        'exclaim': '感叹类',
        'idol': '追星类',
        'learn': '学习类',
        'negative': '负面类',
        'normal': '普通类'
    }

    # 构建结果
    result = {
        'total_danmaku': total,
        'type_distribution': type_distribution,
        'top_types': [
            {
                'type': danmaku_type,
                'label': type_labels.get(danmaku_type, danmaku_type),
                'count': count,
                'ratio': round(count / total * 100, 2) if total > 0 else 0,
                'sample_danmaku': type_details.get(danmaku_type, [])[:5]
            }
            for danmaku_type, count in sorted_types
        ],
        'multi_label_stats': {
            'single_type': 0,
            'multi_type': 0
        }
    }

    # 打印结果
    print(f'    总弹幕数: {total}')
    print(f'    类型分布:')
    for danmaku_type, count in sorted_types:
        label = type_labels.get(danmaku_type, danmaku_type)
        ratio = round(count / total * 100, 2) if total > 0 else 0
        print(f'        {label}: {count}条 ({ratio}%)')

    return result


def main():
    print('=' * 70)
    print('弹幕类型分类')
    print('=' * 70)

    # 加载数据
    print('\n[1] 加载弹幕数据...')
    danmaku_list = load_cleaned_data()
    print(f'    弹幕数量: {len(danmaku_list)}')

    # 分类分析
    result = analyze_danmaku_types(danmaku_list)

    # 保存结果
    print(f'\n[2] 保存结果...')
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'    结果已保存: {OUTPUT_PATH}')

    print('\n' + '=' * 70)
    print('弹幕类型分类完成!')
    print('=' * 70)

    return result


if __name__ == '__main__':
    main()
