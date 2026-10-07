const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('desktop', {
  getLoginState: () => ipcRenderer.invoke('douyin:login-state'),
  clearSession: () => ipcRenderer.invoke('douyin:clear-session'),
  getRequests: () => ipcRenderer.invoke('douyin:requests'),
  setProxy: (value) => ipcRenderer.invoke('proxy:set', value),
  getSettings: () => ipcRenderer.invoke('settings:get'),
  saveSettings: (value) => ipcRenderer.invoke('settings:set', value),
  openDataDirectory: () => ipcRenderer.invoke('data:open'),
  writeLog: (line) => ipcRenderer.invoke('log:write', line),
  listDevices: () => ipcRenderer.invoke('worker:devices'),
  startEngine: (device) => ipcRenderer.invoke('worker:start', device),
  stopEngine: () => ipcRenderer.invoke('worker:stop'),
  getEngineState: () => ipcRenderer.invoke('worker:state'),
  onWorkerLog: (callback) => ipcRenderer.on('worker:log', (_event, item) => callback(item)),
  onWorkerState: (callback) => ipcRenderer.on('worker:state', (_event, item) => callback(item)),
  onWorkerExit: (callback) => ipcRenderer.on('worker:exit', (_event, item) => callback(item)),
  onRequest: (callback) => ipcRenderer.on('douyin:request', (_event, item) => callback(item)),
  onOpenUrl: (callback) => ipcRenderer.on('douyin:open-url', (_event, url) => callback(url)),
});
