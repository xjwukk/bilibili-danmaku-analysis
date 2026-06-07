# -*- coding: utf-8 -*-
"""
分词模块升级版
使用pkuseg替代jieba，提供更精确的中文分词

pkuseg 是北京大学开发的基于条件随机场(CRF)的中文分词工具
在多个公开数据集上分词准确率高于jieba
"""

import json
import os
import re
from collections import Counter

# ============================================================
# 配置路径
# ============================================================
BASE_DIR = 'F:/Claude project/大数据应用系统开发实践'
NLP_DIR = os.path.join(BASE_DIR, 'nlp_processing')
CLEANED_DATA_PATH = os.path.join(NLP_DIR, 'cleaned_danmaku.json')

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
    extra_stopwords = {
        '2333', '233', '666', '哈哈哈', '笑死', '真的', '其实', '觉得', '应该',
        '可能', '不过', '而且', '所以', '但是', '如果', '虽然', '因为', '就是',
        '不是', '这种', '那种', '什么的', '为什么', '怎么样', '多少', '哪些',
    }
    stopwords.update(extra_stopwords)
    print(f'[加载停用词] 共{len(stopwords)}个')
    return stopwords

STOPWORDS = load_stopwords()

# ============================================================
# pkuseg 分词器初始化
# ============================================================
def get_pkuseg_segmenter():
    """获取pkuseg分词器实例"""
    try:
        import pkuseg
        seg = pkuseg.pkuseg()
        print('[pkuseg 分词器初始化成功]')
        return seg
    except ImportError:
        print('[pkuseg 未安装，回退到jieba]')
        return None
    except Exception as e:
        print(f'[pkuseg 初始化失败: {e}，回退到jieba]')
        return None


def get_jieba_segmenter():
    """获取jieba分词器（备用）"""
    import jieba
    import jieba.posseg as pseg
    print('[jieba 分词器初始化成功]')
    return jieba, pseg


# ============================================================
# 分词与词性标注（pkuseg版本）
# ============================================================
class Segmenter:
    """统一分词接口，支持pkuseg和jieba自动切换"""

    def __init__(self):
        self.pkuseg_seg = get_pkuseg_segmenter()
        if self.pkuseg_seg is None:
            self.jieba_seg, self.jieba_posseg = get_jieba_segmenter()
            self.use_pkuseg = False
        else:
            self.use_pkuseg = True

    def cut(self, text):
        """分词"""
        if self.use_pkuseg:
            return self.pkuseg_seg.cut(text)
        else:
            return self.jieba_seg.cut(text)

    def cut_with_pos(self, text):
        """分词+词性标注（pkuseg版本更精确）"""
        if self.use_pkuseg:
            # pkuseg 的词性标注
            words_pos = self.pkuseg_seg.cut(text)
            result = []
            for wp in words_pos:
                if isinstance(wp, tuple):
                    result.append(wp)
                else:
                    # 某些版本返回单字符串
                    result.append((wp, 'n'))  # 默认词性为名词
            return result
        else:
            # jieba 词性标注
            words = self.jieba_posseg.cut(text)
            return [(w.word, w.flag) for w in words]


# ============================================================
# 加载数据
# ============================================================
def load_cleaned_data():
    """加载清洗后的弹幕数据"""
    with open(CLEANED_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['danmaku_list']


# ============================================================
# 分词主函数
# ============================================================
def segment_texts(danmaku_list, use_pkuseg=True):
    """
    对弹幕列表进行分词

    参数:
        danmaku_list: 弹幕列表
        use_pkuseg: 是否优先使用pkuseg

    返回:
        valid_words: 有效词汇列表
        words_with_pos: 带词性的词汇列表
    """
    print(f'\n[分词处理] 使用模型: {"pkuseg" if use_pkuseg else "jieba"}')

    segmenter = Segmenter()
    valid_words = []
    words_with_pos = []

    for item in danmaku_list:
        try:
            content = item['content']
            if not content or len(content.strip()) == 0:
                continue

            # 分词
            words_pos = segmenter.cut_with_pos(content)

            for word, pos in words_pos:
                word = word.strip()
                if not word or len(word) < 2:
                    continue
                if word in STOPWORDS:
                    continue
                # 过滤纯数字和符号
                if re.match(r'^[\d\s.,%]+$', word):
                    continue
                if re.match(r'^[，。！？：；""''【】『』()（）·~`@#$%^&*_+=|\\/<>-]+$', word):
                    continue

                valid_words.append(word)
                words_with_pos.append((word, pos))

        except Exception as e:
            continue

    print(f'    分词后有效词汇数: {len(valid_words)}')
    return valid_words, words_with_pos


# ============================================================
# 词频统计
# ============================================================
def word_frequency_analysis(valid_words, top_n=50):
    """
    词频统计

    返回:
        word_freq: Counter对象
    """
    print('\n[词频统计]')
    word_freq = Counter(valid_words)

    print(f'    Top {top_n} 高频词:')
    for i, (word, freq) in enumerate(word_freq.most_common(top_n), 1):
        print(f'    {i:2d}. {word}: {freq}')

    return word_freq


# ============================================================
# 词性分布统计
# ============================================================
def pos_distribution_analysis(words_with_pos):
    """
    词性分布统计

    参数:
        words_with_pos: [(word, pos), ...]

    返回:
        pos_stats: 词性统计
    """
    print('\n[词性分布统计]')

    pos_counter = Counter([pos for _, pos in words_with_pos])
    total = len(words_with_pos)

    print(f'    词性分布 (Top 10):')
    for pos, count in pos_counter.most_common(10):
        ratio = count / total * 100 if total > 0 else 0
        print(f'        {pos}: {count} ({ratio:.2f}%)')

    return {
        'total': total,
        'pos_distribution': dict(pos_counter.most_common(20)),
        'unique_words': len(set([w for w, _ in words_with_pos]))
    }


# ============================================================
# 主函数
# ============================================================
def main():
    print('=' * 70)
    print('分词模块 (pkuseg 升级版)')
    print('=' * 70)

    # 加载数据
    print('\n[1] 加载弹幕数据...')
    danmaku_list = load_cleaned_data()
    print(f'    弹幕数量: {len(danmaku_list)}')

    # 分词
    valid_words, words_with_pos = segment_texts(danmaku_list)

    # 词频统计
    word_freq = word_frequency_analysis(valid_words, top_n=50)

    # 词性分布
    pos_stats = pos_distribution_analysis(words_with_pos)

    # 保存词频结果
    wordfreq_path = os.path.join(NLP_DIR, 'wordfreq_pkuseg.json')
    wordfreq_data = {
        'total_words': len(valid_words),
        'unique_words': pos_stats['unique_words'],
        'segmenter': 'pkuseg',
        'top_100': [{'word': w, 'freq': f} for w, f in word_freq.most_common(100)],
    }
    with open(wordfreq_path, 'w', encoding='utf-8') as f:
        json.dump(wordfreq_data, f, ensure_ascii=False, indent=2)
    print(f'\n    词频统计已保存: {wordfreq_path}')

    print('\n' + '=' * 70)
    print('分词处理完成!')
    print('=' * 70)

    return {
        'valid_words': valid_words,
        'words_with_pos': words_with_pos,
        'word_freq': word_freq
    }


if __name__ == '__main__':
    main()
