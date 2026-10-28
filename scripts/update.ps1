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
if ($null -eq $item) {
    throw 'CONTEXT_COMMANDS.md was not found in this directory. Run the install command from https://github.com/maximiliamus/context-commands#install.'
}
if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'CONTEXT_COMMANDS.md must be a regular file, not a directory or symbolic link. Nothing was changed.'
}

$marker = '(?m)^<!-- custom-context-commands -->(?=\r?$)'
try { $current = [IO.File]::ReadAllText($target) }
catch { throw "Could not read CONTEXT_COMMANDS.md. Check its permissions. Nothing was changed. $($_.Exception.Message)" }
$installedVersion = Get-ContextVersion $current 'Installed CONTEXT_COMMANDS.md has invalid version metadata. Check its YAML front matter; nothing was changed.'
try { $content = Invoke-RestMethod 'https://raw.githubusercontent.com/maximiliamus/context-commands/master/CONTEXT_COMMANDS.md' }
catch { throw "Could not download CONTEXT_COMMANDS.md from GitHub. Check your connection and try again. Nothing was changed. $($_.Exception.Message)" }
if ($content -isnot [string]) {
    throw 'Downloaded CONTEXT_COMMANDS.md is invalid. Nothing was changed; try again later.'
}
$availableVersion = Get-ContextVersion $content 'Downloaded CONTEXT_COMMANDS.md has invalid version metadata. Nothing was changed; try again later.'
if ($null -eq $availableVersion) { throw 'Downloaded CONTEXT_COMMANDS.md has no version in its YAML front matter. Nothing was changed; try again later.' }
if ($null -ne $installedVersion -and $installedVersion -ceq $availableVersion) {
    Write-Host "CONTEXT_COMMANDS.md version $availableVersion is already installed. Nothing was changed."
    return
}
$header = '\A\uFEFF?---\r?\n(?:(?!---(?:\r?\n|\z))[^\r\n]*\r?\n)*---\r?\n\r?\n# Context Commands\r?\n'
if ($content -notmatch $header) { throw 'Downloaded CONTEXT_COMMANDS.md is invalid. Nothing was changed; try again later.' }
$remoteMarkers = [regex]::Matches($content, $marker)
if ($remoteMarkers.Count -ne 1) {
    throw 'Downloaded CONTEXT_COMMANDS.md has an invalid custom-command marker. Nothing was changed; try again later.'
}
$localMarkers = [regex]::Matches($current, $marker)
if ($localMarkers.Count -ne 1) {
    throw 'Your CONTEXT_COMMANDS.md must contain exactly one <!-- custom-context-commands --> marker before custom commands. Nothing was changed.'
}
# Keep the entire local tail, including Unicode, whitespace and line endings.
$custom = $current.Substring($localMarkers[0].Index + $localMarkers[0].Length)

$updated = $content.Substring(0, $remoteMarkers[0].Index + $remoteMarkers[0].Length) + $custom

# Replace only after the complete download has been validated and merged.
$temporary = "$target.$([guid]::NewGuid().ToString('N')).tmp"
try {
    [IO.File]::WriteAllText($temporary, $updated, [Text.UTF8Encoding]::new($false))
    [IO.File]::Replace($temporary, $target, [System.Management.Automation.Language.NullString]::Value)
} catch {
    throw "Could not update CONTEXT_COMMANDS.md. Check permissions and close programs using the file. The original file was preserved. $($_.Exception.Message)"
} finally {
    if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
}
Write-Host "Updated CONTEXT_COMMANDS.md to version $availableVersion; custom commands were preserved."
