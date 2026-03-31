@echo off
cd /d "%~dp0"
echo Available models - double-click any start-*.bat file:
echo.
echo   onnx-asr (GPU/DirectML):
echo     start-parakeet.bat          - Fastest, good European langs
echo     start-whisper-base.bat      - Smallest, quick test
echo     start-whisper-small.bat     - Good balance
echo     start-whisper-medium.bat    - Better quality
echo     start-whisper-large-turbo.bat - Fast large model
echo     start-whisper-large.bat     - Best quality (slow on CPU)
echo.
echo   faster-whisper (CPU, int8 optimized):
echo     start-faster-base.bat       - Fastest
echo     start-faster-small.bat      - Good balance
echo     start-faster-medium.bat     - Better quality
echo     start-faster-large-turbo.bat - Fast large model
echo     start-faster-large.bat      - Best quality
echo.
echo   whisper.cpp (CPU, C++ optimized):
echo     start-cpp-base.bat          - Fastest
echo     start-cpp-small.bat         - Good balance
echo     start-cpp-medium.bat        - Better quality
echo     start-cpp-large-turbo.bat   - Fast large model
echo     start-cpp-large.bat         - Best quality
echo.
echo Starting default (whisper-large-v3-turbo on onnx-asr)...
echo.
python main.py onnx-community/whisper-large-v3-turbo
pause
