@echo off
setlocal

rem Specify the relative folder to compress and the output zip file
set FOLDER_TO_COMPRESS=.\src
set OUTPUT_ZIP=.\openctm_ctm_blender3.6.zip
set OUTPUT_DIR=..\

rem Use PowerShell to compress the folder
powershell -command "Compress-Archive -Path '%FOLDER_TO_COMPRESS%' -DestinationPath '%OUTPUT_ZIP%' -Force"

rem Check if the zip file was created
if exist "%OUTPUT_ZIP%" (
    echo Folder compressed successfully.
) else (
    echo Failed to compress the folder.
    goto end
)

rem Change directory to the target folder
cd "%FOLDER_TO_COMPRESS%"

rem Run the Blender command
blender --command extension build --output-dir %OUTPUT_DIR%

:end
endlocal
pause
