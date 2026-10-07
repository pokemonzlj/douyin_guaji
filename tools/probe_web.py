#!/usr/bin/env python
"""探针：确认抖音网页版是否具备福袋功能，并取当前直播间真实接口返回。

用法:
  python tools/probe_web.py [port] [--eval "JS"]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp  # noqa: E402

port = None
extra = None
args = sys.argv[1:]
i = 0
while i < len(args):
    if args[i] == "--eval" and i + 1 < len(args):
        extra = args[i + 1]
        i += 2
    elif args[i].isdigit():
        port = args[i]
        i += 1
    else:
        i += 1

if port:
    cdp.BASE = "http://127.0.0.1:%s" % port

targets = cdp.list_targets()
print("== targets ==")
for t in targets:
    print("  %-10s %s" % (t.get("type"), t.get("url", "")[:120]))

# 找抖音直播页 webview
t = None
for cand in targets:
    u = cand.get("url", "")
    if any(k in u for k in ("live.douyin.com", "webcast", "douyin.com/root")):
        t = cand
        break
if not t:
    t = cdp.pick(targets, None, want_type="webview") or cdp.pick(targets, "douyin")
if not t:
    print("!! 未找到抖音 webview")
    sys.exit(1)

print("\n== 命中 target:", t.get("type"), t.get("url", "")[:120])
sess = cdp.Session(t["webSocketDebuggerUrl"])

if extra:
    print("== eval:", extra)
    print(json.dumps(sess.evaluate(extra), ensure_ascii=False, indent=1)[:8000])
    sys.exit(0)

probe = r"""
(async () => {
  const out = {};
  out.href = location.href;
  out.title = document.title;
  out.bridge = typeof window.__dyfd;
  out.bridgeKeys = (window.__dyfd && Object.keys(window.__dyfd)) || [];
  // 从 URL 取 web_rid
  const m = location.href.match(/\/(\d{6,})(?:[/?]|$)/);
  out.web_rid = m ? m[1] : null;
  // 取 cookie 里的 odin/ttwid 状态（只看存在性）
  out.cookie_len = (document.cookie || '').length;
  // 尝试调用 bridge 的 lottery
  if (window.__dyfd && window.__dyfd.lottery && out.web_rid) {
    try {
      const rid = await window.__dyfd.resolve(out.web_rid);
      out.room_id = rid && (rid.room_id || rid.roomId || JSON.stringify(rid).slice(0,200));
      if (out.room_id) {
        const lot = await window.__dyfd.lottery(out.room_id);
        out.lottery_raw = JSON.stringify(lot).slice(0, 1200);
      }
    } catch (e) { out.bridge_err = String(e); }
  }
  // 页面里出现的福袋相关关键字
  const txt = document.body ? document.body.innerText : '';
  out.has_fudai_kw = /福袋|超级福袋|参与抽奖|倒计时/.test(txt);
  out.has_upgrading = /系统升级中|暂不支持|升级中/.test(txt);
  out.body_head = txt.replace(/\s+/g, ' ').slice(0, 300);
  return JSON.stringify(out);
})()
"""

print("\n== 探测结果 ==")
print(json.dumps(sess.evaluate(probe), ensure_ascii=False, indent=1)[:9000])
