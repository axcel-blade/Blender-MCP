# Blender MCP Windows installer
# Installs uv if needed, the Python package, Blender addon, and optional MCP client config.
# Save this file as UTF-8 without BOM. A BOM breaks Windows PowerShell 5.1 parsers.

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

Write-Host "Blender MCP installer for Windows" -ForegroundColor Cyan

function Ensure-Uv {
    if (Get-Command uv -ErrorAction SilentlyContinue) { return }
    Write-Host "Installing uv..."
    winget install --id=astral-sh.uv -e --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "uv not found after install. Open a new terminal and re-run."
    }
}

function Save-JsonNoBom([string]$Path, $Object) {
    $text = $Object | ConvertTo-Json -Depth 20
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $text + [Environment]::NewLine, $utf8NoBom)
}

Ensure-Uv
Set-Location $RepoRoot
Write-Host "Syncing project with uv (Python + deps from uv.lock)..."
uv sync

Write-Host "Installing Blender addon..."
uv run blender-mcp install-addon

function Set-JsonMcpServer([string]$ConfigPath, [string]$RootKey, $Entry) {
    # Writes the blender-mcp entry under $RootKey. Creates the file if the
    # client's folder exists (client installed) but the config does not.
    $dir = Split-Path $ConfigPath -Parent
    if (-not (Test-Path $dir)) { return }
    $json = $null
    if (Test-Path $ConfigPath) {
        $raw = Get-Content $ConfigPath -Raw
        if ($raw -and $raw.Trim()) {
            try { $json = $raw | ConvertFrom-Json } catch {
                Write-Warning "Skipped $ConfigPath (not plain JSON; comments?). Add blender-mcp manually."
                return
            }
        }
        Copy-Item $ConfigPath "$ConfigPath.blender-mcp.bak" -Force
    }
    if (-not $json) { $json = [pscustomobject]@{} }
    if (-not $json.$RootKey) {
        $json | Add-Member -NotePropertyName $RootKey -NotePropertyValue ([pscustomobject]@{}) -Force
    }
    $json.$RootKey | Add-Member -NotePropertyName "blender-mcp" -NotePropertyValue $Entry -Force
    Save-JsonNoBom $ConfigPath $json
    Write-Host "Configured $ConfigPath"
}

function Invoke-Quiet([scriptblock]$Block) {
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $Block *> $null; return ($LASTEXITCODE -eq 0) } catch { return $false } finally { $ErrorActionPreference = $old }
}

function Register-McpClients([string]$RepoRoot) {
    $mcpArgs = @("run", "--directory", "$RepoRoot", "blender-mcp")
    $std = [pscustomobject]@{ command = "uv"; args = $mcpArgs }
    $vsc = [pscustomobject]@{ type = "stdio"; command = "uv"; args = $mcpArgs }

    # Clients configured through a JSON "mcpServers" file
    Set-JsonMcpServer (Join-Path $env:USERPROFILE ".cursor\mcp.json") "mcpServers" $std
    Set-JsonMcpServer (Join-Path $env:APPDATA "Claude\claude_desktop_config.json") "mcpServers" $std
    Set-JsonMcpServer (Join-Path $env:USERPROFILE ".codeium\windsurf\mcp_config.json") "mcpServers" $std
    Set-JsonMcpServer (Join-Path $env:USERPROFILE ".gemini\settings.json") "mcpServers" $std
    Set-JsonMcpServer (Join-Path $env:APPDATA "Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json") "mcpServers" $std
    Set-JsonMcpServer (Join-Path $env:APPDATA "Code\User\globalStorage\rooveterinaryinc.roo-cline\settings\mcp_settings.json") "mcpServers" $std

    # VS Code / VS Code Insiders (Copilot agent mode) use "servers"
    Set-JsonMcpServer (Join-Path $env:APPDATA "Code\User\mcp.json") "servers" $vsc
    Set-JsonMcpServer (Join-Path $env:APPDATA "Code - Insiders\User\mcp.json") "servers" $vsc

    # Claude Code: use its CLI (user scope)
    if (Get-Command claude -ErrorAction SilentlyContinue) {
        [void](Invoke-Quiet { claude mcp remove --scope user blender-mcp })
        if (Invoke-Quiet { claude mcp add --scope user blender-mcp -- uv @mcpArgs }) {
            Write-Host "Configured Claude Code (user scope)"
        } else { Write-Warning "Claude Code: 'claude mcp add' failed. Add blender-mcp manually." }
    }

    # Codex: use its CLI, else append to ~/.codex/config.toml
    if (Get-Command codex -ErrorAction SilentlyContinue) {
        [void](Invoke-Quiet { codex mcp remove blender-mcp })
        if (Invoke-Quiet { codex mcp add blender-mcp -- uv @mcpArgs }) {
            Write-Host "Configured Codex"
        } else { Write-Warning "Codex: 'codex mcp add' failed. Add blender-mcp manually." }
    } else {
        $toml = Join-Path $env:USERPROFILE ".codex\config.toml"
        if ((Test-Path (Split-Path $toml)) -and -not ((Test-Path $toml) -and (Select-String -Path $toml -Pattern '^\[mcp_servers\.blender-mcp\]' -Quiet))) {
            $p = $RepoRoot -replace '\\', '/'
            $block = "`n[mcp_servers.blender-mcp]`ncommand = `"uv`"`nargs = [`"run`", `"--directory`", `"$p`", `"blender-mcp`"]`n"
            [System.IO.File]::AppendAllText($toml, $block, (New-Object System.Text.UTF8Encoding $false))
            Write-Host "Configured $toml"
        }
    }
}

Write-Host "Configuring AI clients..."
Register-McpClients "$RepoRoot"

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "1. Open Blender -> Edit -> Preferences -> Add-ons -> enable 'Blender MCP'"
Write-Host "2. In the 3D Viewport press N -> AI / MCP -> Start"
Write-Host "3. Fully quit and reopen your AI client(s)"
Write-Host "Done."
