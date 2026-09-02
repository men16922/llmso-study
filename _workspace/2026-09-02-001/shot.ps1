# 프루프 카드 HTML을 PNG로 굽는다.
#   powershell -File shot.ps1 -Name proof-w5-01-fp8-budget -Height 640
# 확장 프로그램 경로(file:// 차단)와 로컬 HTTP 서버(PowerShell 세션과 함께 죽음)가
# 둘 다 이 환경에서 안 됐다. 헤드리스 Chrome이 file://을 직접 읽는 경로만 남는다.
param([string]$Name, [int]$Height = 1000, [int]$Width = 1600)
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = "file:///" + $dir.Replace(([char]92), "/") + "/$Name.html"
$out = Join-Path $dir "$Name.png"
Remove-Item $out -ErrorAction SilentlyContinue
& 'C:\Program Files\Google\Chrome\Application\chrome.exe' --headless=new --no-sandbox `
  --disable-gpu --hide-scrollbars --window-size="$Width,$Height" `
  --screenshot="$out" --virtual-time-budget=3000 $src 2>&1 | Out-Null
if (Test-Path $out) { "OK  $Name.png  $((Get-Item $out).Length) bytes" } else { "FAILED $Name" }
