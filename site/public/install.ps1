# Blender MCP remote installer (Windows)
# Usage:
#   irm https://axcel-blade.github.io/Blender-MCP/install.ps1 | iex

$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/axcel-blade/Blender-MCP.git"
$Branch = if ($env:BLENDER_MCP_BRANCH) { $env:BLENDER_MCP_BRANCH } else { "develop" }
$InstallDir = if ($env:BLENDER_MCP_HOME) {
    $env:BLENDER_MCP_HOME
} else {
    Join-Path $env:USERPROFILE "Blender-MCP"
}

Write-Host "Blender MCP installer (Windows)" -ForegroundColor Cyan
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
        git fetch origin
        git checkout $Branch
        git pull --ff-only origin $Branch
        return
    }
    if (Test-Path $InstallDir) {
        throw "Directory exists but is not a git repo: $InstallDir. Set BLENDER_MCP_HOME or remove it."
    }
    Write-Host "Cloning $RepoUrl ($Branch)..."
    git clone --branch $Branch --single-branch $RepoUrl $InstallDir
    Set-Location $InstallDir
}

function Add-McpServer([string]$ConfigPath, [string]$RepoRoot) {
    if (-not (Test-Path $ConfigPath)) { return $false }
    $backup = "$ConfigPath.blender-mcp.bak"
    Copy-Item $ConfigPath $backup -Force
    $json = Get-Content $ConfigPath -Raw | ConvertFrom-Json
    if (-not $json.mcpServers) {
        $json | Add-Member -NotePropertyName mcpServers -NotePropertyValue (@{}) -Force
    }
    $entry = [pscustomobject]@{
        command = "uv"
        args    = @("run", "--directory", "$RepoRoot", "blender-mcp")
    }
    $json.mcpServers | Add-Member -NotePropertyName blender -NotePropertyValue $entry -Force
    $json | ConvertTo-Json -Depth 20 | Set-Content $ConfigPath -Encoding UTF8
    Write-Host "Updated $ConfigPath (backup: $backup)"
    return $true
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git is required. Install Git for Windows, then re-run."
}

Ensure-Uv
Ensure-Repo

Write-Host "Syncing project with uv..."
uv sync

Write-Host "Installing Blender addon..."
uv run blender-mcp install-addon

$cursor = Join-Path $env:USERPROFILE ".cursor\mcp.json"
$claude = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
[void](Add-McpServer $cursor $InstallDir)
[void](Add-McpServer $claude $InstallDir)

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "1. Open Blender → Edit → Preferences → Add-ons → enable 'Blender MCP'"
Write-Host "2. In the 3D Viewport press N → AI / MCP → Start"
Write-Host "3. Fully quit and reopen your MCP client (Cursor / Claude Desktop)"
Write-Host "Done. Repo: $InstallDir"
