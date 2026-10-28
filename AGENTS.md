# Installing Gothic AI on Windows

You are installing Gothic AI on the user's own Windows gaming PC. A message asking to install it, or this repository's link given as an install request, authorizes the whole flow below: work through it without asking for approval between steps. Explicit narrower scope from the user ("only download", "don't launch") and higher-priority instructions win.

Talk to the user in their language (usually Russian). They are not a developer: ask for one concrete action at a time, say where to click, and keep doing independent steps while you wait.

## Boundaries

- **Human-only actions.** Steam sign-in and Steam Guard, Windows UAC prompts, the Inworld key and the ChatGPT sign-in in the setup window, the microphone toggle. Open the right window for the user and ask them to act there.
- **Secrets.** Keys and passwords are typed only by the user, into Steam, the browser or the setup console. Do not ask for them in chat, pass them through stdin or the clipboard, or read `.env`, `secrets.toml`, `chatgpt.json`, browser or Steam login data. `Test-Path` on these files is fine. Keep existing sign-ins: when `setup --check` passes, skip setup.
- **Existing state.** Do not delete or overwrite an existing Gothic AI folder, settings, saves or logs, and do not stop a running game or launcher.
- **Nothing extra.** No purchases, subscriptions or account sign-ups for the user; no changes to Defender, firewall or persistent execution policy; no compiler, Visual Studio, Vulkan SDK, CMake, Git, WSL, VM or local AI models. Besides the Gothic AI build and the Python it prepares, the only software you install is Steam, and only when it is absent (see [If Steam is missing](#if-steam-is-missing)).
- **Privacy.** Game files, saves, logs and diagnostics stay on this PC. Do not upload, publish or message them anywhere.

If your environment sandboxes network access or writes outside its workspace, request the permission these exact steps need.

## How to run the blocks

Run every block in Windows PowerShell 5.1 (`powershell.exe`) or PowerShell 7, as one command. Variables do not carry between commands, so every block whose step says "Uses the preamble" starts with this preamble; change `$repo` if you use an existing clone:

<!-- ci:preamble -->
```powershell
$repo   = Join-Path $env:LOCALAPPDATA 'GothicAI\agent\gothic-ai-windows-main'
$parent = Join-Path $env:LOCALAPPDATA 'GothicAI'
$bundle = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $repo 'bundle.json') | ConvertFrom-Json
$target = Join-Path $parent $bundle.asset.root
```

`bundle.json` is the only source of the pinned build: URL, size, SHA256, root folder, required files and source provenance.

## Main flow

### 1. Check the PC

```powershell
[Environment]::OSVersion.Version.ToString(); [Environment]::Is64BitOperatingSystem
$env:PROCESSOR_ARCHITECTURE; $env:PROCESSOR_ARCHITEW6432; $PSVersionTable.PSVersion.ToString()
Get-ChildItem -LiteralPath (Join-Path $env:LOCALAPPDATA 'GothicAI') -Directory -ErrorAction SilentlyContinue | Select-Object Name
foreach ($name in 'settings.toml', 'secrets.toml', 'chatgpt.json') {
    "$name exists: " + (Test-Path -LiteralPath (Join-Path $env:USERPROFILE ".config\gothic-ai\$name"))
}
Get-Process -Name Gothic2Notr -ErrorAction SilentlyContinue | Select-Object Id, Path
```

Done when: the version is `10.0.<build>` with build 10240 or higher, the OS is 64-bit and the architecture is `AMD64` (in either variable). Note any existing Gothic AI folders and settings: they are reused, not replaced.
Otherwise (macOS, Linux, Wine, ARM64, 32-bit, older Windows): stop and tell the user that Gothic AI runs only on 64-bit Windows 10/11 on x64, and that this request has to be given to an agent on that PC.

### 2. Get this repository locally

Git is optional and GitHub sign-in is not needed. If you are not already in a clone:

```powershell
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$work = Join-Path $env:LOCALAPPDATA 'GothicAI\agent'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$zip = Join-Path $work 'gothic-ai-windows-main.zip'
Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/ffring/gothic-ai-windows/archive/refs/heads/main.zip' -OutFile $zip -TimeoutSec 300
Expand-Archive -LiteralPath $zip -DestinationPath $work -Force
Get-ChildItem -LiteralPath (Join-Path $work 'gothic-ai-windows-main') -File | Select-Object Name
```

Done when: you have read the local `AGENTS.md` and `bundle.json` and follow them from here.

### 3. Find Steam and the game

The user owns Russian Gothic II Gold on Steam (app `39510`); take that as given.

```powershell
$steam = @((Get-ItemProperty -LiteralPath 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath,
           (Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam' -ErrorAction SilentlyContinue).InstallPath) |
    Where-Object { $_ -and (Test-Path -LiteralPath (Join-Path $_ 'steam.exe')) } | Select-Object -First 1
"steam: $steam"
$libraries = @()
if ($steam) {
    $libraries += $steam
    $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
    if (Test-Path -LiteralPath $vdf) {
        $libraries += Get-Content -Encoding UTF8 -LiteralPath $vdf |
            ForEach-Object { if ($_ -match '^\s*"path"\s+"(.+)"\s*$') { $Matches[1] -replace '\\\\', '\' } }
    }
}
$libraries = $libraries | ForEach-Object { [IO.Path]::GetFullPath($_).TrimEnd('\') } | Sort-Object -Unique
foreach ($library in $libraries) {
    $acf = Join-Path $library 'steamapps\appmanifest_39510.acf'
    if (-not (Test-Path -LiteralPath $acf)) { continue }
    $text = Get-Content -Raw -Encoding UTF8 -LiteralPath $acf
    if ($text -notmatch '"installdir"\s+"([^"]+)"') { "game: unreadable $acf (no installdir)"; continue }
    $dir = Join-Path $library "steamapps\common\$($Matches[1])"
    $flags = if ($text -match '"StateFlags"\s+"(\d+)"') { $Matches[1] }
    "game: $dir; StateFlags: $flags; Data folder: $(Test-Path -LiteralPath (Join-Path $dir 'Data'))"
}
```

Done when: a `game:` line has `StateFlags: 4` (fully installed) and `Data folder: True`.
Otherwise: no `steam:` path → [If Steam is missing](#if-steam-is-missing); Steam but no installed game, or an `unreadable` line → [If the game is missing](#if-the-game-is-missing). Ask the user for that action and continue with steps 4 and 5 meanwhile.

### 4. Download, verify and unpack the build

Uses the preamble. Downloads the pinned ZIP and its manifest into `%LOCALAPPDATA%\GothicAI\downloads`, checks size and SHA256 against `bundle.json`, checks that every archive entry lies under the expected root folder, and unpacks into a new versioned folder. An existing folder for this version is checked and reused; an incomplete one is renamed aside, never deleted.

<!-- ci:download -->
```powershell
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'  # Windows PowerShell downloads far faster without the progress bar
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12  # this process only
$downloads = Join-Path $parent 'downloads'
New-Item -ItemType Directory -Force -Path $downloads | Out-Null

function Get-Verified($item) {
    $file = Join-Path $downloads $item.name
    foreach ($attempt in 1..3) {
        if (Test-Path -LiteralPath $file) {
            if ((Get-Item -LiteralPath $file).Length -eq $item.bytes -and
                (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -eq $item.sha256) { return $file }
            Remove-Item -LiteralPath $file  # a broken earlier download of this flow
        }
        if ($attempt -lt 3) { Invoke-WebRequest -UseBasicParsing -Uri $item.url -OutFile $file -TimeoutSec 900 }
    }
    throw "$($item.name): size or SHA256 differs from bundle.json"
}

function Test-Payload([string]$dir) {
    foreach ($relative in $bundle.required) {
        if (-not (Test-Path -LiteralPath (Join-Path $dir $relative) -PathType Leaf)) { "missing $relative" }
    }
    foreach ($binary in $manifest.binaries) {
        $file = Join-Path $dir $binary.path
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { "missing $($binary.path)" }
        elseif ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $binary.sha256) { "changed $($binary.path)" }
    }
}

$zip = Get-Verified $bundle.asset
$manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath (Get-Verified $bundle.manifest) | ConvertFrom-Json
$state = 'installed'
if (Test-Path -LiteralPath $target) {
    $problems = @(Test-Payload $target)
    if ($problems.Count -eq 0) {
        $state = 'reused'
    } elseif (Get-Process -Name Gothic2Notr -ErrorAction SilentlyContinue) {
        throw "$target is incomplete ($($problems -join '; ')) and the game is running; retry after the user closes it"
    } else {
        $aside = "$($bundle.asset.root).incomplete-$(Get-Date -Format yyyyMMdd-HHmmss)"
        Rename-Item -LiteralPath $target -NewName $aside  # kept: it may hold the user's own files
        Write-Host "Renamed the incomplete copy to $aside ($($problems -join '; '))"
    }
}
if ($state -ne 'reused') {
    Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($zip)
    try { $names = @($archive.Entries | ForEach-Object { $_.FullName.Replace('\', '/') }) } finally { $archive.Dispose() }
    $outside = @($names | Where-Object { -not $_.StartsWith($bundle.asset.root + '/') -or $_ -match '(^|/)\.\.(/|$)|:' })
    if ($outside.Count -gt 0) { throw "unexpected archive entry: $($outside[0])" }
    $stage = Join-Path $parent ('.stage-' + [guid]::NewGuid().ToString('N'))
    [System.IO.Compression.ZipFile]::ExtractToDirectory($zip, $stage)
    Move-Item -LiteralPath (Join-Path $stage $bundle.asset.root) -Destination $target
    Remove-Item -LiteralPath $stage -Recurse -Force  # created by this run and now empty
    $problems = @(Test-Payload $target)
    if ($problems.Count -gt 0) { throw "unpacked build failed its checks: $($problems -join '; ')" }
}
[pscustomobject]@{ state = $state; version = $bundle.version; target = $target; sha256 = $bundle.asset.sha256 } | ConvertTo-Json
```

Done when: the block ends with JSON whose `state` is `installed` or `reused`. That means every file in `bundle.json` `required` exists and every binary matches the SHA256 in the release manifest.
Otherwise: a network error or SHA256 mismatch → retry the block once, then report it. A path-length error → set `$parent = 'C:\GothicAI'` in the preamble and repeat from this step.

### 5. Prepare Python and check the status

Uses the preamble. The launcher looks for `uv` only on `PATH`, so the bundled one goes first. Do not add `2>&1` or `$ErrorActionPreference = 'Stop'` here: Windows PowerShell 5.1 turns uv's progress on stderr into errors. Judge by exit codes.

<!-- ci:prepare -->
```powershell
$uv = Join-Path $target 'tools\uv\uv.exe'
$env:PATH = (Split-Path -Parent $uv) + ';' + $env:PATH
$env:UV_PYTHON = '3.12'
$env:UV_PYTHON_PREFERENCE = 'only-managed'
$env:PYTHONUTF8 = '1'
# Packaged Windows apps may redirect AppData. Store physical paths in venvs and settings,
# so Explorer can launch the game after the installing agent has closed.
$probe = & $uv run --no-project --python 3.12 python -c "from pathlib import Path; import json,sys; print(json.dumps({'target':str(Path(sys.argv[1]).resolve()),'python':str((Path(sys.base_prefix)/'python.exe').resolve())}))" $target
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve the physical Python and installation paths' }
$physical = $probe | ConvertFrom-Json
$target = $physical.target
$uv = Join-Path $target 'tools\uv\uv.exe'
$env:PATH = (Split-Path -Parent $uv) + ';' + $env:PATH
$env:UV_PYTHON = $physical.python
foreach ($project in 'launcher\core', 'server', 'asr-service', 'tts-service') {
    $projectPath = Join-Path $target $project
    $venv = Join-Path $projectPath '.venv'
    $cfg = Join-Path $venv 'pyvenv.cfg'
    if (Test-Path -LiteralPath $cfg) {
        $oldHome = Get-Content -LiteralPath $cfg | Where-Object { $_ -match '^home\s*=' } | Select-Object -First 1
        $oldHome = if ($oldHome) { ($oldHome -replace '^home\s*=\s*', '').Trim() } else { '' }
        if ($oldHome -ne (Split-Path -Parent $physical.python)) {
            Rename-Item -LiteralPath $venv -NewName ('.venv.before-path-fix-' + (Get-Date -Format yyyyMMdd-HHmmss))
        }
    }
    & $uv sync --locked --python $physical.python --project $projectPath
    if ($LASTEXITCODE -ne 0) { throw "uv sync failed for $project (exit code $LASTEXITCODE)" }
}
& $uv run --locked --project (Join-Path $target 'launcher\core') gothic-launcher config set paths.repo $target
if ($LASTEXITCODE -ne 0) { throw 'Cannot save the physical repository path' }
# settings.toml is not a secret file. Resolve an already selected game without changing its contents.
$gamePath = & $uv run --locked --project (Join-Path $target 'launcher\core') python -c "from pathlib import Path; import tomllib; p=Path.home()/'.config/gothic-ai/settings.toml'; d=tomllib.loads(p.read_text(encoding='utf-8')) if p.is_file() else {}; v=d.get('game',{}).get('dir'); print(str(Path(v).resolve()) if v else '')"
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect the selected game path' }
if ($gamePath -and (Test-Path -LiteralPath (Join-Path $gamePath 'Data'))) {
    & $uv run --locked --project (Join-Path $target 'launcher\core') gothic-launcher config set game.dir $gamePath
    if ($LASTEXITCODE -ne 0) { throw 'Cannot save the physical game path' }
}
& $uv run --locked --project (Join-Path $target 'launcher\core') gothic-launcher setup --check
"setup --check exit code: $LASTEXITCODE"
```

uv downloads Python 3.12 and the locked libraries once; repeats are fast. `setup --check` asks nothing: it prints in Russian what is still missing.

| Exit code | Meaning | Next |
|---|---|---|
| 0 | Ready: game folder, Inworld key and ChatGPT sign-in are set | Step 7 |
| 2 | The game or the user's setup is missing (expected on a fresh PC) | Step 6 once the game is installed |
| 1 or other | Failure | Read the printed reason; see [If something fails](#if-something-fails) |

### 5a. Preserve an existing modded game

If the Steam Data folder contains extra VDF archives (for example AB_* or Union.vdf), prepare the separate base-game profile before setup. Run `Prepare-GothicAI-Game.cmd "<game folder found in step 3>"` from the bundle with the exact discovered path. This uses hard links to the original base archives and directory junctions; it never copies game data or replaces mods. It sets only game.dir through the launcher. Existing matching profiles are reused. A compressed or missing original base archive is reported explicitly.

The base profile is for Gothic AI. Keep the user's original modded installation and saves. If setup --check already passes, preserve credentials and do not ask the user to sign in again.

### 6. Let the user finish setup in their own console

Only when step 5 returned 2 and step 3 found the installed game. Uses the preamble. This opens the bundled setup in a new visible console window that belongs to the user:

```powershell
Start-Process -FilePath $env:ComSpec -ArgumentList '/k', 'Setup-GothicAI.cmd -SkipBuild' -WorkingDirectory $target
```

Tell the user: in the new black window, answer its questions, paste the Inworld key when asked (the characters stay invisible) and press Enter, then sign in to ChatGPT in the browser that opens. The window prints «Готово» at the end and can then be closed. A user without an Inworld key gets one from Inworld (inworld.ai) themselves; accounts and plans are their decision. Setup finds the game in Steam by itself; if it shows a folder picker, the user picks the Gothic II folder from step 3 (the one with `Data`). If the window does not appear on the user's screen, ask them to open `%LOCALAPPDATA%\GothicAI\GothicAI-windows-x64-r6-9cadf76-winfix1` in Explorer and double-click `Setup-GothicAI.cmd`.

Done when: the user says setup finished and step 5's `setup --check` now returns 0.

### 7. Add a shortcut and launch

Uses the preamble. Resolve the physical installation and cache again, because variables do not carry between commands. Preserve an existing shortcut as a backup, then point the desktop shortcut at a local wrapper. The wrapper contains only filesystem paths, never credentials, and makes both the agent and Explorer use the same imported base cache.

```powershell
$uv = Join-Path $target 'tools\uv\uv.exe'
$env:PYTHONUTF8 = '1'
$paths = & $uv run --no-project --python 3.12 python -c "from pathlib import Path; import json,os,sys; print(json.dumps({'target':str(Path(sys.argv[1]).resolve()),'cache':str((Path(os.environ['LOCALAPPDATA'])/'gothic-ai'/'base').resolve())}))" $target
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve desktop paths' }
$paths = $paths | ConvertFrom-Json
$target = $paths.target
$start = Join-Path $target 'Start-GothicAI.cmd'
$wrapper = Join-Path $target 'Start-Desktop-GothicAI.ps1'
if (-not (Test-Path -LiteralPath $wrapper)) {
    $lines = @(
        ('$env:OPENGOTHIC_BASE_CACHE = ' + "'" + $paths.cache.Replace("'", "''") + "'"),
        ('& ' + "'" + $start.Replace("'", "''") + "' @args"),
        'exit $LASTEXITCODE'
    )
    [IO.File]::WriteAllLines($wrapper, $lines, (New-Object Text.UTF8Encoding $true))
}
$shortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Gothic AI.lnk'
if (Test-Path -LiteralPath $shortcut) {
    $backups = Join-Path $parent 'shortcut-backups'
    New-Item -ItemType Directory -Path $backups -Force | Out-Null
    Copy-Item -LiteralPath $shortcut -Destination (Join-Path $backups ('Gothic AI-' + (Get-Date -Format yyyyMMdd-HHmmss) + '.lnk'))
}
$link = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcut)
$link.TargetPath = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$link.Arguments = '-NoLogo -NoProfile -ExecutionPolicy Bypass -File "' + $wrapper + '"'
$link.WorkingDirectory = $target
$link.IconLocation = (Join-Path $target 'OpenGothic\build\opengothic\Gothic2Notr.exe') + ',0'
$link.Save()
(New-Object -ComObject Shell.Application).ShellExecute($shortcut, '', '', 'open', 1)
```

Tell the user: keep the black window open while playing; closing the game stops everything; to talk to an NPC, hold **T**, speak, then release T and the NPC answers with a voice; the first start takes longer while the game prepares its data; Codex and the browser are no longer needed for playing.

After about a minute:

```powershell
Get-Process -Name Gothic2Notr -ErrorAction SilentlyContinue | Select-Object Id, StartTime, MainWindowTitle
Get-ChildItem -LiteralPath (Join-Path $env:LOCALAPPDATA 'GothicAI\Logs') -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name | Select-Object -Last 1 | Get-ChildItem -File | Select-Object Name, Length
```

Done when: a `Gothic2Notr` process runs. Unless you can see the screen yourself, ask the user one question: is the game on screen, and when they hold T, speak and release T, do they hear the NPC answer with a voice?

### 8. Report

Tell the user exactly one status, with the install folder and version:

- **Ready to play** («Готово к игре») — `setup --check` returned 0 and the game process started. Say "picture and voice confirmed" only if the user confirmed them or you observed them.
- **Files prepared** («Файлы подготовлены») — step 4 is done and `setup --check` returns 2. List each pending human action from steps 3 and 6.
- **Failed** («Не получилось») — what failed, the exact step, and the next action.

Do not describe gameplay, microphone or voice as verified by CI: the build was compiled and unit-tested on GitHub Actions only. Version 0.1.1 has been verified on one real Windows 11 x64 PC, including a user-confirmed voiced NPC reply. On another PC, verify the picture and voice again; CI alone does not prove gameplay.

## If Steam is missing

Install the official Steam client, only when step 3 found no Steam:

```powershell
winget install --id Valve.Steam --exact --source winget
```

The user may need to approve a Windows UAC prompt. If winget is missing or fails, ask the user to install Steam from the official site `store.steampowered.com`. Then continue with [If the game is missing](#if-the-game-is-missing).

## If the game is missing

Start Steam for the user: `Start-Process -FilePath '<steam path from step 3>\steam.exe'`. Ask them to sign in (with Steam Guard if asked), open the Library, install Gothic II: Gold Edition and wait for the download to finish. Re-run step 3 until it reports `StateFlags: 4`. The game files stay where Steam puts them; never copy or upload them.

## Microphone

Read-only check; `Deny` means voice input is blocked:

```powershell
$consent = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone'
foreach ($key in $consent, (Join-Path $consent 'NonPackaged')) {
    "$key : $((Get-ItemProperty -LiteralPath $key -Name Value -ErrorAction SilentlyContinue).Value)"
}
```

If either says `Deny`, open the settings page with `Start-Process 'ms-settings:privacy-microphone'` and ask the user to allow microphone access, including for desktop apps.

Also run `Check-Microphone.cmd` from the bundle to inspect endpoint mute and volume. Windows permission `Allow` does not imply the microphone is unmuted. The check is read-only and does not record audio. If muted, ask the user to unmute the default input in Windows Sound > Recording > Levels or with the laptop microphone key. Do not silently change recording/privacy settings.

## If something fails

- `setup --check` or the setup window explains what is missing in Russian: relay it to the user and fix that item.
- The game window does not appear, the game closes, or NPCs are silent: open `Diagnostics-GothicAI.cmd` from the install folder in a visible window (`Start-Process -FilePath (Join-Path $target 'Diagnostics-GothicAI.cmd') -WorkingDirectory $target`). It takes about a minute and writes `%LOCALAPPDATA%\GothicAI\diagnostics-<time>.txt` with masked keys. Read the newest one locally, plus the newest session folder in `%LOCALAPPDATA%\GothicAI\Logs` when needed. Quote only the lines that matter to the user; logs may contain their speech.
- Missing `MSVCP140.dll` or `VCRUNTIME140.dll`: the user can install the Microsoft Visual C++ Redistributable x64 from `https://aka.ms/vs/17/release/vc_redist.x64.exe`.
- An error about `vulkan-1.dll` or a black screen: the graphics driver needs an update from the GPU vendor's site.
- To change the Inworld key later, the user runs `Setup-GothicAI.cmd -ChangeKey` in their own console, as in step 6.
