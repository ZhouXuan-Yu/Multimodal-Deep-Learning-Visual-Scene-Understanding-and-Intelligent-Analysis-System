/**
 * 端口同步工具
 * 读取后端创建的port.txt并更新到localStorage中供前端使用
 */
const fs = require('fs');
const path = require('path');

// 配置项
const portFilePath = path.join(__dirname, 'port.txt');
const fallbackPort = 8001; // 如果读取失败，使用此默认端口

function syncPort() {
  console.log('正在同步后端端口配置...');
  
  try {
    // 检查端口文件是否存在
    if (fs.existsSync(portFilePath)) {
      // 读取后端端口
      const port = fs.readFileSync(portFilePath, 'utf8').trim();
      const portNumber = parseInt(port, 10);
      
      if (!isNaN(portNumber) && portNumber > 0 && portNumber < 65536) {
        console.log(`✅ 已从port.txt文件读取端口: ${portNumber}`);
        
        // 更新到指定文件用于前端读取
        updateFrontendPort(portNumber);
        return portNumber;
      } else {
        console.error(`❌ 端口文件内容无效: ${port}`);
      }
    } else {
      console.error(`❌ 端口文件不存在: ${portFilePath}`);
    }
  } catch (error) {
    console.error(`❌ 读取端口文件时出错: ${error.message}`);
  }
  
  console.log(`使用默认端口: ${fallbackPort}`);
  updateFrontendPort(fallbackPort);
  return fallbackPort;
}

function updateFrontendPort(port) {
  try {
    // 将端口写入localStorage配置文件
    const configPath = path.join(__dirname, 'ModelService', 'Vue', 'src', 'port_config.js');
    const configContent = `// 自动生成的端口配置文件 - 请勿手动修改
// 由port_sync.js于 ${new Date().toISOString()} 生成

export const BACKEND_PORT = ${port};
export default BACKEND_PORT;
`;
    
    fs.writeFileSync(configPath, configContent, 'utf8');
    console.log(`✅ 已更新前端端口配置文件: ${configPath}`);
    
    // 创建简单的HTML文件用于在浏览器中手动设置localStorage
    const htmlPath = path.join(__dirname, 'set_backend_port.html');
    const htmlContent = `<!DOCTYPE html>
<html>
<head>
  <title>设置后端端口</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
    .success { color: green; }
    .error { color: red; }
    button { padding: 10px; margin-top: 10px; cursor: pointer; }
  </style>
</head>
<body>
  <h1>后端端口配置工具</h1>
  <p>当前检测到的后端端口: <strong>${port}</strong></p>
  <button id="setPort">设置此端口到localStorage</button>
  <p id="status"></p>
  
  <script>
    document.getElementById('setPort').addEventListener('click', function() {
      try {
        localStorage.setItem('backendPort', '${port}');
        document.getElementById('status').innerHTML = 
          '<span class="success">✅ 成功设置端口! 现在可以关闭此页面并刷新应用。</span>';
      } catch (e) {
        document.getElementById('status').innerHTML = 
          '<span class="error">❌ 设置失败: ' + e.message + '</span>';
      }
    });
  </script>
</body>
</html>`;
    
    fs.writeFileSync(htmlPath, htmlContent, 'utf8');
    console.log(`✅ 已创建端口设置工具: ${htmlPath}`);
    
  } catch (error) {
    console.error(`❌ 更新前端配置时出错: ${error.message}`);
  }
}

// 执行端口同步
const port = syncPort();
console.log(`端口同步完成，使用端口: ${port}`);

// 如果从命令行直接运行此脚本
if (require.main === module) {
  console.log('端口同步工具完成运行。');
  console.log('请在前端代码中导入port_config.js使用BACKEND_PORT变量');
  console.log('或者打开set_backend_port.html在浏览器中设置localStorage');
}

module.exports = { syncPort };
