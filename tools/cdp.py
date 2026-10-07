#!/usr/bin/env python
"""极简 Chrome DevTools Protocol 客户端。

用法:
  python cdp.py <port> list
  python cdp.py <port> eval "JS表达式" [target-url-子串]
  python cdp.py <port> dump "CSS选择器" [target-url-子串]
"""
import json
import os
import sys
import time
import urllib.request

import websocket

# 本机调试口必须直连，绕开 http_proxy/HTTPS_PROXY 等环境代理
for _k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    os.environ.pop(_k, None)

_PORT = os.environ.get("CDP_PORT", "9335")
BASE = "http://127.0.0.1:%s" % _PORT

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _fetch(url):
    """优先直连；直连失败时退回 curl（并显式禁用代理）。"""
    try:
        with _OPENER.open(url, timeout=8) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception as exc:
        if os.environ.get("CDP_DEBUG"):
            sys.stderr.write("[cdp] direct failed: %r\n" % (exc,))
        import subprocess
        out = subprocess.run(["curl", "-s", "-m", "8", "--noproxy", "*", url], capture_output=True)
        return out.stdout.decode("utf-8", "replace")


def list_targets():
    last = None
    for _ in range(20):
        try:
            text = _fetch(BASE + "/json/list")
            if text and text.lstrip().startswith("["):
                return json.loads(text)
            last = RuntimeError("bad response: %r" % text[:80])
        except Exception as exc:  # 本地调试口偶发抖动，重试
            last = exc
        time.sleep(1.5)
    raise last


def pick(targets, match=None, want_type=None):
    for t in targets:
        if want_type and t.get("type") != want_type:
            continue
        if not match or match in t.get("url", "") or match in t.get("title", ""):
            return t
    return None


class Session:
    """一条 CDP 连接，可连续下发多条命令。"""

    def __init__(self, ws_url, timeout=60):
        self.ws = websocket.create_connection(ws_url, timeout=timeout, suppress_origin=True)
        self._id = 0

    def send(self, method, params=None, timeout=None):
        self._id += 1
        mid = self._id
        if timeout:
            self.ws.settimeout(timeout)
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                return msg

    def evaluate(self, expr, timeout=60):
        msg = self.send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True,
            "userGesture": True,
        }, timeout=timeout)
        return msg

    def value(self, expr, timeout=60):
        """取值，出错直接抛出异常文本。"""
        msg = self.evaluate(expr, timeout=timeout)
        result = msg.get("result", {})
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"].get("exception", {}).get("description", "JS error"))
        return result.get("result", {}).get("value")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def connect(port=None, match="index.html", want_type=None):
    """连到第一个匹配的 target，返回 Session。"""
    global BASE
    if port:
        BASE = "http://127.0.0.1:%s" % port
    t = pick(list_targets(), match, want_type)
    if not t:
        raise RuntimeError("no target matching %r" % match)
    return Session(t["webSocketDebuggerUrl"]), t


def main():
    cmd = sys.argv[2] if len(sys.argv) > 2 else "list"
    global BASE
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        BASE = "http://127.0.0.1:%s" % sys.argv[1]
    targets = list_targets()
    if cmd == "list":
        for t in targets:
            print("%-15s %-9s %s" % (t["type"], t.get("id", "")[:8], t.get("url", "")[:120]))
        return
    expr = sys.argv[3]
    match = sys.argv[4] if len(sys.argv) > 4 else None
    if cmd == "dump":
        expr = (
            "(() => { const els=[...document.querySelectorAll(%s)];"
            "return JSON.stringify(els.slice(0,60).map(e=>({tag:e.tagName,cls:String(e.className).slice(0,180),"
            "txt:(e.innerText||'').replace(/\\s+/g,' ').slice(0,120),"
            "rect:(r=>({x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}))(e.getBoundingClientRect())})),null,1);})()"
            % json.dumps(expr)
        )
    target = pick(targets, match)
    if not target:
        print("NO_TARGET", [t.get("url", "")[:80] for t in targets])
        sys.exit(1)
    print("-- target:", target["type"], target.get("url", "")[:110])
    print(json.dumps(evaluate(target["webSocketDebuggerUrl"], expr), ensure_ascii=False, indent=1)[:12000])


if __name__ == "__main__":
    main()
