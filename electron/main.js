const { app, BrowserWindow, ipcMain, session, shell } = require('electron');
const { spawn, execFile } = require('child_process');
const fs = require('fs');
const path = require('path');

if (process.env.DYFD_DEBUG_PORT) {
  app.commandLine.appendSwitch('remote-debugging-port', process.env.DYFD_DEBUG_PORT);
  app.commandLine.appendSwitch('remote-allow-origins', '*');
}

if (process.env.PORTABLE_EXECUTABLE_DIR) {
  app.setPath('userData', path.join(process.env.PORTABLE_EXECUTABLE_DIR, 'data'));
}

const DOUYIN_PARTITION = 'persist:douyin';
const LOGIN_COOKIES = new Set(['sessionid', 'sessionid_ss', 'sid_guard', 'sid_tt', 'uid_tt']);
const DEFAULT_SETTINGS = {
  checkInterval: 5,
  maxPending: 50,
  autoFollow: true,
  allowComment: false,
  allowDiamond: false,
  comments: ['来了', '支持主播', '祝大家好运'],
};

let mainWindow;
let requestLog = [];

function dataPath(...parts) {
  return path.join(app.getPath('userData'), ...parts);
}

function settingsPath() {
  return dataPath('settings.json');
}

function logFilePath() {
  const d = new Date();
  const stamp = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
  return dataPath('logs', `run-${stamp}.log`);
}

function appendLogLine(line) {
  try {
    fs.mkdirSync(dataPath('logs'), { recursive: true });
    fs.appendFileSync(logFilePath(), `${line}\n`, 'utf8');
  } catch {
    /* 日志写入失败不影响主流程 */
  }
}

function ensureDataFiles() {
  fs.mkdirSync(dataPath('logs'), { recursive: true });
  if (!fs.existsSync(settingsPath())) {
    fs.writeFileSync(settingsPath(), JSON.stringify(DEFAULT_SETTINGS, null, 2), 'utf8');
  }
}

function readSettings() {
  ensureDataFiles();
  try {
    return { ...DEFAULT_SETTINGS, ...JSON.parse(fs.readFileSync(settingsPath(), 'utf8')) };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

function writeSettings(value) {
  const settings = { ...DEFAULT_SETTINGS, ...value };
  fs.writeFileSync(settingsPath(), JSON.stringify(settings, null, 2), 'utf8');
  return settings;
}

function send(channel, payload) {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send(channel, payload);
}

/* ------------------------------------------------------------------ *
 * ADB 挂机引擎
 * 抖音网页版已下线福袋功能（lottery_info 返回“系统升级中，暂不支持”），
 * 真正能抓福袋的只有手机端 App。这里把「ADB + 手机端抖音 + PaddleOCR」引擎
 * 接进界面：优先用随包附带的 douyin_guaji_worker.exe，其次回退到本机 Python + worker.py。
 * ------------------------------------------------------------------ */

let workerProc = null;

function adbExecutable() {
  const candidates = [];
  if (process.env.ANDROID_HOME) candidates.push(path.join(process.env.ANDROID_HOME, 'platform-tools', 'adb.exe'));
  if (process.env.ANDROID_SDK_ROOT) candidates.push(path.join(process.env.ANDROID_SDK_ROOT, 'platform-tools', 'adb.exe'));
  if (process.env.LOCALAPPDATA) candidates.push(path.join(process.env.LOCALAPPDATA, 'Android', 'Sdk', 'platform-tools', 'adb.exe'));
  candidates.push('C:\\Users\\Administrator\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe');
  candidates.push('C:\\Program Files\\Nox\\bin\\nox_adb.exe');
  candidates.push('adb');
  for (const c of candidates) {
    if (c === 'adb' || fs.existsSync(c)) return c;
  }
  return 'adb';
}

function engineCandidates() {
  const list = [];
  const exeDir = process.env.PORTABLE_EXECUTABLE_DIR || path.dirname(app.getPath('exe'));
  const pyExes = [
    process.env.DYFD_PYTHON,
    'C:\\Users\\Administrator\\anaconda3\\python.exe',
    'py',
    'python',
    'python3',
  ].filter(Boolean);

  // 1) 冻结引擎 exe：resources/worker → exe 同级 → exe/resources/worker
  const exeDirs = [];
  if (process.resourcesPath) exeDirs.push(path.join(process.resourcesPath, 'worker'));
  exeDirs.push(exeDir);
  exeDirs.push(path.join(exeDir, 'resources', 'worker'));
  for (const d of exeDirs) list.push({ kind: 'exe', cmd: path.join(d, 'douyin_guaji_worker.exe') });

  // 2) 随包附带的引擎源码 + 本机 Python
  if (process.resourcesPath) {
    const bundledScript = path.join(process.resourcesPath, 'assets', 'engine', 'worker.py');
    for (const py of pyExes) list.push({ kind: 'py', cmd: py, script: bundledScript });
  }

  // 3) 开发目录里的引擎源码 + 本机 Python
  const projectRoot = path.join(__dirname, '..');
  for (const py of pyExes) list.push({ kind: 'py', cmd: py, script: path.join(projectRoot, 'worker.py') });

  return list;
}

function runAdbDevices() {
  return new Promise((resolve) => {
    const adb = adbExecutable();
    execFile(adb, ['devices', '-l'], { windowsHide: true, timeout: 8000 }, (err, stdout) => {
      const text = String(stdout || '');
      if (err && !text) {
        return resolve({ ok: false, error: String((err && err.message) || err), adb, devices: [] });
      }
      const devices = [];
      for (const line of text.split(/\r?\n/)) {
        const m = line.match(/^(\S+)\s+(\S+)(.*)$/);
        if (!m || m[2] !== 'device') continue;
        const model = (m[3].match(/model:(\S+)/) || [])[1] || '';
        devices.push({ serial: m[1], model });
      }
      resolve({ ok: true, adb, devices });
    });
  });
}

function emitWorkerLog(stream, buf) {
  const text = Buffer.isBuffer(buf) ? buf.toString('utf8') : String(buf);
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/\s+$/, '');
    if (line) send('worker:log', { stream, line });
  }
}

