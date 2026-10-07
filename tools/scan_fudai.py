#!/usr/bin/env python
"""批量扫描：从直播广场采集 room_id，逐个查询福袋接口，找出带福袋的直播间。

用法: python scan_fudai.py [滚动次数]
"""
import json
import sys
import time

sys.path.insert(0, r"D:\wbtest\dyfd\tools")
import cdp  # noqa: E402

cdp.BASE = "http://127.0.0.1:9335"

HARVEST = r"""
(() => {
  const out = [];
  for (const a of document.querySelectorAll('a[href]')) {
    const h = a.href || '';
    const m = h.match(/live\.douyin\.com\/(\d+)/);
    if (!m) continue;
    const r = h.match(/[?&]room_id=(\d+)/);
    out.push({ web_rid: m[1], room_id: r ? r[1] : '' });
  }
  return JSON.stringify(out);
})()
"""

QUERY = r"""
(async () => {
  const base = %s;
  const ids = %s;
  const out = [];
  for (const rid of ids) {
    try {
      const res = await fetch(base + rid, { credentials: 'include' });
      const txt = await res.text();
      let obj = null;
      try { obj = JSON.parse(txt); } catch (e) {}
      if (obj && obj.data && Object.keys(obj.data).length) {
        out.push({ room_id: rid, data: obj.data });
      }
    } catch (e) {}
  }
  return JSON.stringify(out);
})()
"""

BASE = ("/webcast/lottery/melon/lottery_info/?aid=6383&app_name=douyin_web&live_id=1&device_platform=web"
        "&language=zh-CN&enter_from=page_refresh&cookie_enabled=true&screen_width=1920&screen_height=1080"
        "&browser_language=zh-CN&browser_platform=Win32&browser_name=Chrome&browser_version=136.0.0.0"
        "&os_name=Windows&os_version=10&query_from=1&room_id=")


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    sess, t = cdp.connect(match="douyin", want_type="webview")
    print("[i] 当前页面:", t.get("url", "")[:80])

    import re
    if not re.match(r"^https://live\.douyin\.com/?(\?.*)?$", t.get("url") or ""):
        sess.evaluate("location.href='https://live.douyin.com/'; 'n'")
        time.sleep(11)

    pairs = {}
    for i in range(rounds):
        try:
            data = json.loads(sess.value(HARVEST, timeout=30))
        except Exception as exc:
            print("[!] 采集失败:", exc)
            data = []
        for item in data:
            if item["room_id"]:
                pairs[item["room_id"]] = item["web_rid"]
        sess.evaluate("window.scrollBy({top: window.innerHeight*1.2, behavior:'instant'}); 's'")
        time.sleep(2.2)
        print("    第%2d轮: 累计有效房间 %d" % (i + 1, len(pairs)))

    if not pairs:
        print("[!] 未采集到 room_id")
        return 1

    ids = list(pairs.keys())
    print("[i] 共 %d 个房间，开始查询福袋接口…" % len(ids))
    found = []
    for start in range(0, len(ids), 25):
        chunk = ids[start:start + 25]
        js = QUERY % (json.dumps(BASE), json.dumps(chunk))
        try:
            res = json.loads(sess.value(js, timeout=90))
        except Exception as exc:
            print("[!] 查询失败:", exc)
            continue
        for item in res:
            item["web_rid"] = pairs.get(item["room_id"], "")
            found.append(item)
            print("★ 福袋房间 room_id=%s web_rid=%s" % (item["room_id"], item["web_rid"]))
            print(json.dumps(item["data"], ensure_ascii=False)[:1500])
        print("    已查询 %d/%d，命中 %d" % (min(start + 25, len(ids)), len(ids), len(found)))

    with open(r"D:\wbtest\dyfd\tools\fudai_found.json", "w", encoding="utf-8") as fh:
        json.dump({"pairs": pairs, "found": found}, fh, ensure_ascii=False, indent=1)
    print("[i] 结果写入 tools/fudai_found.json，命中 %d 个" % len(found))
    return 0


if __name__ == "__main__":
    sys.exit(main())
