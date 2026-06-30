@echo off
chcp 65001 >nul
title Agnes AI Toolkit
cls

echo ===================================================
echo   Cleaning up残留進程 (Streamlit / Node)...
echo ===================================================
taskkill /F /IM streamlit.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
echo   Done!
echo.

cd /d "D:\PV"

:menu
cls
echo ===================================================
echo          Agnes AI 服務啟動選單
echo ===================================================
echo   [1] 圖片生成
echo   [2] 影片生成
echo   [3] 強制重新清理背景進程
echo   [4] 離開退出
echo ===================================================
echo.

set /p choice="請輸入選項數字 (1-4): "

if "%choice%"=="1" goto menu_pic
if "%choice%"=="2" goto menu_vid
if "%choice%"=="3" goto clean_again
if "%choice%"=="4" goto exit_bat

echo   無效的選項，請重新輸入！
timeout /t 2 >nul
goto menu

:menu_pic
cls
echo ===================================================
echo          圖片生成 - 選擇供應商
echo ===================================================
echo   [1] Agnes 圖片生成 (agn_pic.py)
echo   [2] GRS  圖片生成 (grs_pic.py)
echo   [3] 返回主選單
echo ===================================================
echo.

set /p pic_choice="請輸入選項數字 (1-3): "

if "%pic_choice%"=="1" goto run_agn_pic
if "%pic_choice%"=="2" goto run_grs_pic
if "%pic_choice%"=="3" goto menu

echo   無效的選項，請重新輸入！
timeout /t 2 >nul
goto menu_pic

:run_agn_pic
cls
echo   正在啟動 Agnes 圖片生成工具 (agn_pic.py)...
echo   啟動成功後將自動開啟瀏覽器頁面。
echo   提示：若要停止服務，請在此視窗按下 Ctrl + C
echo ---------------------------------------------------
streamlit run agn_pic.py
pause
goto menu_pic

:run_grs_pic
cls
echo   正在啟動 GRS 圖片生成工具 (grs_pic.py)...
echo   啟動成功後將自動開啟瀏覽器頁面。
echo   提示：若要停止服務，請在此視窗按下 Ctrl + C
echo ---------------------------------------------------
streamlit run grs_pic.py
pause
goto menu_pic

:menu_vid
cls
echo ===================================================
echo          影片生成 - 選擇供應商
echo ===================================================
echo   [1] Agnes 影片生成 (agn_vid.py)
echo   [2] 返回主選單
echo ===================================================
echo.

set /p vid_choice="請輸入選項數字 (1-2): "

if "%vid_choice%"=="1" goto run_agn_vid
if "%vid_choice%"=="2" goto menu

echo   無效的選項，請重新輸入！
timeout /t 2 >nul
goto menu_vid

:run_agn_vid
cls
echo   正在啟動 Agnes 影片生成工具 (agn_vid.py)...
echo   啟動成功後將自動開啟瀏覽器頁面。
echo   提示：若要停止服務，請在此視窗按下 Ctrl + C
echo ---------------------------------------------------
streamlit run agn_vid.py
pause
goto menu_vid

:clean_again
cls
echo   正在重新強制殺死進程...
taskkill /F /IM streamlit.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
echo   清理完畢！
timeout /t 2 >nul
goto menu

:exit_bat
echo   感謝使用，祝你生成順利！
timeout /t 2 >nul
exit
