param(
  [Parameter(Mandatory=$true)]
  [string]$MrUrl
)

$SkillRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptPath = Join-Path $SkillRoot "scripts\mr_prep.py"

python $ScriptPath $MrUrl