function startWorker(device) {
  return new Promise((resolve) => {
    if (workerProc) return resolve({ ok: false, error: '引擎已在运行' });
    const cwd = dataPath('engine');
    fs.mkdirSync(cwd, { recursive: true });
    seedEngineAssets(cwd);
    const env = Object.assign({}, process.env, {
      PYTHONIOENCODING: 'utf-8',
      PYTHONUNBUFFERED: '1',
      PYTHONUTF8: '1',
      DYFD_DATA_DIR: cwd,
      DYFD_DEVICE: device || '',
      PATH: path.dirname(adbExecutable()) + path.delimiter + (process.env.PATH || ''),
    });
    const candidates = engineCandidates();
    let idx = 0;

    const tryNext = () => {
      if (idx >= candidates.length) {
        return resolve({ ok: false, error: '未找到可用的挂机引擎：需要随包的 douyin_guaji_worker.exe，或本机安装 Python 并保留 worker.py。' });
      }
      const cand = candidates[idx++];
      let cmd, args;
      if (cand.kind === 'exe') {
        if (!fs.existsSync(cand.cmd)) return tryNext();
        cmd = cand.cmd;
        args = device ? ['--device', device] : [];
      } else {
        if (!cand.script || !fs.existsSync(cand.script)) return tryNext();
        cmd = cand.cmd;
        args = [cand.script].concat(device ? ['--device', device] : []);
      }

      let proc;
      try {
        proc = spawn(cmd, args, { cwd: cand.cwd || cwd, env, windowsHide: true });
      } catch {
        return tryNext();
      }

      let settled = false;
      proc.on('error', () => { if (!settled) { settled = true; tryNext(); } });
      proc.stdout && proc.stdout.on('data', (b) => emitWorkerLog('out', b));
      proc.stderr && proc.stderr.on('data', (b) => emitWorkerLog('err', b));
      proc.on('spawn', () => {
        settled = true;
        workerProc = proc;
        appendLogLine('[engine] 已启动: ' + cmd + ' ' + args.join(' '));
        send('worker:state', { running: true, command: cmd, device: device || '' });
        resolve({ ok: true, path: cmd, kind: cand.kind, device: device || '' });
      });
      proc.on('exit', (code, signal) => {
        workerProc = null;
        appendLogLine('[engine] 进程退出 code=' + code + ' signal=' + signal);
        send('worker:state', { running: false, code, signal });
        send('worker:exit', { code, signal });
      });
    };

    tryNext();
  });
}

function stopWorker() {
  return new Promise((resolve) => {
    if (!workerProc) return resolve({ ok: true, already: true });
    const pid = workerProc.pid;
    const proc = workerProc;
    try {
      if (process.platform === 'win32') {
        spawn('taskkill', ['/pid', String(pid), '/T', '/F'], { windowsHide: true });
      } else {
        process.kill(pid, 'SIGTERM');
      }
    } catch {
      /* 忽略 */
    }
    const timer = setTimeout(() => {
      try { proc.kill('SIGKILL'); } catch { /* 忽略 */ }
      resolve({ ok: true });
    }, 4000);
    proc.once('exit', () => { clearTimeout(timer); resolve({ ok: true }); });
  });
}

function killWorkerSync() {
  if (!workerProc) return;
  try {
    if (process.platform === 'win32') spawn('taskkill', ['/pid', String(workerProc.pid), '/T', '/F'], { windowsHide: true });
    else process.kill(workerProc.pid, 'SIGKILL');
  } catch {
    /* 忽略 */
  }
}

/* 引擎运行目录需要自带 target_pic 模板与 config.json（引擎按工作目录相对查找）。 */
function assetRoots() {
  const roots = [];
  if (process.resourcesPath) {
    roots.push(path.join(process.resourcesPath, 'assets', 'engine'));
    roots.push(path.join(process.resourcesPath, 'assets'));
  }
  roots.push(path.join(__dirname, '..'));
  return roots;
}

