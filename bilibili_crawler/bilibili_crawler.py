"""
B站视频弹幕数据爬虫
支持登录Cookie获取完整弹幕数据
"""

import requests
import json
import time
from datetime import datetime
from xml.etree import ElementTree as ET

BV_ID = "BV1jEAaz3E6K"

# ============== 请填写你的B站Cookie ==============
# 获取方式：
# 1. 登录B站 (https://www.bilibili.com)
# 2. 按F12打开开发者工具
# 3. 切换到Network(网络)标签
# 4. 刷新页面，找到www.bilibili.com的请求
# 5. 在请求头中找到Cookie字段，复制完整内容
#
# Cookie格式类似：SESSDATA=xxxx; bili_jct=xxx; DedeUserID=xxx;
COOKIE = "SESSDATA=2037754f%2C1792289202%2Cc8e9b%2A42CjB6OTyC7Tfd6_CZSAeBwi5Kru3po6MWjYnm2D0_JsIfKDC8Wt6McHYT-9eKS8nXDpUSVjEzeEdwVVA2TXMyV3V3MVcyRnhva1pkNlhWSVBhNjZ4MHdMWTBHek0ybTNXWndHd3pBNHBQNXN3U3VJWlNSOWN0UnFHQjFIXzNLUkEwa3N3T3k3ZVZnIIEC; bili_jct=23e0d605267a8fd48b6f7e578d64425d;DedeUserID=3493093334583981;"  # <-- 在这里粘贴你的Cookie，或设置为空使用公开API

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


# 如果有Cookie，添加到headers
if COOKIE:
    HEADERS["Cookie"] = COOKIE


def get_video_info(bvid):
    """获取视频信息"""
    resp = requests.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", headers=HEADERS, timeout=10)
    return resp.json()["data"]


def parse_danmaku_protobuf(content):
    """正确解析B站protobuf弹幕格式"""
    danmaku_list = []
    pos = 0

    while pos < len(content):
        if pos >= len(content):
            break
        tag = content[pos]
        pos += 1

        field = tag >> 3
        wire_type = tag & 7

        if field == 1 and wire_type == 2:  # elems字段
            length, n = read_varint(content, pos)
            pos += n

            elem_data = content[pos:pos + length]
            pos += length

            elem_pos = 0
            while elem_pos < len(elem_data):
                elem, consumed = parse_elem(elem_data, elem_pos)
                elem_pos += consumed
                if elem:
                    danmaku_list.append(elem)
        elif wire_type == 0:
            _, n = read_varint(content, pos)
            pos += n
        elif wire_type == 2:
            length, n = read_varint(content, pos)
            pos += n + length
        elif wire_type == 5:
            pos += 4

    return danmaku_list


def read_varint(data, pos):
    """读取protobuf varint"""
    result = 0
    shift = 0
    orig_pos = pos
    while pos < len(data):
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, pos - orig_pos
        shift += 7
    return result, pos - orig_pos


def parse_elem(data, start):
    """解析单个DanmakuElem"""
    pos = start
    end = len(data)
    consumed = 0

    dmid = 0
    progress = 0
    mode = 1
    fontsize = 25
    color = 0xFFFFFF
    mid_hash = ""
    content = ""
    ctime = 0

    while pos < end:
        if pos >= end:
            break
        tag = data[pos]
        pos += 1
        consumed += 1

        field = tag >> 3
        wire_type = tag & 7

        if wire_type == 0:
            val, n = read_varint(data, pos)
            pos += n
            consumed += n

            if field == 1:
                progress = val
            elif field == 2:
                mode = val
            elif field == 3:
                fontsize = val
            elif field == 4:
                color = val
            elif field == 8:
                dmid = val
            elif field == 9:
                ctime = val

        elif wire_type == 2:
            length, n = read_varint(data, pos)
            pos += n
            consumed += n

            val = data[pos:pos + length]
            pos += length
            consumed += length

            if field == 1:
                dmid = int.from_bytes(val, 'little') if val else 0
            elif field == 6:
                mid_hash = val.decode('utf-8', errors='ignore')
            elif field == 7:
                content = val.decode('utf-8', errors='ignore')

        elif wire_type == 5:
            pos += 4
            consumed += 4

        else:
            break

    if content:
        r = color & 0xFF
        g = (color >> 8) & 0xFF
        b = (color >> 16) & 0xFF

        return {
            "id": dmid,
            "content": content.strip(),
            "timestamp": progress / 1000,
            "type": mode,
            "font_size": fontsize,
            "color_hex": f"#{r:02x}{g:02x}{b:02x}",
            "sender": mid_hash,
            "send_time": ctime,
        }, consumed

    return None, consumed


