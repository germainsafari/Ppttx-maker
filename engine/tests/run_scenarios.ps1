# Runs the three demo scenarios in parallel against the local LLM and renders PNG previews (Windows + PowerPoint).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location "$root\engine"
$env:PYTHONUNBUFFERED = "1"
$py = ".\.venv\Scripts\python"
$jobs = @(
  @{ name = "digital_platforms_14"; n = 14; files = @("..\Survey Dec 25 - Digital Platforms.pptx");
     prompt = "Create a presentation for the Digital Platforms team leads summarising their December 2025 satisfaction survey results compared to the company average: headline numbers, trends, strengths, pain points, what employees said, and recommended next steps." },
  @{ name = "credentials"; n = 8; files = @("tests\inputs\admind_website.txt");
     prompt = "Build an 8-slide Admind agency credentials deck for a first meeting with a large industrial energy company. Show who we are, our scale, how we work, the ABB case, what clients say and why we are a safe pair of hands." },
  @{ name = "campaign_q3"; n = 9; files = @("tests\inputs\campaign_q3.xlsx");
     prompt = "Prepare a Q3 2026 campaign performance review for the client Northwind Energy: results by quarter, channel performance, key learnings and the Q4 plan." }
)
$procs = foreach ($j in $jobs) {
  $args = @("-m", "app.cli", "-p", "`"$($j.prompt)`"", "-n", $j.n, "-o", "data\scenario_$($j.name)")
  foreach ($f in $j.files) { $args += @("-f", "`"$f`"") }
  Start-Process -FilePath $py -ArgumentList $args -NoNewWindow -PassThru -RedirectStandardOutput "data\scenario_$($j.name).log" -RedirectStandardError "data\scenario_$($j.name).err"
}
$procs | Wait-Process
foreach ($j in $jobs) {
  "==== $($j.name)"
  Get-Content "data\scenario_$($j.name).log" | Where-Object { $_ -match "PPTX|slides:|timings|llm:|WARN" }
  & powershell -ExecutionPolicy Bypass -File "$root\tools\render_pptx_windows.ps1" "data\scenario_$($j.name)\deck.pptx" | Out-Null
  & $py "$root\tools\contact_sheet.py" "data\scenario_$($j.name)\deck_png" | Out-Null
}
