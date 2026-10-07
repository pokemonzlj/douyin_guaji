// 抖音福袋万花筒 桌面版 3.0
// 核心思路：不做本地签名、不伪造算法，直接在已登录的抖音直播页里调用页面自身的接口，
// 因此不会出现“加密算法解析异常”这类随抖音更新而失效的问题。

const $ = (id) => document.getElementById(id);
const webview = $('douyin');

/* ------------------------------------------------------------------ *
 * 注入到抖音页面里的桥接脚本
 * 说明：使用 String.raw 模板，脚本内不能出现反引号与 ${ }
 * ------------------------------------------------------------------ */
const DYFD_BRIDGE = String.raw`
(() => {
  if (window.__dyfd && window.__dyfd.version >= 3) return 'exists';

  const COMMON = [
    'aid=6383', 'app_name=douyin_web', 'live_id=1', 'device_platform=web', 'language=zh-CN',
    'enter_from=web_live_room', 'cookie_enabled=true', 'screen_width=1920', 'screen_height=1080',
    'browser_language=zh-CN', 'browser_platform=Win32', 'browser_name=Chrome',
    'browser_version=136.0.0.0', 'os_name=Windows', 'os_version=10'
  ].join('&');

  const TAP = { lottery: [], draw: [], other: [], lastLottery: null };

  const record = (url, body) => {
    const u = String(url || '');
    if (!/\/webcast\/lottery\//.test(u)) return;
    const item = { url: u, at: Date.now(), body: String(body || '').slice(0, 4000) };
    if (/(draw|join|participate|delivery|user_condition)/i.test(u)) {
      TAP.draw.unshift(item);
      if (TAP.draw.length > 20) TAP.draw.pop();
    } else {
      TAP.lottery.unshift(item);
      if (TAP.lottery.length > 20) TAP.lottery.pop();
      if (/lottery_info/.test(u)) TAP.lastLottery = item;
    }
  };

  try {
    const OX = XMLHttpRequest.prototype.open;
    const OS = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (m, u) { this.__dyUrl = u; return OX.apply(this, arguments); };
    XMLHttpRequest.prototype.send = function () {
      const self = this;
      this.addEventListener('load', () => { try { record(self.__dyUrl, self.responseText); } catch (e) {} });
      return OS.apply(this, arguments);
    };
    const OF = window.fetch;
    if (OF) {
      window.fetch = function () {
        const args = arguments;
        const u = (args[0] && args[0].url) || args[0];
        return OF.apply(this, args).then((res) => {
          try { res.clone().text().then((t) => record(u, t)).catch(() => {}); } catch (e) {}
          return res;
        });
      };
    }
  } catch (e) {}

  const json = async (path) => {
    const res = await fetch(path, { credentials: 'include' });
    const text = await res.text();
    try { return JSON.parse(text); } catch (e) { return { __raw: text.slice(0, 300) }; }
  };

  const clean = (v) => String(v || '').replace(/\s+/g, ' ').trim();

  const api = {
    version: 3,
    tap: TAP,

    /* 从当前页面 DOM 里收集直播间 web_rid（直播广场 / 关注页 / 直播间页面都可用） */
    harvest() {
      const found = new Map();
      const push = (rid, title) => {
        if (!rid || !/^\d{5,}$/.test(rid)) return;
        if (!found.has(rid)) found.set(rid, clean(title || ''));
      };
      for (const a of document.querySelectorAll('a[href]')) {
        const m = String(a.href || '').match(/live\.douyin\.com\/(\d+)/);
        if (m) {
          const card = a.closest('[class]') || a;
          push(m[1], (card.getAttribute('title') || a.getAttribute('title') || card.innerText || '').slice(0, 40));
        }
      }
      return [...found.entries()].map(([webRid, title]) => ({ webRid, title }));
    },

    /* 解析直播间：web_rid -> room_id / 主播 / 是否已关注 / 相似直播间 */
    async resolve(webRid) {
      const path = '/webcast/room/web/enter/?' + COMMON +
        '&web_rid=' + encodeURIComponent(webRid) +
        '&room_id_str=&enter_source=&is_need_double_stream=false&insert_task_id=&live_reason=';
      const j = await json(path);
      const room = j && j.data && j.data.data && j.data.data[0];
      if (!room) return null;
      const owner = room.owner || {};
      const similar = [];
      const list = (j.data && j.data.similar_rooms) || [];
      for (const s of list) {
        const r = s.room || s;
        const rid = r && (r.id_str || r.room_id_str || (r.owner && r.owner.web_rid));
        if (rid) similar.push(String(rid));
      }
      return {
        webRid: String(webRid),
        roomId: String(room.id_str || ''),
        title: clean(room.title),
        status: room.status,
        userCount: clean(room.user_count_str),
        anchorId: String(owner.id_str || ''),
        anchorName: clean(owner.nickname),
        followed: !!(owner.follow_info && (owner.follow_info.follow_status === 1 || owner.follow_info.follow_status === 2)),
        lottery: (room.lottery_info && Object.keys(room.lottery_info).length) ? room.lottery_info : null,
        similar,
      };
    },

    /* 查询房间当前福袋状态；data 非空表示存在福袋 */
    async lottery(roomId) {
      const path = '/webcast/lottery/melon/lottery_info/?' + COMMON + '&room_id=' + encodeURIComponent(roomId) + '&query_from=1';
      const j = await json(path);
      if (j && j.data && Object.keys(j.data).length) return j.data;
      return null;
    },

    /* DOM 层福袋探测（接口不可用时的兜底） */
    domBag() {
      const visible = (e) => {
        const s = getComputedStyle(e);
        const r = e.getBoundingClientRect();
        return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 2 && r.height > 2;
      };
      const nodes = [...document.querySelectorAll('div,span,button,a')].filter((e) => {
        const t = clean(e.innerText);
        return /福袋/.test(t) && t.length <= 60 && visible(e) && e.children.length <= 2;
      });
      const controls = [...document.querySelectorAll('button,[role="button"],div,span,a')]
        .filter(visible)
        .map((e) => clean(e.innerText))
        .filter((t) => t && t.length <= 30);
      return {
        bagNodes: nodes.slice(0, 6).map((e) => ({ text: clean(e.innerText), cls: String(e.className).slice(0, 120) })),
        hasBag: nodes.length > 0,
        controls: [...new Set(controls)].slice(0, 200),
      };
    },

    /* 依次点击“福袋入口 -> 参与按钮” */
    clickBag() {
      const visible = (e) => {
        const s = getComputedStyle(e);
        const r = e.getBoundingClientRect();
        return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 2 && r.height > 2;
      };
      const pick = (regex, exact) => {
        const list = [...document.querySelectorAll('button,[role="button"],div,span,a')]
          .filter(visible)
          .map((e) => ({ e, t: clean(e.innerText), a: e.getBoundingClientRect().width * e.getBoundingClientRect().height }))
          .filter((x) => x.t && (exact ? x.t === exact : regex.test(x.t)) && x.t.length <= 30)
          .sort((x, y) => x.a - y.a);
        return list.length ? list[0] : null;
      };
      const entry = pick(/福袋|抽奖|超级福袋|幸运福袋/, false);
      if (!entry) return { ok: false, step: '未找到福袋入口' };
      entry.e.click();
      return { ok: true, step: '已点击福袋入口', text: entry.t };
    },

    clickJoin() {
      const visible = (e) => {
        const s = getComputedStyle(e);
        const r = e.getBoundingClientRect();
        return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 2 && r.height > 2;
      };
      const target = [...document.querySelectorAll('button,[role="button"],div,span,a')]
        .filter(visible)
        .map((e) => ({ e, t: clean(e.innerText), a: e.getBoundingClientRect().width * e.getBoundingClientRect().height }))
        .filter((x) => /^(立即参与|参与抽奖|一键参与|参与福袋|立即抽奖|参与)$/.test(x.t))
        .sort((x, y) => x.a - y.a)[0];
      if (!target) return { ok: false, step: '未找到参与按钮' };
      target.e.click();
      return { ok: true, step: '已点击参与', text: target.t };
    },

    clickFollow() {
      const visible = (e) => {
        const s = getComputedStyle(e);
        const r = e.getBoundingClientRect();
        return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 2 && r.height > 2;
      };
      const target = [...document.querySelectorAll('button,[role="button"],div,span,a')]
        .filter(visible)
        .map((e) => ({ e, t: clean(e.innerText) }))
        .filter((x) => /^(关注主播|关注)$/.test(x.t))[0];
      if (!target) return { ok: false };
      target.e.click();
      return { ok: true, text: target.t };
    },

    captcha() {
      const frame = document.querySelector('iframe[src*="captcha"], iframe[src*="verify.zijieapi"], iframe[src*="rmc.bytedance"]');
      const node = document.querySelector('[class*="captcha-container"], [id*="captcha"], [class*="verify-wrap"]');
      const text = document.body ? clean(document.body.innerText) : '';
      return !!(frame || node) || /请完成安全验证|拖动滑块|验证码/.test(text);
    },

    /* 学习到的参与接口（页面自己调用过就能拿到） */
    learnedDraw() {
      if (!TAP.draw.length) return null;
      try {
        const u = new URL(TAP.draw[0].url, location.origin);
        return u.pathname;
      } catch (e) { return null; }
    },

    /* 用页面自身签名能力复现一次参与请求 */
    async callDraw(roomId, lotteryId, anchorId) {
      const path = api.learnedDraw();
      if (!path) return { ok: false, err: '尚未捕获到参与接口' };
      const u = new URL(TAP.draw[0].url, location.origin);
      const params = u.searchParams;
      params.set('room_id', roomId);
      if (lotteryId) { params.set('lottery_id', lotteryId); params.set('lottery_id_str', lotteryId); }
      if (anchorId) { params.set('anchor_id', anchorId); params.set('anchor_id_str', anchorId); }
      ['a_bogus', 'msToken', 'X-Bogus', 'signature', 'timestamp', 'ts', 'xx-tt-dd'].forEach((k) => params.delete(k));
      try {
        const res = await fetch(u.pathname + '?' + params.toString(), { credentials: 'include', method: 'POST' });
        return { ok: res.ok, status: res.status, body: (await res.text()).slice(0, 400) };
      } catch (e) { return { ok: false, err: String(e) }; }
    },
  };

  window.__dyfd = api;
  return 'injected';
})()
`;