def get_danmaku_by_seg(cid, pid, segment_index=1):
    """通过分片API获取弹幕"""
    url = "https://api.bilibili.com/x/v2/dm/web/seg.so"
    params = {
        "type": 1,
        "oid": cid,
        "pid": pid,
        "segment_index": segment_index,
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
    return parse_danmaku_protobuf(resp.content)


def get_danmaku_xml(cid):
    """通过XML方式获取弹幕（备用）"""
    url = f"https://comment.bilibili.com/{cid}.xml"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = 'utf-8'
        root = ET.fromstring(resp.content)
        danmaku_list = []
        for d in root.findall('.//d'):
            p = d.get('p', '').split(',')
            if d.text:
                try:
                    color_int = int(p[3]) if len(p) > 3 else 16777215
                    r = color_int & 0xFF
                    g = (color_int >> 8) & 0xFF
                    b = (color_int >> 16) & 0xFF
                    danmaku_list.append({
                        "id": 0,
                        "content": d.text.strip(),
                        "timestamp": float(p[0]) if p else 0,
                        "type": int(p[1]) if len(p) > 1 else 1,
                        "font_size": int(p[2]) if len(p) > 2 else 25,
                        "color_hex": f"#{r:02x}{g:02x}{b:02x}",
                        "sender": p[4] if len(p) > 4 else "",
                        "send_time": int(p[5]) if len(p) > 5 else 0,
                    })
                except:
                    pass
        return danmaku_list
    except Exception as e:
        print(f"XML获取失败: {e}")
        return []


def get_danmaku_history(cid, pid, date_str):
    """通过历史弹幕API获取特定日期的弹幕（需要Cookie）"""
    url = f"https://api.bilibili.com/x/v2/dm/web/history/seg.so?type=1&oid={cid}&pid={pid}&date={date_str}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if len(resp.content) > 100:
            return parse_danmaku_protobuf(resp.content)
    except Exception as e:
        print(f"历史弹幕获取失败: {e}")
    return []


def main():
    print("=" * 60)
    print("B站弹幕爬虫 - 支持登录Cookie")
    print("=" * 60)

    # 检查Cookie状态
    if COOKIE:
        print("\n[✓] 已配置登录Cookie，将获取完整弹幕数据")
        if 'SESSDATA' in COOKIE:
            print("    Cookie格式正确")
    else:
        print("\n[!] 未配置Cookie，将使用公开API（可能获取不完整）")
        print("    如需完整数据，请在代码中配置你的B站Cookie")

    # 获取视频信息
    print("\n[1] 获取视频信息...")
    video = get_video_info(BV_ID)
    cid = video["cid"]
    aid = video["aid"]
    duration = video["duration"]
    title = video["title"]
    stat = video["stat"]

    print(f"标题: {title}")
    print(f"播放量: {stat['view']:,}")
    print(f"弹幕数(官方): {stat['danmaku']:,}")
    print(f"评论数: {stat['reply']:,}")
    print(f"CID: {cid}, AID: {aid}")
    print(f"时长: {duration}秒")

    # 获取弹幕
    print("\n[2] 获取弹幕数据...")

    all_danmaku = []
    has_cookie = bool(COOKIE and 'SESSDATA' in COOKIE)

    if has_cookie:
        # 使用分片API获取
        num_segments = (duration + 359) // 360
        print(f"分片数(估算): {num_segments}")

        for seg in range(1, num_segments + 1):
            print(f"  分片 {seg}/{num_segments}...", end=" ")
            dm_list = get_danmaku_by_seg(cid, aid, seg)
            print(f"{len(dm_list)}条")
            all_danmaku.extend(dm_list)
            time.sleep(0.2)

        print(f"\n分片获取: {len(all_danmaku)}条")

        # 如果有更多分片可用，尝试获取
        for seg in range(num_segments + 1, num_segments + 5):
            dm_list = get_danmaku_by_seg(cid, aid, seg)
            if dm_list:
                print(f"  额外分片 {seg}: +{len(dm_list)}条")
                all_danmaku.extend(dm_list)
            time.sleep(0.2)
    else:
        # 无Cookie，使用公开API
        print("使用公开API获取弹幕...")

        # XML获取（主方法）
        xml_danmaku = get_danmaku_xml(cid)
        print(f"XML获取: {len(xml_danmaku)}条")
        all_danmaku.extend(xml_danmaku)

        # 分片获取（备用）
        num_segments = (duration + 359) // 360
        seg_total = 0
        for seg in range(1, num_segments + 1):
            dm_list = get_danmaku_by_seg(cid, aid, seg)
            seg_total += len(dm_list)
            if dm_list:
                all_danmaku.extend(dm_list)
        print(f"分片获取: {seg_total}条")

    # 去重
    seen = set()
    unique_danmaku = []
    for dm in all_danmaku:
        content = dm.get('content', '')
        if content and content not in seen:
            seen.add(content)
            unique_danmaku.append(dm)

    # 按时间排序
    unique_danmaku.sort(key=lambda x: x.get('timestamp', 0))

    print(f"\n去重后: {len(unique_danmaku)}条弹幕")
    print(f"完整度: {len(unique_danmaku)}/{stat['danmaku']} = {len(unique_danmaku)/stat['danmaku']*100:.1f}%")

    # 保存数据
    result = {
        "video_info": {
            "bvid": video["bvid"],
            "title": title,
            "aid": aid,
            "cid": cid,
            "duration": duration,
            "publish_date": datetime.fromtimestamp(video["pubdate"]).strftime("%Y-%m-%d %H:%M:%S"),
            "view_count": stat["view"],
            "like_count": stat["like"],
            "coin_count": stat["coin"],
            "favorite_count": stat["favorite"],
            "danmaku_count": stat["danmaku"],
            "reply_count": stat["reply"],
            "owner": {
                "mid": video["owner"]["mid"],
                "name": video["owner"]["name"],
            }
        },
        "danmaku_list": unique_danmaku,
        "danmaku_count": len(unique_danmaku),
        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "has_full_cookie": has_cookie,
    }

    output_file = "bilibili_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存到: {output_file}")
    print(f"总计: {len(unique_danmaku)}条弹幕")

    # 显示样例
    print("\n弹幕样例(前20条):")
    print("-" * 60)
    for i, dm in enumerate(unique_danmaku[:20]):
        ts = int(dm.get('timestamp', 0))
        mins, secs = ts // 60, ts % 60
        content = dm.get('content', '')[:50]
        print(f"[{mins:02d}:{secs:02d}] {content}")

    return len(unique_danmaku)


if __name__ == "__main__":
    count = main()
    print(f"\n最终获取: {count}条弹幕")