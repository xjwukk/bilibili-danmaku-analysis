# -*- coding: utf-8 -*-
"""
实体识别模块 (NER)
基于词性标注和规则抽取人名、地名、机构名等实体

使用jieba的词性标注功能进行实体识别：
- nr: 人名
- ns: 地名
- nt: 机构名
- nz: 其他专名
"""

import json
import os
import re
from collections import Counter, defaultdict

# ============================================================
# 配置路径
# ============================================================
BASE_DIR = 'F:/Claude project/大数据应用系统开发实践'
NLP_DIR = os.path.join(BASE_DIR, 'nlp_processing')
CLEANED_DATA_PATH = os.path.join(NLP_DIR, 'cleaned_danmaku.json')
OUTPUT_PATH = os.path.join(NLP_DIR, 'ner_entities.json')

# ============================================================
# 停用词表
# ============================================================
def load_stopwords():
    """从cn_stopwords.txt加载停用词"""
    stopwords_file = os.path.join(NLP_DIR, 'cn_stopwords.txt')
    stopwords = set()
    if os.path.exists(stopwords_file):
        with open(stopwords_file, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word and not word.startswith('$'):
                    stopwords.add(word)
    return stopwords

STOPWORDS = load_stopwords()


# ============================================================
# 实体识别器
# ============================================================
class NERecognizer:
    """基于词性标注的命名实体识别器"""

    def __init__(self):
        import jieba
        import jieba.posseg as pseg
        self.jieba = jieba
        self.pseg = pseg

        # 弹幕中常见的实体类型关键词
        self.entity_keywords = {
            'person': ['老师', '同学', '老板', '小哥', '大哥', 'up主', 'up', '主播',
                      '小哥哥', '小姐姐', '小可爱', '大佬', '神人', '天才', '凡人'],
            'location': ['中国', '美国', '日本', '韩国', '北京', '上海', '深圳', '杭州',
                        '广州', '成都', '武汉', '西安', '南京', '东京', '纽约', '硅谷'],
            'organization': ['谷歌', 'Google', '微软', 'Microsoft', '苹果', 'Apple', '阿里',
                            '腾讯', '百度', '字节', 'OpenAI', 'B站', 'bilibili', '斯坦福'],
            'product': ['手机', '电脑', 'iPhone', 'Android', 'Windows', 'Mac', 'MacBook',
                       'ChatGPT', 'GPT', 'AI', '模型', '芯片', '显卡', 'CPU', 'GPU'],
            'tech': ['AI', '人工智能', '机器学习', '深度学习', '神经网络', 'NLP', 'CV',
                    'OpenClaw', 'Openclaw', 'openclaw', 'Claude', 'GPT', 'BERT']
        }

        print('[实体识别器初始化完成]')

    def extract_entities(self, text):
        """
        从文本中抽取实体

        返回:
            entities: {'person': [...], 'location': [...], ...}
        """
        entities = {
            'person': [],
            'location': [],
            'organization': [],
            'product': [],
            'tech': [],
            'other': []
        }

        # 使用jieba词性标注
        words_pos = self.pseg.cut(text)

        for word, flag in words_pos:
            word = word.strip()
            if not word or len(word) < 2:
                continue
            if word in STOPWORDS:
                continue

            # 根据词性分类
            if flag == 'nr':  # 人名
                entities['person'].append(word)
            elif flag == 'ns':  # 地名
                entities['location'].append(word)
            elif flag == 'nt':  # 机构名
                entities['organization'].append(word)
            elif flag == 'nz':  # 其他专名
                entities['other'].append(word)

            # 根据关键词分类
            for entity_type, keywords in self.entity_keywords.items():
                if word in keywords and word not in entities[entity_type]:
                    entities[entity_type].append(word)

        return entities

    def analyze_danmaku(self, danmaku_list):
        """
        分析弹幕列表中的实体

        返回:
            entity_stats: 实体统计
        """
        print('\n[实体识别分析]')

        all_entities = {
            'person': [],
            'location': [],
            'organization': [],
            'product': [],
            'tech': [],
            'other': []
        }

        danmaku_with_entities = []

        for i, item in enumerate(danmaku_list):
            content = item.get('content', '')
            if not content:
                continue

            entities = self.extract_entities(content)

            # 收集所有实体
            for entity_type, words in entities.items():
                all_entities[entity_type].extend(words)

            # 记录包含实体的弹幕
            total_entities = sum(len(words) for words in entities.values())
            if total_entities > 0:
                danmaku_with_entities.append({
                    'content': content,
                    'timestamp': item.get('timestamp', 0),
                    'entities': {k: list(set(v)) for k, v in entities.items() if v}
                })

            if (i + 1) % 500 == 0:
                print(f'    已处理: {i + 1}/{len(danmaku_list)}')

        # 统计实体频率
        entity_stats = {}
        for entity_type, words in all_entities.items():
            if words:
                word_freq = Counter(words)
                entity_stats[entity_type] = {
                    'count': len(words),
                    'unique_count': len(word_freq),
                    'top_entities': dict(word_freq.most_common(30))
                }

        # 计算含实体弹幕比例
        entity_danmaku_count = len(danmaku_with_entities)
        entity_ratio = entity_danmaku_count / len(danmaku_list) * 100 if danmaku_list else 0

        result = {
            'total_danmaku': len(danmaku_list),
            'danmaku_with_entities': entity_danmaku_count,
            'entity_ratio': round(entity_ratio, 2),
            'entity_stats': entity_stats,
            'sample_danmaku': danmaku_with_entities[:20]
        }

        print(f'    总弹幕数: {len(danmaku_list)}')
        print(f'    含实体弹幕: {entity_danmaku_count} ({entity_ratio:.1f}%)')
        for entity_type, stats in entity_stats.items():
            print(f'        {entity_type}: {stats["unique_count"]}种, {stats["count"]}次')

        return result


# ============================================================
# 加载数据
# ============================================================
def load_cleaned_data():
    """加载清洗后的弹幕数据"""
    with open(CLEANED_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['danmaku_list']


# ============================================================
# 主函数
# ============================================================
def main():
    print('=' * 70)
    print('实体识别 (NER) 模块')
    print('=' * 70)

    # 加载数据
    print('\n[1] 加载弹幕数据...')
    danmaku_list = load_cleaned_data()
    print(f'    弹幕数量: {len(danmaku_list)}')

    # 实体识别
    print('\n[2] 实体识别...')
    recognizer = NERecognizer()
    result = recognizer.analyze_danmaku(danmaku_list)

    # 保存结果
    print(f'\n[3] 保存结果...')
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'    结果已保存: {OUTPUT_PATH}')

    print('\n' + '=' * 70)
    print('实体识别完成!')
    print('=' * 70)

    return result


if __name__ == '__main__':
    main()
