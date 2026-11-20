# Blender MCP remote installer for Windows
# Usage:
#   irm https://axcel-blade.github.io/Blender-MCP/install.ps1 | iex
# Save this file as UTF-8 without BOM. A BOM breaks irm|iex on Windows PowerShell 5.1.

$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/axcel-blade/Blender-MCP.git"
$Branch = if ($env:BLENDER_MCP_BRANCH) { $env:BLENDER_MCP_BRANCH } else { "main" }
$InstallDir = if ($env:BLENDER_MCP_HOME) {
    $env:BLENDER_MCP_HOME
} else {
    Join-Path $env:USERPROFILE "Blender-MCP"
}

Write-Host "Blender MCP installer for Windows" -ForegroundColor Cyan
Write-Host "Install dir: $InstallDir"
Write-Host "Branch:      $Branch"

function Ensure-Uv {
    if (Get-Command uv -ErrorAction SilentlyContinue) { return }
    Write-Host "Installing uv..."
    try {
        winget install --id=astral-sh.uv -e --accept-package-agreements --accept-source-agreements
    } catch {
        Write-Host "winget install failed; trying uv bootstrap script..."
        irm https://astral.sh/uv/install.ps1 | iex
    }
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" +
                (Join-Path $env:USERPROFILE ".local\bin")
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "uv not found after install. Open a new terminal and re-run."
    }
}

function Ensure-Repo {
    if (Test-Path (Join-Path $InstallDir ".git")) {
        Write-Host "Updating existing clone..."
        Set-Location $InstallDir
        $dirty = git status --porcelain --untracked-files=no
        if ($dirty) {
            $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
            Write-Host "Local changes found; stashing them as blender-mcp-installer-$stamp (restore with: git -C `"$InstallDir`" stash pop)" -ForegroundColor Yellow
            git stash push -m "blender-mcp-installer-$stamp"
            Assert-Exit "git stash"
        }
        git fetch origin
        Assert-Exit "git fetch"
        git checkout $Branch
        Assert-Exit "git checkout $Branch"
        git pull --ff-only origin $Branch
        Assert-Exit "git pull"
        return
    }
    if (Test-Path $InstallDir) {
        throw "Directory exists but is not a git repo: $InstallDir. Set BLENDER_MCP_HOME or remove it."
    }
    Write-Host "Cloning $RepoUrl ($Branch)..."
    git clone --branch $Branch --single-branch $RepoUrl $InstallDir
    Assert-Exit "git clone"
    Set-Location $InstallDir
}

function Assert-Exit([string]$What, [string]$Hint = "") {
    if ($LASTEXITCODE -ne 0) {
        $msg = "$What failed (exit code $LASTEXITCODE)."
        if ($Hint) { $msg += " $Hint" }
        throw $msg
    }
}

function Stop-RunningServers([string]$Root) {
    # A running MCP server (started by Claude, Cursor, etc.) keeps .venv\Scripts\blender-mcp.exe
    # locked, and uv sync then fails with "os error 32". Stop those processes first.
    $venv = [System.IO.Path]::GetFullPath((Join-Path $Root ".venv")).TrimEnd('\') + '\'
    $procs = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        try { $_.Path -and $_.Path.StartsWith($venv, [System.StringComparison]::OrdinalIgnoreCase) } catch { $false }
    }
    if (-not $procs) { return }
    Write-Host "Stopping running Blender MCP processes that lock the venv (your MCP client will restart them):" -ForegroundColor Yellow
    foreach ($p in $procs) {
        Write-Host "  $($p.ProcessName) (PID $($p.Id))"
        try { Stop-Process -Id $p.Id -Force -ErrorAction Stop } catch {
            Write-Host "  Could not stop PID $($p.Id): $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    Start-Sleep -Milliseconds 500
}

function Save-JsonNoBom([string]$Path, $Object) {
    $text = $Object | ConvertTo-Json -Depth 20
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $text + [Environment]::NewLine, $utf8NoBom)
}

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
    # Microsoft Store (MSIX) Claude Desktop keeps its config in a virtualized AppData
    $pkgs = Join-Path $env:LOCALAPPDATA "Packages"
    if (Test-Path $pkgs) {
        Get-ChildItem $pkgs -Directory -Filter "Claude_*" -ErrorAction SilentlyContinue | ForEach-Object {
            Set-JsonMcpServer (Join-Path $_.FullName "LocalCache\Roaming\Claude\claude_desktop_config.json") "mcpServers" $std
        }
    }
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
        if (Test-Path (Split-Path $toml)) {
            $p = $RepoRoot -replace '\\', '/'
            $text = ""
            if (Test-Path $toml) {
                $text = [System.IO.File]::ReadAllText($toml)
                Copy-Item $toml "$toml.blender-mcp.bak" -Force
            }
            # Drop any existing blender-mcp table (and sub-tables) so a reinstall updates the path.
            $text = [regex]::Replace($text, '(?ms)^\[mcp_servers\.blender-mcp(?:\.[^\]]*)?\][^\r\n]*\r?\n.*?(?=^\[(?!mcp_servers\.blender-mcp[\].])|\z)', '')
            $text = $text.TrimEnd()
            if ($text) { $text += "`n`n" }
            $text += "[mcp_servers.blender-mcp]`ncommand = `"uv`"`nargs = [`"run`", `"--directory`", `"$p`", `"blender-mcp`"]`n"
            [System.IO.File]::WriteAllText($toml, $text, (New-Object System.Text.UTF8Encoding $false))
            Write-Host "Configured $toml"
        }
    }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git is required. Install Git for Windows, then re-run."
}

Ensure-Uv
Ensure-Repo

Write-Host "Syncing project with uv..."
Stop-RunningServers $InstallDir
# An activated venv from another checkout only triggers a uv warning; ignore it.
Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
uv sync
Assert-Exit "uv sync" "If a file is still locked, close Claude/Cursor/other MCP clients and re-run."

Write-Host "Installing Blender addon..."
uv run blender-mcp install-addon
Assert-Exit "Installing the Blender addon"

Write-Host "Configuring AI clients..."
Register-McpClients $InstallDir

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "1. Open Blender -> Edit -> Preferences -> Add-ons -> enable 'Blender MCP'"
Write-Host "2. In the 3D Viewport press N -> Blender MCP -> Start"
Write-Host "3. Fully quit and reopen your AI client(s)"
Write-Host "Done. Repo: $InstallDir"
