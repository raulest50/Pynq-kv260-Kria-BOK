@echo off
setlocal
call C:\AMDDesignTools\2025.2\Vitis\settings64.bat
if errorlevel 1 exit /b %errorlevel%

set ROOT=%~dp0
call xclbinutil ^
  --add-section EMBEDDED_METADATA:RAW:"%ROOT%xclbin_source\metadata.xml" ^
  --add-section MEM_TOPOLOGY:JSON:"%ROOT%xclbin_source\mem.json" ^
  --output "%ROOT%bpm2d_kv260_kerr_interleaved_si.xclbin" ^
  --force
if errorlevel 1 exit /b %errorlevel%

call xclbinutil --info --input "%ROOT%bpm2d_kv260_kerr_interleaved_si.xclbin"
