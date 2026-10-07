#!/usr/bin/env python
"""抖音直播页侦察：注入网络探针 -> 遍历直播间 -> 收集福袋相关接口/DOM 结构。

用法: python recon.py [房间数]
"""
import json
import re
import sys
import time

sys.path.insert(0, r"D:\wbtest\dyfd\tools")
from cdp import connect, list_targets, pick  # noqa: E402

TAP = r"""
(() => {
  if (window.__dyTap) return 'already';
  const tap = window.__dyTap = { hits: [], wsCount: 0, wsTypes: {}, urls: [] };
  const KEY = /lottery|lucky|bag|prize|award|fudai|draw|抽奖|福袋/i;
  const push = (o) => { tap.hits.push(o); if (tap.hits.length > 300) tap.hits.shift(); };
  const ascii = (buf) => {
    try { const b = new Uint8Array(buf); let s = '';
      for (let i = 0; i < Math.min(b.length, 8192); i++) { const c = b[i]; if (c >= 32 && c < 127) s += String.fromCharCode(c); }
      return s; } catch (e) { return ''; }
  };
  const scan = (url, text) => {
    try {
      tap.urls.push(String(url).slice(0, 200));
      if (tap.urls.length > 600) tap.urls.shift();
      if (KEY.test(String(url))) { push({ k: 'url', url: String(url).slice(0, 320), text: String(text).slice(0, 1500) }); return; }
      const m = String(text).match(/.{0,60}(?:lottery|lucky_?bag|fudai|抽奖|福袋).{0,140}/i);
      if (m) push({ k: 'body', url: String(url).slice(0, 220), text: String(text).slice(0, 2000) });
    } catch (e) {}
  };
  try {
    const OX = XMLHttpRequest.prototype.open, OS = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (m, u, ...r) { this.__u = u; return OX.call(this, m, u, ...r); };
    XMLHttpRequest.prototype.send = function (...a) {
      this.addEventListener('load', () => { try { scan(this.__u, this.responseText || ''); } catch (e) {} });
      return OS.apply(this, a);
    };
    const OF = window.fetch;
    if (OF) window.fetch = function (...a) {
      const u = (a[0] && a[0].url) || a[0];
      return OF.apply(this, a).then((res) => { try { res.clone().text().then((t) => scan(u, t)).catch(() => {}); } catch (e) {} return res; });
    };
    const OW = window.WebSocket;
    window.WebSocket = function (...a) {
      const ws = new OW(...a); tap.wsCount++;
      try {
        ws.addEventListener('message', (ev) => {
          const d = ev.data;
          if (typeof d === 'string') { scan('ws:' + a[0], d); return; }
          if (d instanceof ArrayBuffer) {
            const s = ascii(d);
            const m = s.match(/[A-Za-z]{5,40}(?:Lottery|LuckyBag|Prize|RedPacket)[A-Za-z]*/g);
            if (m) { m.slice(0, 4).forEach((t) => { tap.wsTypes[t] = (tap.wsTypes[t] || 0) + 1; }); push({ k: 'wsbin', url: String(a[0]).slice(0, 120), text: s.slice(0, 1500) }); }
          }
        });
      } catch (e) {}
      return ws;
    };
    window.WebSocket.prototype = OW.prototype;
  } catch (e) {}
  return 'hooked';
})()
"""

DOMCHK = r"""
(() => {
  const cls = (e) => String(e.className && e.className.baseVal !== undefined ? e.className.baseVal : e.className);
  const vis = (e) => { const s = getComputedStyle(e), r = e.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 2 && r.height > 2; };
  const text = (e) => String(e.innerText || e.textContent || '').replace(/\s+/g, ' ').trim();
  const bagText = [...document.querySelectorAll('*')]
    .filter((e) => /福袋/.test(text(e)) && ![...e.children].some((c) => /福袋/.test(text(c))))
    .slice(0, 10)
    .map((e) => ({ tag: e.tagName, cls: cls(e).slice(0, 140), vis: vis(e), txt: text(e).slice(0, 90) }));
  const lotteryCls = [...document.querySelectorAll('*')]
    .filter((e) => /lottery|lucky|fudai|prize/i.test(cls(e)))
    .slice(0, 20)
    .map((e) => ({ cls: cls(e).slice(0, 140), vis: vis(e), txt: text(e).slice(0, 70) }));
  return JSON.stringify({ url: location.href, title: document.title, bagText, lotteryCls,
    tap: { wsCount: window.__dyTap ? window.__dyTap.wsCount : -1,
           wsTypes: window.__dyTap ? window.__dyTap.wsTypes : {},
           hits: window.__dyTap ? window.__dyTap.hits.slice(-25) : [] } });
})()
"""


def main():
    want = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    sess, target = connect(match="douyin", want_type="webview")
    sess.send("Page.enable")
    sess.send("Runtime.enable")
    sess.send("Page.addScriptToEvaluateOnNewDocument", {"source": TAP})
    print("[i] 探针已注入，target =", target.get("url", "")[:80])

    # 1) 收集直播间
    sess.evaluate("location.href='https://live.douyin.com/'; 'nav'")
    time.sleep(11)
    rooms = []
    for _ in range(4):
        sess.evaluate("window.scrollBy({top: window.innerHeight*0.9, behavior:'instant'}); 's'")
        time.sleep(2.5)
        raw = sess.value("JSON.stringify([...new Set([...document.querySelectorAll('a[href]')].map(a=>a.href))])", timeout=30)
        for h in json.loads(raw):
            m = re.match(r"https://live\.douyin\.com/(\d+)", h)
            if m and m.group(1) not in rooms:
                rooms.append(m.group(1))
    print("[i] 收集到直播间 %d 个: %s" % (len(rooms), rooms[:want]))
    if not rooms:
        return 1

    # 2) 逐个进入
    report = []
    for rid in rooms[:want]:
        sess.evaluate("location.href='https://live.douyin.com/%s'; 'nav'" % rid)
        time.sleep(12)
        try:
            data = json.loads(sess.value(DOMCHK, timeout=40))
        except Exception as exc:
            print("[!] %s 探查失败: %s" % (rid, exc))
            continue
        hits = data["tap"]["hits"]
        report.append((rid, data["title"], data["bagText"], data["lotteryCls"], data["tap"], hits))
        flag = "★福袋" if (data["bagText"] or hits) else "  -"
        print("%s %s | %s | bagText=%d lotteryCls=%d hits=%d ws=%d" %
              (flag, rid, data["title"][:40], len(data["bagText"]), len(data["lotteryCls"]),
               len(hits), data["tap"]["wsCount"]))
        if hits:
            for h in hits[:6]:
                print("      [%s] %s" % (h.get("k"), (h.get("url") or "")[:150]))
                print("           %s" % (h.get("text") or "")[:400].replace("\n", " "))

    with open(r"D:\wbtest\dyfd\tools\recon_report.json", "w", encoding="utf-8") as fh:
        json.dump([{"room": r[0], "title": r[1], "bagText": r[2], "lotteryCls": r[3], "tap": r[4], "hits": r[5]} for r in report],
                  fh, ensure_ascii=False, indent=1)
    print("[i] 报告写入 tools/recon_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
