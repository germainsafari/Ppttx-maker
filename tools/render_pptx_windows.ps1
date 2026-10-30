param([Parameter(Mandatory)] [string]$Pptx, [string]$OutDir = "", [int]$Width = 1280)
# Export every slide of a .pptx to PNG using desktop PowerPoint (Windows-only test helper).
$Pptx = (Resolve-Path $Pptx).Path
if (-not $OutDir) { $OutDir = [IO.Path]::ChangeExtension($Pptx, $null).TrimEnd('.') + "_png" }
New-Item -ItemType Directory -Force $OutDir | Out-Null
$pp = New-Object -ComObject PowerPoint.Application
$p = $pp.Presentations.Open($Pptx, $true, $false, $false)
$h = [int]($Width * $p.PageSetup.SlideHeight / $p.PageSetup.SlideWidth)
$n = $p.Slides.Count
for ($i = 1; $i -le $n; $i++) { $p.Slides.Item($i).Export("$OutDir\s$('{0:D2}' -f $i).png", "PNG", $Width, $h) }
$p.Close()
"exported $n slides to $OutDir"
