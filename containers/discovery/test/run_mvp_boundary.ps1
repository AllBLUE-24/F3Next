# Run MVP boundary harness from repo root (user text -> LLM -> MVP boundary).
#
# Interactive (paste user story, blank line to finish):
#   .\containers\discovery\test\run_mvp_boundary.ps1
#
# From a file:
#   .\containers\discovery\test\run_mvp_boundary.ps1 -TranscriptFile .\story.txt
#
# Full chat JSON (multiple turns):
#   .\containers\discovery\test\run_mvp_boundary.ps1 -MessagesFile .\chat.json

param(
    [string]$Transcript = "",
    [string]$TranscriptFile = "",
    [string]$MessagesFile = "",
    [switch]$NoLlm,
    [string]$JsonOut = ""
)

$repoRoot = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
Set-Location $repoRoot

$args = @("-m", "containers.discovery.test.harness_mvp_boundary")

if ($Transcript) { $args += @("--transcript", $Transcript) }
if ($TranscriptFile) { $args += @("--transcript-file", $TranscriptFile) }
if ($MessagesFile) { $args += @("--messages-file", $MessagesFile) }
if ($NoLlm) { $args += "--no-llm" }
if ($JsonOut) { $args += @("--json-out", $JsonOut) }

python @args
