param([string]$Title = "", [string]$Out = "C:\TEKKEN\tools\snap_window.png")
Add-Type -TypeDefinition 'using System.Runtime.InteropServices; public class DpiHelper { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }'
[DpiHelper]::SetProcessDPIAware() | Out-Null
Add-Type -TypeDefinition '
using System;
using System.Runtime.InteropServices;
public class Win32 {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
}'
Add-Type -AssemblyName System.Drawing
$proc = Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*$Title*" } | Select-Object -First 1
if (-not $proc) { Write-Output "window not found: $Title"; exit 1 }
$r = New-Object Win32+RECT
[Win32]::GetWindowRect($proc.MainWindowHandle, [ref]$r) | Out-Null
$w = $r.Right - $r.Left; $h = $r.Bottom - $r.Top
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
[Win32]::PrintWindow($proc.MainWindowHandle, $hdc, 2) | Out-Null
$g.ReleaseHdc($hdc); $g.Dispose()
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
Write-Output "saved $Out ($w x $h) from window '$($proc.MainWindowTitle)'"