function findAsset(name) {
  for (const r of assetRoots()) {
    const p = path.join(r, name);
    if (fs.existsSync(p)) return p;
  }
  return null;
}

function copyDir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const name of fs.readdirSync(src)) {
    const s = path.join(src, name);
    const d = path.join(dst, name);
    if (fs.statSync(s).isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

function seedEngineAssets(cwd) {
  fs.mkdirSync(path.join(cwd, 'pic'), { recursive: true });
  fs.mkdirSync(path.join(cwd, 'pic', 'save'), { recursive: true });
  const tp = findAsset('target_pic');
  if (tp) {
    try { copyDir(tp, path.join(cwd, 'target_pic')); } catch { /* 忽略 */ }
  }
  const dstCfg = path.join(cwd, 'config.json');
  const cfg = findAsset('config.json');
  if (cfg && !fs.existsSync(dstCfg)) {
    try { fs.copyFileSync(cfg, dstCfg); } catch { /* 忽略 */ }
  }
}


function summarizeRequest(details) {
  let hostname;
  try {
    hostname = new URL(details.url).hostname;
  } catch {
    return;
  }
  if (!/(^|\.)(douyin|douyinvod|byteimg|snssdk)\.com$/i.test(hostname)) return;
  if (!/(?:live|webcast|room|lottery|lucky|gift|bag|follow|aweme)/i.test(details.url)) return;
  const entry = { at: Date.now(), method: details.method, status: details.statusCode, url: details.url };
  requestLog.push(entry);
  requestLog = requestLog.slice(-300);
  send('douyin:request', entry);
}

function setupDouyinSession() {
  const douyinSession = session.fromPartition(DOUYIN_PARTITION);
  douyinSession.setUserAgent(
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
    'Chrome/136.0.0.0 Safari/537.36'
  );
  douyinSession.webRequest.onCompleted(
    {
      urls: [
        '*://*.douyin.com/*',
        '*://*.douyinvod.com/*',
        '*://*.snssdk.com/*',
        '*://*.byteimg.com/*',
        '*://*.douyincdn.com/*',
      ],
    },
    summarizeRequest
  );
}

async function getLoginState() {
  const cookies = await session.fromPartition(DOUYIN_PARTITION).cookies.get({ domain: '.douyin.com' });
  const names = new Set(cookies.map((cookie) => cookie.name));
  const loggedIn = [...LOGIN_COOKIES].some((name) => names.has(name));
  return {
    loggedIn,
    cookieCount: cookies.length,
    accountKey: cookies.find((cookie) => ['uid_tt', 'sessionid'].includes(cookie.name))?.value.slice(0, 8) || '',
  };
}

async function setProxy(proxyRules) {
  const douyinSession = session.fromPartition(DOUYIN_PARTITION);
  const rules = String(proxyRules || '').trim();
  await douyinSession.setProxy(rules ? { proxyRules: rules } : { mode: 'direct' });
  await douyinSession.closeAllConnections();
  return { ok: true, enabled: Boolean(rules) };
}

function createWindow() {
  ensureDataFiles();
  mainWindow = new BrowserWindow({
    width: 1420,
    height: 900,
    minWidth: 1060,
    minHeight: 680,
    backgroundColor: '#f2f2f2',
    title: '抖音福袋万花筒',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webviewTag: true,
    },
  });
  mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
  mainWindow.on('closed', () => { mainWindow = null; });
}

ipcMain.handle('douyin:login-state', getLoginState);
ipcMain.handle('douyin:clear-session', async () => {
  const douyinSession = session.fromPartition(DOUYIN_PARTITION);
  await douyinSession.clearStorageData({ storages: ['cookies', 'localstorage', 'indexdb', 'serviceworkers'] });
  return { ok: true };
});
ipcMain.handle('douyin:requests', () => requestLog.slice());
ipcMain.handle('proxy:set', (_event, value) => setProxy(value));
ipcMain.handle('settings:get', () => readSettings());
ipcMain.handle('settings:set', (_event, value) => writeSettings(value));
ipcMain.handle('log:write', (_event, line) => { appendLogLine(String(line)); return { ok: true }; });
ipcMain.handle('data:open', () => shell.openPath(app.getPath('userData')));

// 挂机引擎（ADB + 手机端抖音）
ipcMain.handle('worker:devices', () => runAdbDevices());
ipcMain.handle('worker:start', (_event, device) => startWorker(device));
ipcMain.handle('worker:stop', () => stopWorker());
ipcMain.handle('worker:state', () => ({ running: !!workerProc, adb: adbExecutable() }));

// 站内新开窗口统一在内置浏览器中打开，避免弹出无法控制的独立窗口
app.on('web-contents-created', (_event, contents) => {
  contents.setWindowOpenHandler(({ url }) => {
    if (mainWindow && /^https?:\/\//i.test(url)) {
      mainWindow.webContents.send('douyin:open-url', url);
    }
    return { action: 'deny' };
  });
});

app.whenReady().then(() => {
  setupDouyinSession();
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  killWorkerSync();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', killWorkerSync);
