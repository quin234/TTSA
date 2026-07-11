# Stockfish Installation Guide for TTSA

## Quick Installation (Recommended)

### Option 1: Using Chocolatey (Windows)
If you have Chocolatey package manager installed:
```powershell
choco install stockfish
```

### Option 2: Manual Download (Most Reliable)

1. **Download Stockfish:**
   - Visit: https://stockfishchess.org/download/
   - Download the Windows version (stockfish-windows-x86-64.zip)

2. **Extract the file:**
   - Right-click on the downloaded zip file
   - Select "Extract All..."
   - Extract to: `C:\Users\CEEJAY\Desktop\TTSA\`

3. **Rename the executable:**
   - Navigate to the extracted folder
   - Find the executable (usually named `stockfish-windows-x86-64.exe`)
   - Rename it to `stockfish.exe`
   - Move it to the project root: `C:\Users\CEEJAY\Desktop\TTSA\stockfish.exe`

4. **Verify installation:**
   - Open Command Prompt or PowerShell
   - Navigate to project directory: `cd C:\Users\CEEJAY\Desktop\TTSA`
   - Run: `.\stockfish.exe`
   - You should see Stockfish output starting with "Stockfish..."

## Alternative Installation Paths

If you prefer to install Stockfish elsewhere, you can configure the path in the settings:

### Install to Program Files
1. Extract Stockfish to `C:\Program Files\Stockfish\`
2. Rename executable to `stockfish.exe`
3. Update the configuration in `ttsa_app/stockfish_config.py`:

```python
STOCKFISH_CONFIG = {
    'executable': r'C:\Program Files\Stockfish\stockfish.exe',
    # ... other settings
}
```

## Verification

After installation, verify Stockfish is working:

```powershell
cd C:\Users\CEEJAY\Desktop\TTSA
.\stockfish.exe
```

Type `uci` and press Enter. You should see:
```
id name Stockfish ...
id author Stockfish ...
uciok
```

Type `quit` to exit.

## Troubleshooting

### "stockfish.exe not found"
- Ensure the file is named exactly `stockfish.exe`
- Check it's in the project root directory
- Verify file permissions (right-click → Properties)

### "Access Denied"
- Run Command Prompt as Administrator
- Check antivirus software isn't blocking the executable

### Stockfish doesn't start
- Ensure you downloaded the correct Windows version
- Try running from Command Prompt instead of PowerShell
- Check Windows Event Viewer for error details

## Next Steps

Once Stockfish is installed:
1. Start the Django development server
2. Navigate to the chess game
3. The system will automatically detect and use Stockfish
4. Check browser console for "Stockfish move:" messages to confirm it's working

## Fallback Mode

If Stockfish installation fails, the system will automatically use the custom JavaScript engine, so the chess game will still work perfectly without Stockfish.
