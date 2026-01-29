#!/usr/bin/env python3
"""
Build script for Windows executable (local testing)
This script automates the PyInstaller build process and tool bundling.
For production builds, use GitHub Actions workflow instead.
"""

import os
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path

def main():
    """Main build function"""
    print("=" * 60)
    print("GameManager Windows Build Script")
    print("=" * 60)
    
    # Check if we're on Windows
    if sys.platform != 'win32':
        print("⚠️  Warning: This script is designed for Windows.")
        print("   For Linux builds, use the standard Python installation.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return
    
    # Check PyInstaller
    print("\n[1/6] Checking PyInstaller...")
    try:
        import PyInstaller
        print(f"✅ PyInstaller found: {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
        print("✅ PyInstaller installed")
    
    # Check external tools
    print("\n[2/6] Checking external tools...")
    tools_dir = Path('tools/windows')
    tools_required = {
        'ffmpeg/ffmpeg.exe': 'FFmpeg',
        'ffmpeg/ffprobe.exe': 'FFprobe',
        'imagemagick/magick.exe': 'ImageMagick (magick – IM 7)',
        'yt-dlp.exe': 'yt-dlp',
    }
    
    missing_tools = []
    for tool_path, tool_name in tools_required.items():
        full_path = tools_dir / tool_path
        if full_path.exists():
            print(f"✅ {tool_name} found: {full_path}")
        else:
            print(f"⚠️  {tool_name} not found: {full_path}")
            missing_tools.append((tool_name, tool_path))
    
    if missing_tools:
        print("\n⚠️  Warning: Some tools are missing. The build will continue,")
        print("   but the executable may not work correctly without them.")
        print("\nMissing tools:")
        for tool_name, tool_path in missing_tools:
            print(f"  - {tool_name}: {tools_dir / tool_path}")
        print("\nDownload instructions:")
        print("  - FFmpeg: https://www.gyan.dev/ffmpeg/builds/")
        print("  - ImageMagick: https://imagemagick.org/script/download.php")
        print("  - yt-dlp: https://github.com/yt-dlp/yt-dlp/releases/latest")
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            return
    
    # Clean previous builds
    print("\n[3/6] Cleaning previous builds...")
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✅ Removed {dir_name}/")
    
    # Run PyInstaller
    print("\n[4/6] Running PyInstaller...")
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'PyInstaller', '--clean', 'gamemanager.spec'],
            check=True
        )
        print("✅ PyInstaller build completed")
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller build failed: {e}")
        return 1
    
    # Organize distribution
    print("\n[5/6] Organizing distribution...")
    dist_dir = Path('dist/gamemanager_windows')
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy executable
    exe_src = Path('dist/gamemanager.exe')
    if exe_src.exists():
        shutil.copy2(exe_src, dist_dir / 'gamemanager.exe')
        print(f"✅ Copied executable: {dist_dir / 'gamemanager.exe'}")
    else:
        print(f"❌ Executable not found: {exe_src}")
        return 1
    
    # Copy _internal folder
    internal_src = Path('dist/_internal')
    if internal_src.exists():
        shutil.copytree(internal_src, dist_dir / '_internal', dirs_exist_ok=True)
        print(f"✅ Copied _internal folder")
    
    # Copy tools
    if tools_dir.exists():
        shutil.copytree('tools', dist_dir / 'tools', dirs_exist_ok=True)
        print(f"✅ Copied tools directory")
    
    # Create var directory structure
    var_dir = dist_dir / 'var'
    (var_dir / 'config').mkdir(parents=True, exist_ok=True)
    (var_dir / 'db').mkdir(parents=True, exist_ok=True)
    (var_dir / 'task_logs').mkdir(parents=True, exist_ok=True)
    print(f"✅ Created var directory structure")
    
    # Copy README
    readme_src = Path('README_WINDOWS.md')
    if readme_src.exists():
        shutil.copy2(readme_src, dist_dir / 'README_WINDOWS.txt')
        print(f"✅ Copied README")
    
    # Create zip archive
    print("\n[6/6] Creating zip archive...")
    zip_path = Path('dist/gamemanager-windows-local.zip')
    if zip_path.exists():
        zip_path.unlink()
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(dist_dir)
                zipf.write(file_path, arcname)
                print(f"  Added: {arcname}")
    
    print(f"\n✅ Build complete!")
    print(f"\nDistribution folder: {dist_dir.absolute()}")
    print(f"Zip archive: {zip_path.absolute()}")
    print(f"\nYou can now test the executable by running:")
    print(f"  {dist_dir / 'gamemanager.exe'}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