/* ------------------------------------------------------------------ *
 * 运行状态
 * ------------------------------------------------------------------ */
const state = {
  running: false,
  timer: null,
  settings: null,
  rooms: new Map(),        // webRid -> { ...resolve 结果, checkedAt }
  found: new Map(),        // roomId  -> 待开奖/已参与记录
  visited: new Map(),      // webRid -> 上次进入时间
  currentRoom: '',
  inRoomSince: 0,
  joinBusy: false,
  captchaAlerted: 0,
};

const CHECK_TTL = 25000;   // 同一房间的最小检测间隔
const BATCH = 6;           // 每轮检测多少个房间
const ROOM_STAY = 20000;   // 在带福袋的房间里停留多久

function appendLog(message, level = 'info') {
  const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
  const prefix = level === 'error' ? '错误' : level === 'success' ? '完成' : '信息';
  const line = '[' + time + '] [' + prefix + '] ' + message;
  const node = $('log');
  node.textContent += line + '\n';
  const lines = node.textContent.split('\n');
  if (lines.length > 500) node.textContent = lines.slice(-400).join('\n');
  node.scrollTop = node.scrollHeight;
  if (window.desktop.writeLog) window.desktop.writeLog(line);
}

function setRunState(running, label) {
  state.running = running;
  $('start').disabled = running;
  $('stop').disabled = !running;
  $('run-state').textContent = label || (running ? '扫描中' : '未运行');
  $('run-state').className = 'status ' + (running ? 'running' : 'idle');
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function normalizeUrl(value) {
  let url = String(value || '').trim();
  if (!/^https?:\/\//i.test(url)) url = 'https://' + url;
  return url;
}

function loadUrl(value) {
  const url = normalizeUrl(value);
  $('address').value = url;
  webview.loadURL(url);
}

const bridgeReady = () => new Promise((resolve) => {
  webview.executeJavaScript(DYFD_BRIDGE).then(() => resolve(true)).catch(() => resolve(false));
});

const pageEval = (code) => webview.executeJavaScript(code);

/* ------------------------------------------------------------------ */
async function refreshLoginState() {
  const info = await window.desktop.getLoginState();
  $('login-state').textContent = info.loggedIn ? '已登录' : '未登录';
  $('login-state').className = 'status ' + (info.loggedIn ? 'logged-in' : '');
  $('account-detail').textContent = info.loggedIn
    ? '登录会话已保存' + (info.accountKey ? '，账号标识 ' + info.accountKey : '') + '。关闭软件后仍会保留。'
    : '请在左侧抖音页面扫码登录。';
  return info;
}

function currentPageUrl() {
  try { return webview.getURL() || ''; } catch (e) { return ''; }
}

function onLiveRoom() {
  return /^https:\/\/live\.douyin\.com\/\d+/.test(currentPageUrl());
}

function currentWebRid() {
  const m = currentPageUrl().match(/^https:\/\/live\.douyin\.com\/(\d+)/);
  return m ? m[1] : '';
}

/* ------------------------------- 渲染 ------------------------------- */
function renderRooms() {
  const rows = [...state.rooms.values()].slice(0, 200);
  $('room-count').textContent = String(rows.length);
  $('rooms-body').innerHTML = rows.length
    ? rows.map((r) => {
        const tag = r.lottery ? '有福袋' : (r.userCount ? '直播中 ' + r.userCount : '直播中');
        return '<tr' + (r.lottery ? ' class="hit"' : '') + '>'
          + '<td title="' + escapeHtml(r.title) + '">' + escapeHtml(r.title || r.webRid) + '</td>'
          + '<td>' + escapeHtml(r.anchorName || '') + (r.followed ? ' · 已关注' : '') + '</td>'
          + '<td>' + escapeHtml(tag) + '</td></tr>';
      }).join('')
    : '<tr class="empty"><td colspan="3">队列为空，正在从直播广场发现房间</td></tr>';
}

function renderFound() {
  const rows = [...state.found.values()].reverse();
  $('pending-count').textContent = String(rows.length);
  $('pending-body').innerHTML = rows.length
    ? rows.map((it) => '<tr>'
        + '<td title="' + escapeHtml(it.title) + '">' + escapeHtml(it.title) + '</td>'
        + '<td title="' + escapeHtml(it.detail) + '">' + escapeHtml(it.detail) + '</td>'
        + '<td>' + it.foundAt + '</td>'
        + '<td>' + escapeHtml(it.status) + '</td></tr>').join('')
    : '<tr class="empty"><td colspan="4">尚未发现福袋</td></tr>';
}

function addFound(room, detail, status) {
  const key = room.roomId || room.webRid;
  const prev = state.found.get(key);
  state.found.set(key, {
    title: room.title || room.webRid,
    detail: detail || '检测到福袋',
    foundAt: prev ? prev.foundAt : new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    status,
  });
  while (state.found.size > (state.settings ? state.settings.maxPending : 50)) {
    state.found.delete(state.found.keys().next().value);
  }
  renderFound();
}

/* ------------------------------ 主循环 ------------------------------ */
function parseLottery(data, room) {
  if (!data) return null;
  const info = data.lottery_info || data.lotteryInfo || data;
  const prize = info.prize_info || info.prize || {};
  const title = prize.name || prize.prize_name || info.title || info.prize_name || '';
  const conds = [];
  const c = info.condition || info.conditions || {};
  if (c.follow) conds.push('关注');
  if (c.comment || info.comment_count) conds.push('评论');
  if (c.fansclub || info.fansclub_level) conds.push('粉丝团');
  if (c.diamond || info.diamond_count) conds.push('钻石');
  if (info.condition_text) conds.push(String(info.condition_text));
  const drawn = info.drawn || info.is_drawn || info.user_status === 1 || info.has_drawn;
  return {
    lotteryId: String(info.lottery_id || info.lottery_id_str || info.id || ''),
    title: title || '福袋',
    conditions: conds.join('/') || '无条件',
    drawn: !!drawn,
    raw: info,
  };
}

async function discoverRooms() {
  try {
    const found = await pageEval('JSON.stringify(window.__dyfd ? window.__dyfd.harvest() : [])');
    const list = JSON.parse(found || '[]');
    let added = 0;
    for (const item of list) {
      if (!state.rooms.has(item.webRid)) {
        state.rooms.set(item.webRid, { webRid: item.webRid, title: item.title, checkedAt: 0 });
        added += 1;
      }
    }
    if (added) {
      appendLog('发现 ' + added + ' 个新直播间，队列共 ' + state.rooms.size + ' 个。');
      renderRooms();
    }
    return added;
  } catch (e) {
    return 0;
  }
}

async function resolveBatch() {
  const now = Date.now();
  const pending = [...state.rooms.values()].filter((r) => now - (r.checkedAt || 0) > CHECK_TTL).slice(0, BATCH);
  if (!pending.length) return [];
  const hits = [];
  for (const item of pending) {
    try {
      const raw = await pageEval('(async () => { ' +
        'const r = await window.__dyfd.resolve(' + JSON.stringify(item.webRid) + '); ' +
        'if (!r) return "null"; ' +
        'let d = r.lottery; ' +
        'if (!d) { d = await window.__dyfd.lottery(r.roomId); } ' +
        'return JSON.stringify(Object.assign({}, r, { lotteryData: d })); })()');
      if (!raw || raw === 'null') { item.checkedAt = now; continue; }
      const info = JSON.parse(raw);
      const merged = Object.assign({}, item, info, { checkedAt: now });
      delete merged.lotteryData;
      state.rooms.set(item.webRid, merged);
      if (info.similar && info.similar.length) {
        for (const rid of info.similar) {
          if (!state.rooms.has(rid)) state.rooms.set(rid, { webRid: rid, title: '', checkedAt: 0 });
        }
      }
      const parsed = parseLottery(info.lotteryData, info);
      if (parsed) {
        merged.lottery = parsed;
        state.rooms.set(item.webRid, merged);
        hits.push(merged);
        appendLog('房间「' + (info.title || item.webRid) + '」检测到福袋：' + parsed.title + '（' + parsed.conditions + '）', 'success');
      }
    } catch (e) {
      item.checkedAt = now;
    }
  }
  if (hits.length) renderRooms();
  else renderRooms();
  return hits;
}

async function enterRoom(room) {
  appendLog('进入直播间「' + (room.title || room.webRid) + '」尝试参与。');
  loadUrl('https://live.douyin.com/' + room.webRid);
  state.currentRoom = room.webRid;
  state.inRoomSince = Date.now();
}

async function tryJoinCurrentRoom() {
  if (state.joinBusy || !onLiveRoom()) return;
  state.joinBusy = true;
  try {
    const rid = currentWebRid();
    const cached = state.rooms.get(rid) || {};
    let data = null;
    try {
      const raw = await pageEval('(async () => { const r = await window.__dyfd.resolve(' + JSON.stringify(rid) + '); ' +
        'if (!r) return "null"; let d = r.lottery; if (!d) d = await window.__dyfd.lottery(r.roomId); ' +
        'return JSON.stringify(Object.assign({}, r, { lotteryData: d })); })()');
      if (raw && raw !== 'null') {
        const info = JSON.parse(raw);
        Object.assign(cached, info);
        state.rooms.set(rid, Object.assign(cached, { checkedAt: Date.now() }));
        data = info.lotteryData;
      }
    } catch (e) {}

    const dom = JSON.parse(await pageEval('JSON.stringify(window.__dyfd.domBag())') || '{}');
    const parsed = parseLottery(data, cached);
    const hasSignal = !!parsed || dom.hasBag;
    if (!hasSignal) return;

    const label = parsed ? parsed.title + '（' + parsed.conditions + '）' : (dom.bagNodes[0] ? dom.bagNodes[0].text : '页面福袋');
    addFound(cached, label, '已发现，尝试参与');

    const opened = JSON.parse(await pageEval('JSON.stringify(window.__dyfd.clickBag())') || '{}');
    if (opened.ok) {
      appendLog('已点击福袋入口：' + opened.text);
      await new Promise((r) => setTimeout(r, 1500));
    }
    const joined = JSON.parse(await pageEval('JSON.stringify(window.__dyfd.clickJoin())') || '{}');
    if (joined.ok) {
      addFound(cached, label, '已点击参与');
      appendLog('已在「' + (cached.title || rid) + '」点击参与：' + joined.text, 'success');
      return;
    }

    if (state.settings.autoFollow && /关注/.test(label)) {
      const followed = JSON.parse(await pageEval('JSON.stringify(window.__dyfd.clickFollow())') || '{}');
      if (followed.ok) {
        appendLog('已完成关注条件，重新尝试参与。');
        await new Promise((r) => setTimeout(r, 1200));
        const retry = JSON.parse(await pageEval('JSON.stringify(window.__dyfd.clickJoin())') || '{}');
        if (retry.ok) {
          addFound(cached, label, '已点击参与');
          appendLog('关注后参与成功。', 'success');
          return;
        }
      }
    }

    if (state.settings.allowDiamond === false && /钻石/.test(label)) {
      addFound(cached, label, '已跳过：需要钻石');
      appendLog('该福袋需要钻石，按设置跳过。');
      return;
    }

    const viaApi = parsed ? await pageEval('(async () => JSON.stringify(await window.__dyfd.callDraw(' +
      JSON.stringify(cached.roomId || '') + ',' + JSON.stringify(parsed.lotteryId) + ',' +
      JSON.stringify(cached.anchorId || '') + ')))()') : '{}';
    let apiResult = {};
    try { apiResult = JSON.parse(viaApi || '{}'); } catch (e) {}
    if (apiResult.ok) {
      addFound(cached, label, '已通过接口参与');
      appendLog('已通过页面接口提交参与请求。', 'success');
    } else {
      addFound(cached, label, '检测到，等待手动参与');
      appendLog('未能自动点击参与按钮，请在该直播间手动点击（' + (apiResult.err || '未捕获参与接口') + '）。', 'error');
    }
  } catch (e) {
    appendLog('参与流程异常：' + e.message, 'error');
  } finally {
    state.joinBusy = false;
  }
}

async function checkCaptcha() {
  try {
    const hit = await pageEval('window.__dyfd ? window.__dyfd.captcha() : false');
    if (hit) {
      $('captcha-alert').style.display = 'flex';
      if (Date.now() - state.captchaAlerted > 30000) {
        state.captchaAlerted = Date.now();
        appendLog('检测到验证码，已暂停扫描，请在左侧内置浏览器手动完成验证后重新开始。', 'error');
      }
      stopScanning('等待验证');
      return true;
    }
    $('captcha-alert').style.display = 'none';
  } catch (e) {}
  return false;
}

async function scanOnce() {
  if (!state.running) return;
  if (webview.isLoading()) return;
  try {
    if (await checkCaptcha()) return;

    if (state.currentRoom && currentWebRid() === state.currentRoom &&
        Date.now() - state.inRoomSince < ROOM_STAY && onLiveRoom()) {
      await tryJoinCurrentRoom();
      return;
    }

    if (onLiveRoom()) {
      await tryJoinCurrentRoom();
      if (Date.now() - state.inRoomSince < ROOM_STAY) return;
    }

    if (!/^https:\/\/live\.douyin\.com\//.test(currentPageUrl())) {
      loadUrl('https://live.douyin.com/');
      state.inRoomSince = Date.now();
      return;
    }

    if (state.rooms.size < 30) {
      await discoverRooms();
    }
    const hits = await resolveBatch();
    const target = hits.find((r) => !r.lottery || !r.lottery.drawn);
    if (target) {
      await enterRoom(target);
    } else if (!state.rooms.size) {
      await discoverRooms();
    }
  } catch (e) {
    appendLog('扫描异常：' + e.message, 'error');
  }
}

function readSettingsFromForm() {
  return Object.assign({}, state.settings, {
    checkInterval: Math.max(3, Number($('room-stay').value) || 5),
    maxPending: Math.max(1, Number($('max-pending').value) || 50),
    autoFollow: $('auto-follow').checked,
    allowComment: $('allow-comment').checked,
    allowDiamond: $('allow-diamond').checked,
  });
}

async function startScanning() {
  const login = await refreshLoginState();
  if (!login.loggedIn) {
    appendLog('尚未检测到登录 Cookie，请先点击“扫码登录”并完成登录。', 'error');
    loadUrl('https://www.douyin.com/');
    return;
  }
  state.settings = readSettingsFromForm();
  await window.desktop.saveSettings(state.settings);
  state.rooms.clear();
  state.visited.clear();
  renderRooms();
  if (!/^https:\/\/live\.douyin\.com\//.test(currentPageUrl())) {
    loadUrl('https://live.douyin.com/');
  }
  setRunState(true);
  state.inRoomSince = Date.now();
  state.currentRoom = '';
  appendLog('扫描已启动：从直播广场采集房间，并直接读取福袋接口。', 'success');
  await new Promise((r) => setTimeout(r, 1200));
  await scanOnce();
  state.timer = setInterval(scanOnce, (state.settings.checkInterval || 5) * 1000);
}

function stopScanning(label) {
  clearInterval(state.timer);
  state.timer = null;
  setRunState(false, label || '已停止');
  appendLog(label || '已停止');
}

/* --------------------------- 挂机引擎控制 --------------------------- */
function setEngineState(running, label) {
  $('engine-start').disabled = running;
  $('engine-stop').disabled = !running;
  $('engine-state').textContent = label || (running ? '运行中' : '未运行');
  $('engine-state').className = 'status ' + (running ? 'logged-in' : 'idle');
}

async function refreshDevices() {
  const sel = $('engine-device');
  const current = sel.value;
  sel.innerHTML = '<option value="">自动选择</option>';
  let res = null;
  try { res = await window.desktop.listDevices(); } catch (e) { res = { ok: false, error: e.message }; }
  if (!res || !res.ok) {
    $('engine-detail').textContent = 'ADB 不可用：' + ((res && res.error) || '未知错误');
    appendLog('设备检测失败：' + ((res && res.error) || 'adb 不可用'), 'error');
    return;
  }
  for (const d of res.devices) {
    const opt = document.createElement('option');
    opt.value = d.serial;
    opt.textContent = d.serial + (d.model ? '（' + d.model + '）' : '');
    sel.appendChild(opt);
  }
  if (current && [...sel.options].some((o) => o.value === current)) sel.value = current;
  $('engine-detail').textContent = res.devices.length
    ? '已发现 ' + res.devices.length + ' 台设备：' + res.devices.map((d) => d.serial).join('、')
    : '未发现设备。请连接手机并开启 USB 调试（adb devices 能列出才算连上）。';
  appendLog(
    res.devices.length ? '发现 ' + res.devices.length + ' 台 ADB 设备。' : '未发现 ADB 设备，请检查连接与 USB 调试。',
    res.devices.length ? 'success' : 'error'
  );
}

async function startEngine() {
  const device = $('engine-device').value;
  $('engine-detail').textContent = '正在启动引擎…（首次加载 OCR 模型约需 10 秒）';
  appendLog('正在启动挂机引擎' + (device ? '（设备 ' + device + '）' : '（自动选择设备）') + '…');
  let res = null;
  try { res = await window.desktop.startEngine(device); } catch (e) { res = { ok: false, error: e.message }; }
  if (!res || !res.ok) {
    appendLog('引擎启动失败：' + ((res && res.error) || '未知错误'), 'error');
    $('engine-detail').textContent = '启动失败：' + ((res && res.error) || '未知错误');
    setEngineState(false);
    return;
  }
  setEngineState(true, '运行中');
  $('engine-detail').textContent = '引擎已启动：' + res.path;
}

async function stopEngine() {
  await window.desktop.stopEngine();
  setEngineState(false, '已停止');
  $('engine-detail').textContent = '引擎已停止。';
  appendLog('挂机引擎已停止。');
}

if (window.desktop.onWorkerLog) {
  window.desktop.onWorkerLog((item) => {
    appendLog((item.stream === 'err' ? '[引擎/错误] ' : '[引擎] ') + item.line);
  });
}
if (window.desktop.onWorkerState) {
  window.desktop.onWorkerState((item) => {
    setEngineState(!!item.running, item.running ? '运行中' : '已停止');
  });
}
if (window.desktop.onWorkerExit) {
  window.desktop.onWorkerExit((item) => {
    setEngineState(false, '已退出');
    $('engine-detail').textContent = '引擎进程已退出（code=' + item.code + '）。';
    appendLog('引擎进程已退出，code=' + item.code, 'error');
  });
}

/* ------------------------- webview 事件绑定 ------------------------- */
webview.addEventListener('did-start-loading', () => { $('browser-status').textContent = '正在加载'; });
webview.addEventListener('dom-ready', async () => {
  $('browser-status').textContent = '页面已加载';
  $('address').value = currentPageUrl();
  await bridgeReady();
  await refreshLoginState();
});
webview.addEventListener('did-navigate', (e) => { $('address').value = e.url; });
webview.addEventListener('did-navigate-in-page', (e) => { $('address').value = e.url; });
webview.addEventListener('did-fail-load', (e) => {
  if (e.errorCode !== -3) $('browser-status').textContent = '加载失败：' + e.errorDescription;
});
// 抖音页面自身的第三方噪音：私信模块在嵌入环境里会被 CORS 拦掉，
// 随后页面代码对空响应读 .next_cursor 抛未捕获异常。与抢福袋无关，直接忽略。
const WEB_CONSOLE_IGNORED = new RegExp(
  [
    'Content Security Policy',
    'ERR_BLOCKED_BY_CLIENT',
    'third-party cookie',
    'ResizeObserver loop',
    'jsb 同名 JSB',
    'attribute viewBox',
    'CORS policy',
    'Access-Control-Allow-Origin',
    'imapi\\.douyin\\.com',
    'get_conversation_list',
    'next_cursor',
    'get_conversation_info',
  ].join('|'),
  'i'
);
let lastWebConsoleMsg = '';
let lastWebConsoleRepeat = 0;

webview.addEventListener('console-message', (e) => {
  if (!(e.level >= 3) || !e.message) return;
  if (WEB_CONSOLE_IGNORED.test(e.message)) return;
  // 同一条错误反复刷屏时，只在首次和每第 20 次记录，避免淹没引擎日志
  if (e.message === lastWebConsoleMsg) {
    lastWebConsoleRepeat += 1;
    if (lastWebConsoleRepeat % 20 === 0) {
      appendLog('网页提示：' + e.message + '（已重复 ' + lastWebConsoleRepeat + ' 次）', 'error');
    }
    return;
  }
  lastWebConsoleMsg = e.message;
  lastWebConsoleRepeat = 1;
  appendLog('网页提示：' + e.message, 'error');
});

$('back').onclick = () => webview.canGoBack() && webview.goBack();
$('forward').onclick = () => webview.canGoForward() && webview.goForward();
$('reload').onclick = () => webview.reload();
$('go').onclick = () => loadUrl($('address').value);
$('address').addEventListener('keydown', (e) => { if (e.key === 'Enter') loadUrl($('address').value); });
$('login-home').onclick = () => loadUrl('https://www.douyin.com/');
$('start').onclick = startScanning;
$('stop').onclick = () => stopScanning();
$('refresh-devices').onclick = () => refreshDevices();
$('engine-start').onclick = startEngine;
$('engine-stop').onclick = stopEngine;
$('clear-log').onclick = () => { $('log').textContent = ''; };
$('open-data').onclick = () => window.desktop.openDataDirectory();
$('close-captcha').onclick = () => { $('captcha-alert').style.display = 'none'; };
$('logout').onclick = async () => {
  stopScanning('已退出运行');
  await window.desktop.clearSession();
  loadUrl('https://www.douyin.com/');
  await refreshLoginState();
  appendLog('浏览器登录数据已清除。');
};
$('apply-proxy').onclick = async () => {
  const result = await window.desktop.setProxy($('proxy').value);
  appendLog(result.enabled ? '代理已应用，正在刷新页面。' : '代理已关闭，已恢复直连。');
  webview.reload();
};

window.desktop.onRequest((request) => {
  if (state.running && /lottery|draw/i.test(request.url)) {
    appendLog('捕获福袋接口：' + new URL(request.url).pathname);
  }
});

if (window.desktop.onOpenUrl) {
  window.desktop.onOpenUrl((url) => loadUrl(url));
}

async function initialize() {
  state.settings = await window.desktop.getSettings();
  $('room-stay').value = state.settings.checkInterval || 5;
  $('max-pending').value = state.settings.maxPending || 50;
  $('auto-follow').checked = !!state.settings.autoFollow;
  $('allow-comment').checked = !!state.settings.allowComment;
  $('allow-diamond').checked = !!state.settings.allowDiamond;
  await refreshLoginState();
  appendLog('内置浏览器会话已就绪。请扫码登录后开始扫描。');
  await refreshDevices();
  try {
    const st = await window.desktop.getEngineState();
    setEngineState(!!(st && st.running));
  } catch (e) { /* 忽略 */ }
}

initialize();
window.setInterval(() => { refreshLoginState().catch(() => {}); }, 4000);
