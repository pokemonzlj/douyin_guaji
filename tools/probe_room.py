#!/usr/bin/env python
"""在 webview 目标里执行 JS，用于探查抖音直播间 DOM。"""
import json
import sys

sys.path.insert(0, r"D:\wbtest\dyfd\tools")
from cdp import evaluate, list_targets, pick  # noqa: E402

PROBE = r"""
(() => {
  const out = {};
  out.url = location.href;
  out.title = document.title;
  const cls = (e) => String(e.className && e.className.baseVal !== undefined ? e.className.baseVal : e.className);
  const vis = (e) => { const s = getComputedStyle(e); const r = e.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 2 && r.height > 2; };
  const text = (e) => String(e.innerText || e.textContent || '').replace(/\s+/g, ' ').trim();

  // 1) class 里带 lottery / lucky / fudai / bag 的元素
  const byClass = [...document.querySelectorAll('*')]
    .filter(e => /lottery|lucky|fudai|bag|prize|award|gift-?bag/i.test(cls(e)))
    .slice(0, 40)
    .map(e => ({ cls: cls(e).slice(0, 160), vis: vis(e), txt: text(e).slice(0, 80) }));
  out.byClass = byClass;

  // 2) 文本含"福袋"的元素（取最内层）
  const bagEls = [...document.querySelectorAll('*')]
    .filter(e => /福袋/.test(text(e)) && ![...e.children].some(c => /福袋/.test(text(c))))
    .slice(0, 25)
    .map(e => { const r = e.getBoundingClientRect();
      return { tag: e.tagName, cls: cls(e).slice(0, 160), vis: vis(e), txt: text(e).slice(0, 120),
        rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) } }; });
  out.bagEls = bagEls;

  // 3) data-e2e / aria-label / title 属性里带关键字的
  const byAttr = [...document.querySelectorAll('[data-e2e],[aria-label],[title],[href]')]
    .filter(e => /lottery|lucky|fudai|bag|prize|福袋|抽奖/i.test(
      (e.getAttribute('data-e2e') || '') + (e.getAttribute('aria-label') || '') + (e.getAttribute('title') || '') + (e.getAttribute('href') || '')))
    .slice(0, 30)
    .map(e => ({ tag: e.tagName, cls: cls(e).slice(0, 120), vis: vis(e),
      attrs: { e2e: e.getAttribute('data-e2e'), aria: e.getAttribute('aria-label'), href: (e.getAttribute('href') || '').slice(0, 60) } }));
  out.byAttr = byAttr;

  // 4) 页面正文片段
  out.bodyHead = String(document.body ? document.body.innerText : '').replace(/\s+/g, ' ').slice(0, 600);

  // 5) 是否有验证码/登录弹层
  out.captcha = !!document.querySelector('iframe[src*="captcha"], iframe[src*="verify"], [class*="captcha"], [class*="verify"]');
  out.loginWall = /扫码登录|登录后即可/.test(String(document.body ? document.body.innerText : ''));

  return JSON.stringify(out, null, 1);
})()
"""


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    match = "live.douyin.com"
    t = pick(list_targets(), match)
    if not t:
        print("no target")
        return 1
    if url:
        evaluate(t["webSocketDebuggerUrl"], "location.href=%s; 'nav'" % json.dumps(url))
        print("navigated ->", url)
        import time
        time.sleep(13)
        t = pick(list_targets(), "live.douyin.com")
    print(json.dumps(evaluate(t["webSocketDebuggerUrl"], PROBE), ensure_ascii=False)[:20000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
