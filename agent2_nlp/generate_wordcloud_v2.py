# -*- coding: utf-8 -*-
"""词云生成脚本 V2 - 修复版"""
import json
import os

NLP_DIR = 'F:/Claude project/大数据应用系统开发实践/agent2_nlp'

print('Loading word frequency data...')
with open(os.path.join(NLP_DIR, 'wordfreq.json'), 'r', encoding='utf-8') as f:
    wordfreq_data = json.load(f)

top_words = wordfreq_data['top_100'][:100]

# 创建词频字典
word_freq = {w['word']: w['freq'] for w in top_words}

print(f'Total words: {len(word_freq)}')

# 尝试不同的字体
font_candidates = [
    'C:/Windows/Fonts/simhei.ttf',
    'C:/Windows/Fonts/simsun.ttc',
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/arial.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
]

font_path = None
for fp in font_candidates:
    if os.path.exists(fp):
        font_path = fp
        print(f'Found font: {fp}')
        break

try:
    from wordcloud import WordCloud
    import matplotlib
    matplotlib.use('Agg')  # 无头模式，避免GUI问题
    import matplotlib.pyplot as plt

    if font_path:
        wc = WordCloud(font_path=font_path,
                       width=1200, height=600,
                       background_color='white',
                       max_words=80,
                       max_font_size=120,
                       random_state=42,
                       prefer_horizontal=0.8)
    else:
        wc = WordCloud(width=1200, height=600,
                       background_color='white',
                       max_words=80,
                       max_font_size=120,
                       random_state=42)

    print('Generating wordcloud...')
    wc.generate_from_frequencies(word_freq)

    output_path = os.path.join(NLP_DIR, 'wordcloud.png')
    wc.to_file(output_path)
    print(f'Wordcloud saved to: {output_path}')

    # 同时保存为文本格式供参考
    text_output = os.path.join(NLP_DIR, 'wordfreq_top80.txt')
    with open(text_output, 'w', encoding='utf-8') as f:
        for i, (word, freq) in enumerate(sorted(word_freq.items(), key=lambda x: -x[1])[:80]):
            f.write(f'{i+1}. {word}: {freq}\n')
    print(f'Top 80 words saved to: {text_output}')

except Exception as e:
    print(f'Wordcloud generation failed: {e}')
    print('Saving as text file instead...')

    text_output = os.path.join(NLP_DIR, 'wordfreq_top80.txt')
    with open(text_output, 'w', encoding='utf-8') as f:
        for i, (word, freq) in enumerate(sorted(word_freq.items(), key=lambda x: -x[1])[:80]):
            f.write(f'{i+1}. {word}: {freq}\n')
    print(f'Top 80 words saved to: {text_output}')

print('Done!')