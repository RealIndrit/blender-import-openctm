@echo off
setlocal

rem Specify the relative folder to compress, the copied folder, the output zip file, and the output directory
set FOLDER_TO_COMPRESS=.\src
set COPIED_FOLDER=.\openctm
set OUTPUT_ZIP=.\openctm_ctm_blender3.6.zip
set OUTPUT_DIR=..\

rem Copy the contents to the openctm folder
xcopy /E /I "%FOLDER_TO_COMPRESS%" "%COPIED_FOLDER%"

rem Check if the copied folder was created
if exist "%COPIED_FOLDER%" (
    echo Folder copied successfully.
) else (
    echo Failed to copy the folder.
    goto end
)

rem Use PowerShell to compress the copied folder
powershell -command "Compress-Archive -Path '%COPIED_FOLDER%' -DestinationPath '%OUTPUT_ZIP%' -Force"

rem Check if the zip file was created
if exist "%OUTPUT_ZIP%" (
    echo Folder compressed and zipped successfully.
) else (
    echo Failed to compress the folder.
    goto end
)

rem Change directory to the copied folder
cd "%COPIED_FOLDER%"

rem Run the Blender command
blender --command extension build --output-dir %OUTPUT_DIR%

rem Go back to the parent directory
cd ..

rem Remove the copied openctm folder
rmdir /S /Q "%COPIED_FOLDER%"

:end
endlocal
pause
