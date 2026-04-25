# -*- coding: utf-8 -*-
"""
弹幕数据清洗模块
功能：过滤特殊符号、emoji、空白字符；去除无意义弹幕；繁简体转换；去重；长度过滤
"""

import json
import re
import os
from collections import Counter

# ============================================================
# 1. 停用词表（从cn_stopwords.txt加载）
# ============================================================
def load_stopwords():
    """从cn_stopwords.txt加载停用词"""
    base_dir = 'F:/Claude project/大数据应用系统开发实践'
    nlp_dir = os.path.join(base_dir, 'agent2_nlp')
    stopwords_file = os.path.join(nlp_dir, 'cn_stopwords.txt')
    stopwords = set()
    if os.path.exists(stopwords_file):
        with open(stopwords_file, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word and not word.startswith('$'):
                    stopwords.add(word)
    # 添加弹幕常见无意义词汇
    extra = {
        '2333', '233', '666', '哈哈哈', '笑死', '真的', '其实', '觉得', '应该',
        '可能', '不过', '而且', '所以', '但是', '如果', '虽然', '因为', '就是',
    }
    stopwords.update(extra)
    return stopwords

STOPWORDS = load_stopwords()

# ============================================================
# 2. 正则表达式模式
# ============================================================
# 特殊符号和emoji
SPECIAL_CHARS_PATTERN = re.compile(
    r'[\U00010000-\U0010ffff]'  # emoji
    r'|[\u2100-\u214F]'         # 字母符号
    r'|[\u2190-\u21FF]'         # 箭头
    r'|[\u2600-\u26FF]'         # 杂项符号
    r'|[\u2700-\u27BF]'         # 装饰符号
    r'|[\u3000-\u303F]'         # CJK符号
    r'|[\uFE00-\uFE0F]'         # 选择符
    r'|[\U0001F000-\U0001F9FF]'  # 表情符号 (Emoji)
    r'|[\U000E0000-\U000E007F]'  # 标签符号
)

# 空白字符
WHITESPACE_PATTERN = re.compile(r'\s+')

# 纯数字
PURE_NUMBER_PATTERN = re.compile(r'^[\d\s.,%]+$')

# 纯符号（弹幕中常见）
PURE_SYMBOL_PATTERN = re.compile(r'^[，。！？：；""''【】『』()（）·~`@#$%^&*_+=|\\/<>-]+$')


def load_danmaku(json_path):
    """加载弹幕数据"""
    with open(json_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    return data['danmaku_list']


def remove_special_chars(text):
    """去除特殊符号和emoji"""
    text = SPECIAL_CHARS_PATTERN.sub('', text)
    text = WHITESPACE_PATTERN.sub(' ', text)
    return text.strip()


def is_meaningful(text):
    """判断弹幕是否有意义"""
    if not text or len(text.strip()) == 0:
        return False
    if PURE_NUMBER_PATTERN.match(text):
        return False
    if PURE_SYMBOL_PATTERN.match(text):
        return False
    if len(text) < 2:  # 去除超短弹幕
        return False
    if len(text) > 100:  # 去除超长弹幕
        return False
    return True


def convert_to_simple(text):
    """简繁体转换（简->繁；繁->简）"""
    # 使用简单的字符映射进行繁简转换
    # 这里使用一个简化的映射表
    conv_table = {
        '網': '网', '電': '电', '雲': '云', '語': '语', '數': '数',
        '據': '据', '開': '开', '發': '发', '開': '发', '發': '发',
        '會': '会', '對': '对', '們': '们', '過': '过', '時': '时',
        '間': '间', '說': '说', '請': '请', '這': '这', '個': '个',
        '種': '种', '樣': '样', '樣': '样', '關': '关', '機': '机',
        '場': '场', '問題': '问题', '資訊': '资讯',
    }
    # 简化处理：如果字符在转换表中则转换，否则保持原样
    result = []
    for char in text:
        result.append(conv_table.get(char, char))
    return ''.join(result)


def clean_danmaku(danmaku_list):
    """
    数据清洗主函数

    参数:
        danmaku_list: 弹幕列表

    返回:
        cleaned_list: 清洗后的弹幕列表
        stats: 统计数据
    """
    stats = {
        'total_input': len(danmaku_list),
        'after_length_filter': 0,
        'after_meaningful_filter': 0,
        'after_dedup': 0,
        'removed_special': 0,
        'removed_short': 0,
        'removed_long': 0,
        'removed_number': 0,
        'removed_symbol': 0,
    }

    cleaned = []

    for item in danmaku_list:
        content = item.get('content', '')

        # 去除特殊字符和emoji
        original_len = len(content)
        content = remove_special_chars(content)
        if len(content) != original_len:
            stats['removed_special'] += 1

        # 跳过空内容
        if not content:
            continue

        stats['after_length_filter'] += 1

        # 判断是否有意义
        if not is_meaningful(content):
            if PURE_NUMBER_PATTERN.match(content):
                stats['removed_number'] += 1
            elif PURE_SYMBOL_PATTERN.match(content):
                stats['removed_symbol'] += 1
            elif len(content) < 2:
                stats['removed_short'] += 1
            elif len(content) > 100:
                stats['removed_long'] += 1
            continue

        stats['after_meaningful_filter'] += 1

        # 繁简转换
        content = convert_to_simple(content)

        # 添加清洗后的内容
        cleaned.append({
            'content': content,
            'timestamp': item.get('timestamp', 0),
            'type': item.get('type', 1),
        })

    # 去重（基于内容）
    seen = set()
    unique_danmaku = []
    for item in cleaned:
        if item['content'] not in seen:
            seen.add(item['content'])
            unique_danmaku.append(item)

    stats['after_dedup'] = len(unique_danmaku)

    return unique_danmaku, stats


def save_cleaned_data(cleaned_list, output_path):
    """保存清洗后的弹幕数据"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({'danmaku_list': cleaned_list}, f, ensure_ascii=False, indent=2)


def main():
    """主函数"""
    # 路径配置
    base_dir = 'F:/Claude project/大数据应用系统开发实践'
    input_path = os.path.join(base_dir, 'agent1_crawler/bilibili_data.json')
    output_dir = os.path.join(base_dir, 'agent2_nlp')
    output_path = os.path.join(output_dir, 'cleaned_danmaku.json')

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    print('=' * 60)
    print('弹幕数据清洗模块')
    print('=' * 60)

    # 1. 加载弹幕
    print('\n[1] 加载弹幕数据...')
    danmaku_list = load_danmaku(input_path)
    print(f'    加载弹幕数量: {len(danmaku_list)}')

    # 2. 数据清洗
    print('\n[2] 数据清洗中...')
    cleaned_list, stats = clean_danmaku(danmaku_list)

    # 3. 打印统计信息
    print('\n[3] 清洗统计:')
    print(f'    输入弹幕总数: {stats["total_input"]}')
    print(f'    去除特殊字符/Emoji: {stats["removed_special"]}')
    print(f'    去除纯数字弹幕: {stats["removed_number"]}')
    print(f'    去除纯符号弹幕: {stats["removed_symbol"]}')
    print(f'    去除超短弹幕: {stats["removed_short"]}')
    print(f'    去除超长弹幕: {stats["removed_long"]}')
    print(f'    有效弹幕数量: {stats["after_meaningful_filter"]}')
    print(f'    去重后弹幕数量: {stats["after_dedup"]}')

    # 4. 保存结果
    print(f'\n[4] 保存清洗结果到: {output_path}')
    save_cleaned_data(cleaned_list, output_path)

    print('\n' + '=' * 60)
    print('数据清洗完成!')
    print('=' * 60)

    return cleaned_list, stats


if __name__ == '__main__':
    cleaned_list, stats = main()