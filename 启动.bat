@echo off
cd /d "%~dp0"

set PY=python
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 goto nopython
  set PY=py
)

echo.
echo   中国医械标准库
echo   ----------------------------------------
echo   第一次运行需要联网抓取官方数据，约 7 分钟。
echo   屏幕会一行行滚动，正常，不要关窗口。
echo   抓完会生成一个网页并自动打开。
echo   以后要更新，再双击本文件即可。
echo   ----------------------------------------
echo.

%PY% run.py --open
if errorlevel 1 goto fail

echo.
echo   已生成页面，以后可以直接双击那个 html 文件打开。
pause
exit /b 0

:nopython
echo.
echo   没有找到 Python。本工具需要 Python 3.8 或更高版本。
echo   请到 python.org 下载安装，安装时勾选 "Add Python to PATH"，再双击本文件。
pause
exit /b 1

:fail
echo.
echo   运行没有完成。请把上面的文字截图发给提供者。
pause
exit /b 1
