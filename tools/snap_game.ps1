param([string]$Out = "C:\TEKKEN\tools\game_snap.png")
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WCX {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
  public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
$p = Get-Process -Name "Tekken Tag Tournament 2" | Select-Object -First 1
$rect = New-Object WCX+RECT
[WCX]::GetWindowRect($p.MainWindowHandle, [ref]$rect) | Out-Null
$w = [int]$rect.Right - [int]$rect.Left; $h = [int]$rect.Bottom - [int]$rect.Top
$bmp = New-Object System.Drawing.Bitmap($w, $h)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
[WCX]::PrintWindow($p.MainWindowHandle, $hdc, 2) | Out-Null
$g.ReleaseHdc($hdc); $g.Dispose()
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
Write-Output "saved $Out (${w}x${h})"
