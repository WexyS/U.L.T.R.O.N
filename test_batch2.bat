@echo off
if 1 equ 1 (
    echo "testing powershell with parenthesis inside if"
    powershell -Command "try { $r=(Invoke-WebRequest 'http://localhost:4040/api/tunnels' -UseBasicParsing).Content | ConvertFrom-Json; $url=$r.tunnels[0].public_url; if($url) { (Get-Content ../.env) -replace '^NGROK_URL=.*','NGROK_URL='+$url | Set-Content ../.env; echo \"[NGROK] $url\"; } } catch { echo \"[NGROK] Tünel bilgisi henüz hazir degil.\" }"
)
echo "survived"
pause
