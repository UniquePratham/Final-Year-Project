const fs = require('fs');
const path = require('path');

const srcDir = path.join(__dirname, '../frontend/dist');
const destDir = path.join(__dirname, 'dist');

function copyRecursive(src, dest) {
  const exists = fs.existsSync(src);
  const stats = exists && fs.statSync(src);
  const isDirectory = exists && stats.isDirectory();
  
  if (isDirectory) {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }
    fs.readdirSync(src).forEach((child) => {
      copyRecursive(path.join(src, child), path.join(dest, child));
    });
  } else {
    fs.copyFileSync(src, dest);
  }
}

if (fs.existsSync(srcDir)) {
  console.log(`Copying built frontend from ${srcDir} to ${destDir}...`);
  if (fs.existsSync(destDir)) {
    fs.rmSync(destDir, { recursive: true, force: true });
  }
  copyRecursive(srcDir, destDir);
  console.log('Frontend assets copied successfully.');
} else {
  console.error('Error: Build frontend first using npm run build in frontend directory.');
  process.exit(1);
}
