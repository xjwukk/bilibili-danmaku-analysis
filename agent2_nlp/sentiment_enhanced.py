# -*- coding: utf-8 -*-
"""
情感分析增强模块
基于规则+词典+否定处理的增强版情感分析

改进点：
1. 否定词处理（不、没有、未...）
2. 程度副词处理（非常、很、太、有点...）
3. 表情符号识别
4. 标点符号分析（感叹号、问号）
5. 复杂句式处理（转折、因果）
"""

import json
import os
import re
from collections import Counter

# ============================================================
# 配置路径
# ============================================================
BASE_DIR = 'F:/Claude project/大数据应用系统开发实践'
NLP_DIR = os.path.join(BASE_DIR, 'agent2_nlp')
CLEANED_DATA_PATH = os.path.join(NLP_DIR, 'cleaned_danmaku.json')
OUTPUT_PATH = os.path.join(NLP_DIR, 'sentiment_enhanced.json')

# ============================================================
# 否定词表
# ============================================================
NEGATION_WORDS = {
    '不', '没', '无', '别', '非', '否', '莫', '勿', '未', '甭',
    '不会', '不能', '不是', '没是', '不需要', '不要', '别要',
    '不太', '不够', '未', '莫', '非', '休', '勿', '未曾'
}

# 双重否定表（表示肯定）
DOUBLE_NEGATION = {
    '不得不', '不能不', '不可不', '不会不', '不是不', '没理由不'
}

# ============================================================
# 程度副词表
# ============================================================
INTENSITY_MODIFIERS = {
    # 极强（权重2.0）
    '极其': 2.0, '极为': 2.0, '极度': 2.0, '极端': 2.0, '至': 2.0, '最': 2.0,
    '超级': 2.0, '无比': 2.0, '绝对': 2.0, '相当': 2.0,

    # 强（权重1.5）
    '非常': 1.5, '很': 1.5, '特别': 1.5, '十分': 1.5, '尤其': 1.5,
    '格外': 1.5, '分外': 1.5, '太': 1.5, '真': 1.3, '着实': 1.5,

    # 中等（权重1.2）
    '比较': 1.2, '较': 1.2, '挺': 1.2, '蛮': 1.2, '相当': 1.2, '较为': 1.2,

    # 弱（权重0.8）
    '有点': 0.8, '稍微': 0.8, '一点': 0.8, '有些': 0.8, '略': 0.8,
    '不太': 0.7, '不怎么': 0.7, '不太': 0.7, '不怎么': 0.7
}

# ============================================================
# 情感词典
# ============================================================
POSITIVE_WORDS = {
    # 基础正面词
    '好', '棒', '强', '厉害', '牛', '赞', '支持', '喜欢', '爱', '酷', '帅',
    '优秀', '精彩', '完美', '聪明', '开心', '有趣', '期待', '希望', '满分',
    '神', '神仙', '天使', '超棒', '超级棒', '碉堡', '炸裂', '太强', '太牛',
    '佩服', '膜拜', '顶', '收藏', '转发', '点赞', '打卡', '学习', '实用',

    # 进阶正面词
    'nb', '牛逼', '绝了', '太棒', '真好', '不错', '神仙', '炸', '秀', '太秀',
    '奥利给', '给力', '硬核', '硬核', '牛蛙', '牛批', 'nice', '奈斯',
    '可以', '靠谱', '良心', '必看', '马克', '马住', '码住', '记下了',
    '干货', '有用', '受益', '学到了', '涨知识', '科普', '清楚', '清晰',

    # 网络用语
    '笑死', '笑喷', '笑抽', '哈哈哈', '233', '2333', '23333', '笑死我',
    '绷不住', '破防', '上头', '离谱', '离谱了', '牛啊', '厉害', '可',
    '可以', '可太', '可太牛', '我的天', '天哪', '哇塞', '牛蛙', '牛批'
}

