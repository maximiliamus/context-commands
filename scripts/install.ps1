$ErrorActionPreference = 'Stop'
$target = Join-Path (Get-Location).ProviderPath 'CONTEXT_COMMANDS.md'
if (Get-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue) {
    throw 'CONTEXT_COMMANDS.md already exists. Run update.ps1 to preserve custom commands.'
}

$content = Invoke-RestMethod 'https://raw.githubusercontent.com/maximiliamus/context-commands/master/CONTEXT_COMMANDS.md'
$marker = '(?m)^<!-- custom-context-commands -->(?=\r?$)'
if ($content -isnot [string] -or $content -notmatch '\A\uFEFF?# Context Commands\r?\n' -or
    [regex]::Matches($content, $marker).Count -ne 1) {
    throw 'Downloaded content is not a valid CONTEXT_COMMANDS.md. Nothing was installed.'
}

$temporary = "$target.$([guid]::NewGuid().ToString('N')).tmp"
try {
    [IO.File]::WriteAllText($temporary, $content, [Text.UTF8Encoding]::new($false))
    [IO.File]::Move($temporary, $target)
} finally {
    if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
}
Write-Host 'Installed CONTEXT_COMMANDS.md.'
