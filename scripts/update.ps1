$ErrorActionPreference = 'Stop'
$target = Join-Path (Get-Location).ProviderPath 'CONTEXT_COMMANDS.md'
$item = Get-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
if ($null -eq $item -or $item.PSIsContainer -or
    ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'CONTEXT_COMMANDS.md must be a regular file. Run install.ps1 first if it is missing.'
}

$marker = '(?m)^<!-- custom-context-commands -->(?=\r?$)'
$current = [IO.File]::ReadAllText($target)
$localMarkers = [regex]::Matches($current, $marker)
if ($localMarkers.Count -ne 1) {
    throw 'Keep exactly one <!-- custom-context-commands --> line above your custom entries. Nothing was changed.'
}
# Keep the entire local tail, including Unicode, whitespace and line endings.
$custom = $current.Substring($localMarkers[0].Index + $localMarkers[0].Length)

$content = Invoke-RestMethod 'https://raw.githubusercontent.com/maximiliamus/context-commands/master/CONTEXT_COMMANDS.md'
if ($content -isnot [string] -or $content -notmatch '\A\uFEFF?# Context Commands\r?\n') {
    throw 'Downloaded content is not a valid CONTEXT_COMMANDS.md. Nothing was changed.'
}
$remoteMarkers = [regex]::Matches($content, $marker)
if ($remoteMarkers.Count -ne 1) {
    throw 'Downloaded content must contain exactly one custom-command marker. Nothing was changed.'
}
$updated = $content.Substring(0, $remoteMarkers[0].Index + $remoteMarkers[0].Length) + $custom

# Replace only after the complete download has been validated and merged.
$temporary = "$target.$([guid]::NewGuid().ToString('N')).tmp"
try {
    [IO.File]::WriteAllText($temporary, $updated, [Text.UTF8Encoding]::new($false))
    [IO.File]::Replace($temporary, $target, [System.Management.Automation.Language.NullString]::Value)
} finally {
    if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
}
Write-Host 'Updated CONTEXT_COMMANDS.md; custom commands were preserved.'