NEGATIVE_WORDS = {
    # 基础负面词
    '烂', '差', '垃圾', '废物', '蠢', '傻', '笨', '无聊', '难听', '难看', '尴尬',
    '无语', '失望', '坑', '骗', '假', '恶心', '吐', '弱', '呵呵', '无奈',
    '遗憾', '可惜', '悲剧', '什么鬼', '有毒', '服了', '服气', '醉了', '扯淡',

    # 进阶负面词
    '辣鸡', '垃圾', '废物', '智障', '脑残', '小学生', '幼儿园', '博士后',
    '有毒', '巨坑', '大坑', '血亏', '亏死', '悔', '后悔', '可惜', '悲哀',
    '惨', '太惨', '完蛋', '炸裂', '崩', '崩了', '烂透', '烂穿', '一文不值',

    # 网络用语
    '呵呵呵', '我吐', '服了', '服了', '我伙呆', '惊呆了', '震惊',
    '可怕', '吓人', '瑟瑟发抖', '危险', '危险了', '凉了', '要凉'
}

# ============================================================
# 表情符号映射
# ============================================================
EMOTICONS = {
    # 正面表情
    '😊': 0.8, '😄': 0.8, '👍': 0.8, '❤️': 0.8, '💕': 0.8, '😍': 0.9,
    '🥰': 0.9, '😘': 0.9, '🤩': 0.9, '😎': 0.7, '🤗': 0.7, '🙂': 0.6,
    '✨': 0.7, '🎉': 0.8, '🎊': 0.8, '👏': 0.8, '🤝': 0.7,

    # 负面表情
    '😢': -0.6, '😭': -0.8, '😞': -0.7, '😠': -0.8, '😡': -0.9,
    '👎': -0.8, '💔': -0.7, '😱': -0.7, '😨': -0.8, '🤮': -0.9,
    '😤': -0.7, '🙄': -0.5, '😒': -0.5, '🤨': -0.4, '😐': -0.2,

    # 中性/疑问
    '🤔': 0.0, '❓': 0.0, '⁉️': 0.0, '💭': 0.0, '😐': 0.0
}

# ============================================================
# 情感分析器
# ============================================================
class EnhancedSentimentAnalyzer:
    """增强版情感分析器"""

    def __init__(self):
        print('[增强版情感分析器初始化]')
        print(f'    正面词: {len(POSITIVE_WORDS)}个')
        print(f'    负面词: {len(NEGATIVE_WORDS)}个')
        print(f'    否定词: {len(NEGATION_WORDS)}个')
        print(f'    程度词: {len(INTENSITY_MODIFIERS)}个')

    def preprocess(self, text):
        """预处理文本"""
        # 移除多余空格
        text = re.sub(r'\s+', '', text)
        return text

    def find_pattern(self, text, pattern):
        """查找模式"""
        return re.search(pattern, text)

    def calculate_emoticon_score(self, text):
        """计算表情符号得分"""
        score = 0
        for emoticon, value in EMOTICONS.items():
            if emoticon in text:
                score += value
        return score

    def calculate_punctuation_score(self, text):
        """计算标点符号得分"""
        score = 0

        # 感叹号（增强情感）
        exclamation_count = text.count('！') + text.count('!')
        question_count = text.count('？') + text.count('?')

        # 多个感叹号表示强烈情感
        if exclamation_count >= 3:
            score += 0.5
        elif exclamation_count >= 1:
            score += 0.2

        # 问号可能表示疑惑/负面
        if question_count >= 2:
            score -= 0.3
        elif question_count == 1:
            score -= 0.1

        return score

    def analyze_word_sentiment(self, words):
        """
        分析词语情感（考虑否定词和程度词）

        返回:
            (positive_score, negative_score)
        """
        pos_score = 0
        neg_score = 0

        i = 0
        while i < len(words):
            word = words[i]
            next_word = words[i + 1] if i + 1 < len(words) else ''

            # 检查否定词
            is_negated = word in NEGATION_WORDS

            # 检查程度词
            intensity = 1.0
            if word in INTENSITY_MODIFIERS:
                intensity = INTENSITY_MODIFIERS[word]
                i += 1
                word = next_word
                next_word = words[i + 1] if i + 1 < len(words) else ''

            # 检查情感词
            if word in POSITIVE_WORDS:
                if is_negated:
                    neg_score += intensity  # 否定正面词
                else:
                    pos_score += intensity
            elif word in NEGATIVE_WORDS:
                if is_negated:
                    pos_score += intensity  # 双重否定
                else:
                    neg_score += intensity

            i += 1

        return pos_score, neg_score

    def analyze(self, text):
        """
        综合情感分析

        返回:
            {
                'sentiment': 'positive' | 'negative' | 'neutral',
                'score': 情感得分 (-1 ~ 1),
                'pos_score': 正面得分,
                'neg_score': 负面得分,
                'confidence': 置信度
            }
        """
        text = self.preprocess(text)

        # 1. 表情符号分析
        emoticon_score = self.calculate_emoticon_score(text)

        # 2. 标点符号分析
        punctuation_score = self.calculate_punctuation_score(text)

        # 3. 词语情感分析
        import jieba
        words = [w for w in jieba.cut(text) if w.strip()]
        word_pos_score, word_neg_score = self.analyze_word_sentiment(words)

        # 4. 特殊句式检测
        # 转折句式（但是、然而、不过、可惜）
        has_b转折 = any(w in text for w in ['但是', '然而', '不过', '可惜', '却', '然而'])
        if has_b转折:
            # 转折后是重点，降低前面部分的权重
            word_pos_score *= 0.7
            word_neg_score *= 0.7

        # 5. 综合得分
        # 权重：词语分析(0.7) + 表情(0.2) + 标点(0.1)
        total_pos = word_pos_score * 0.7 + max(emoticon_score, 0) * 0.2 + max(punctuation_score, 0) * 0.1
        total_neg = word_neg_score * 0.7 + max(-emoticon_score, 0) * 0.2 + max(-punctuation_score, 0) * 0.1

        # 归一化到 [-1, 1]
        total = total_pos + total_neg
        if total > 0:
            score = (total_pos - total_neg) / total
        else:
            score = 0

        # 判断情感类别
        if score > 0.1:
            sentiment = 'positive'
        elif score < -0.1:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        # 置信度
        confidence = min(abs(score) * 1.5, 1.0) if score != 0 else 0.5

        return {
            'sentiment': sentiment,
            'score': round(score, 3),
            'pos_score': round(total_pos, 3),
            'neg_score': round(total_neg, 3),
            'confidence': round(confidence, 3)
        }


