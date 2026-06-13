const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    title: "Sentinel Forge: AI Log Analyzer",
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Load the React app (points to the Vite dev server in development)
  const devUrl = 'http://localhost:3000';
  
  win.loadURL(devUrl).catch(() => {
    // Fallback if dev server is not running
    win.loadFile(path.join(__dirname, 'dist/index.html'));
  });

  // Remove default menu bar
  win.setMenuBarVisibility(false);
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
