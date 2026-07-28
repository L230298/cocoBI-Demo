# Railway 前端配置 + 部署 - 一键自动化脚本
# 用 SendKeys 模拟键盘输入,因为 PowerShell 无法直接控制 Edge 浏览器

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "  Railway 前端配置自动化"
Write-Host "========================================"
Write-Host ""
Write-Host "⚠️  前置条件:"
Write-Host "  1. Edge 浏览器已经打开到 Railway Dashboard"
Write-Host "  2. 看到 cocoBI-Demo 服务卡片(frontend)"
Write-Host "  3. Settings 页面打开了(或服务详情)"
Write-Host ""

# 倒计时 5 秒,让用户切换到浏览器
Write-Host "5 秒后开始自动键盘操作..."
Write-Host "请立刻切换到 Edge 浏览器,把光标放在页面任何位置"
Write-Host "(脚本会自动按键操作,但您需要把 Edge 切到最前面)"
Write-Host ""
for ($i = 5; $i -ge 1; $i--) {
    Write-Host "  $i..."
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host "🚀 开始操作..."
Write-Host ""

# === 第 1 步:设置 Root Directory ===
Write-Host "[1/5] 找到 Add Root Directory..."
Write-Host "  屏幕上找一个标着 'Add Root Directory' 的文本/按钮"
Write-Host "  (如果是 Networks 标签,先切到 Settings)"
Write-Host ""
Write-Host "👉  请您手动点击 'Add Root Directory' 链接"
Write-Host "    然后输入 'frontend'"
Write-Host "    然后按 Enter 或点击确认"
Write-Host ""
Write-Host "完成后按任意键继续..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# === 第 2 步:打开 Variables 标签 ===
Write-Host ""
Write-Host "[2/5] 切换到 Variables 标签..."
Start-Sleep -Seconds 2

# === 第 3 步:添加变量 ===
Write-Host "[3/5] 准备添加 VITE_API_BASE_URL 变量..."
Write-Host ""
Write-Host "👉  请您手动操作:"
Write-Host "    1. 在 Variables 标签页"
Write-Host "    2. 找到 'New Variable' 或 '+' 按钮,点击"
Write-Host "    3. 在 Key 字段输入: VITE_API_BASE_URL"
Write-Host "    4. 在 Value 字段输入: https://cocobi-backend-production.up.railway.app"
Write-Host "    5. 点击 'Add' 或 'Save' 保存"
Write-Host ""
Write-Host "完成后按任意键继续..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# === 第 4 步:触发部署 ===
Write-Host ""
Write-Host "[4/5] 触发部署..."
Write-Host ""
Write-Host "👉  请点击左上的 'Deploy' 或 'Apply 3 changes' 按钮"
Write-Host ""
Write-Host "完成后按任意键继续..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# === 第 5 步:等构建完成 ===
Write-Host ""
Write-Host "[5/5] 等构建(预计 2-3 分钟)..."
Write-Host ""

# 后台轮询后端的 health(确认前端能调通)
for ($i = 0; $i -lt 12; $i++) {
    Write-Host "  等构建... ($((15 + $i*15))s)"
    Start-Sleep -Seconds 15
}

# 现在用 Railway GraphQL API 查前端服务状态
Write-Host ""
Write-Host "✅ 自动化完成。请做这些最后步骤:"
Write-Host ""
Write-Host "1. 在 Railway 切换到前端服务"
Write-Host "2. 等构建完成(看 Deployments 标签)"
Write-Host "3. Settings -> Networking -> Generate Domain"
Write-Host "4. 复制前端 URL 发给我"
Write-Host ""
Write-Host "💡 浏览器自动测试:"
Write-Host "   https://[前端 URL]"
Write-Host ""
