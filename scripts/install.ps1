$ErrorActionPreference = 'Stop'
$target = Join-Path (Get-Location).ProviderPath 'CONTEXT_COMMANDS.md'
$frontMatter = '\A\uFEFF?---\r?\n(?<metadata>(?:[^\r\n]*\r?\n)*?)---(?=\r?\n|\z)'
function Get-ContextVersion([string]$Text, [string]$InvalidMessage) {
    $block = [regex]::Match($Text, $frontMatter)
    if (-not $block.Success) {
        if ($Text -match '\A\uFEFF?---(?:\r?\n|\z)') { throw $InvalidMessage }
        return $null
    }
    $fields = [regex]::Matches($block.Groups['metadata'].Value, '(?m)^version[ \t]*:[ \t]*(?<value>[^\r\n]*)\r?$')
    if ($fields.Count -eq 0) { return $null }
    if ($fields.Count -ne 1) { throw $InvalidMessage }
    $value = $fields[0].Groups['value'].Value.Trim()
    if ($value.StartsWith("'") -or $value.StartsWith('"')) {
        $closing = $value.IndexOf($value[0], 1)
        if ($closing -lt 1 -or ($value.Substring($closing + 1).Trim() -notmatch '^(?:#.*)?$')) {
            throw $InvalidMessage
        }
        $value = $value.Substring(1, $closing - 1)
    } else {
        if ($value.StartsWith('#')) { throw $InvalidMessage }
        $value = [regex]::Replace($value, '[ \t]+#.*$', '').Trim()
    }
    if ([string]::IsNullOrWhiteSpace($value)) { throw $InvalidMessage }
    return $value
}
$item = Get-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
if ($item -and ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint))) {
    throw 'CONTEXT_COMMANDS.md must be a regular file, not a directory or symbolic link. Nothing was changed.'
}
$installedVersion = $null
if ($item) {
    try { $current = [IO.File]::ReadAllText($target) }
    catch { throw "Could not read CONTEXT_COMMANDS.md. Check its permissions. Nothing was changed. $($_.Exception.Message)" }
    $installedVersion = Get-ContextVersion $current 'Installed CONTEXT_COMMANDS.md has invalid version metadata. Check its YAML front matter; nothing was changed.'
}

try { $content = Invoke-RestMethod 'https://raw.githubusercontent.com/maximiliamus/context-commands/master/CONTEXT_COMMANDS.md' }
catch { throw "Could not download CONTEXT_COMMANDS.md from GitHub. Check your connection and try again. Nothing was changed. $($_.Exception.Message)" }
$marker = '(?m)^<!-- custom-context-commands -->(?=\r?$)'
if ($content -isnot [string]) {
    throw 'Downloaded CONTEXT_COMMANDS.md is invalid. Nothing was installed; try again later.'
}
$availableVersion = Get-ContextVersion $content 'Downloaded CONTEXT_COMMANDS.md has invalid version metadata. Nothing was installed; try again later.'
if ($null -eq $availableVersion) { throw 'Downloaded CONTEXT_COMMANDS.md has no version in its YAML front matter. Nothing was installed; try again later.' }
if ($null -ne $installedVersion -and $installedVersion -ceq $availableVersion) {
    Write-Host "CONTEXT_COMMANDS.md version $availableVersion is already installed. Nothing was changed."
    return
}
if ($item) {
    throw 'A different or unknown version is already installed. Run the update command from https://github.com/maximiliamus/context-commands#update. Nothing was changed.'
}
$header = '\A\uFEFF?---\r?\n(?:(?!---(?:\r?\n|\z))[^\r\n]*\r?\n)*---\r?\n\r?\n# Context Commands\r?\n'
if ($content -notmatch $header -or [regex]::Matches($content, $marker).Count -ne 1) {
    throw 'Downloaded CONTEXT_COMMANDS.md is invalid. Nothing was installed; try again later.'
}

$temporary = "$target.$([guid]::NewGuid().ToString('N')).tmp"
try {
    [IO.File]::WriteAllText($temporary, $content, [Text.UTF8Encoding]::new($false))
    [IO.File]::Move($temporary, $target)
} catch {
    throw "Could not install CONTEXT_COMMANDS.md. Check the directory permissions and try again. Nothing was installed. $($_.Exception.Message)"
} finally {
    if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
}
Write-Host "Installed CONTEXT_COMMANDS.md (version $availableVersion)."
Write-Host 'To enable the commands, add "Read @CONTEXT_COMMANDS.md and follow it." to your agent instructions, such as AGENTS.md.'
