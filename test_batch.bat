@echo off
if 1 equ 1 (
    echo "test"
    powershell -Command "if($url) { echo 'hi' }"
) else (
    echo "else"
)
pause