# ============================================================
# 主函数
# ============================================================
def main():
    print('=' * 70)
    print('情感分析增强模块')
    print('=' * 70)

    # 加载数据
    print('\n[1] 加载弹幕数据...')
    with open(CLEANED_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    danmaku_list = data['danmaku_list']
    print(f'    弹幕数量: {len(danmaku_list)}')

    # 分析
    print('\n[2] 情感分析...')
    analyzer = EnhancedSentimentAnalyzer()

    results = []
    pos_count = 0
    neg_count = 0
    neu_count = 0

    for i, item in enumerate(danmaku_list):
        content = item.get('content', '')
        if not content:
            continue

        result = analyzer.analyze(content)
        results.append({
            'content': content,
            'timestamp': item.get('timestamp', 0),
            **result
        })

        if result['sentiment'] == 'positive':
            pos_count += 1
        elif result['sentiment'] == 'negative':
            neg_count += 1
        else:
            neu_count += 1

        if (i + 1) % 500 == 0:
            print(f'    已处理: {i + 1}/{len(danmaku_list)}')

    total = len(results)

    # 统计
    stats = {
        'total': total,
        'positive': {
            'count': pos_count,
            'ratio': round(pos_count / total * 100, 2) if total > 0 else 0
        },
        'negative': {
            'count': neg_count,
            'ratio': round(neg_count / total * 100, 2) if total > 0 else 0
        },
        'neutral': {
            'count': neu_count,
            'ratio': round(neu_count / total * 100, 2) if total > 0 else 0
        }
    }

    print(f'\n[3] 分析结果:')
    print(f'    正面弹幕: {pos_count} ({stats["positive"]["ratio"]}%)')
    print(f'    负面弹幕: {neg_count} ({stats["negative"]["ratio"]}%)')
    print(f'    中性弹幕: {neu_count} ({stats["neutral"]["ratio"]}%)')

    # 保存
    print(f'\n[4] 保存结果...')
    output = {
        'stats': stats,
        'details': results
    }
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f'    结果已保存: {OUTPUT_PATH}')

    print('\n' + '=' * 70)
    print('情感分析完成!')
    print('=' * 70)


if __name__ == '__main__':
    main()
