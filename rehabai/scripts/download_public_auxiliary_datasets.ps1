param(
    [string]$Destination = 'D:\PhucHoiChucNangTay\RehabAI_Datasets_FULL_VERIFIED\04_Public_Auxiliary_2026'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$records = @(
    @{ Id = 4610859; Slug = 'intellirehabds'; Include = @('SkeletonData.zip', 'readme.txt'); IntendedUse = 'skeleton_ssl_and_correctness_auxiliary' },
    # Subjects 05/06/07 are the stroke cohort identified by the official record.
    # The other ARMin files are able-bodied controls and are excluded here to
    # keep this acquisition focused and storage-efficient.
    @{ Id = 14800465; Slug = 'armin5_fusion'; Include = @('subject_05.mat', 'subject_06.mat', 'subject_07.mat'); IntendedUse = 'stroke_kinematic_representation_only' },
    @{ Id = 7587404; Slug = 'stroke_functional_reaching'; Include = @('*'); IntendedUse = 'stroke_reaching_kinematic_representation_only' },
    @{ Id = 51270; Slug = 'stroke_robot_aided_kinematics'; Include = @('*'); IntendedUse = 'stroke_robot_kinematic_representation_only' },
    @{ Id = 19956651; Slug = 'upper_limb_perturbation_2026'; Include = @('*'); IntendedUse = 'upper_limb_perturbation_auxiliary_only' }
)

New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$manifest = [System.Collections.Generic.List[object]]::new()

foreach ($record in $records) {
    $recordDir = Join-Path $Destination $record.Slug
    $rawDir = Join-Path $recordDir 'raw'
    New-Item -ItemType Directory -Force -Path $rawDir | Out-Null

    $metadata = Invoke-RestMethod -Uri "https://zenodo.org/api/records/$($record.Id)"
    if ($metadata.metadata.access_right -ne 'open') {
        throw "Record $($record.Id) is no longer openly accessible"
    }
    $metadata | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $recordDir 'zenodo_record.json') -Encoding UTF8

    foreach ($file in $metadata.files) {
        $included = $record.Include -contains '*' -or $record.Include -contains $file.key
        if (-not $included) { continue }

        $target = Join-Path $rawDir $file.key
        $expectedMd5 = ([string]$file.checksum) -replace '^md5:', ''
        $downloadNeeded = $true
        if (Test-Path -LiteralPath $target) {
            $existingMd5 = (Get-FileHash -LiteralPath $target -Algorithm MD5).Hash.ToLowerInvariant()
            $downloadNeeded = $existingMd5 -ne $expectedMd5.ToLowerInvariant()
        }
        if ($downloadNeeded) {
            Write-Output "Downloading $($record.Slug)/$($file.key)"
            & curl.exe --fail --location --retry 5 --retry-delay 2 --continue-at - --output $target $file.links.self
            if ($LASTEXITCODE -ne 0) { throw "Download failed: $($file.links.self)" }
        } else {
            Write-Output "Verified existing $($record.Slug)/$($file.key)"
        }

        $actualMd5 = (Get-FileHash -LiteralPath $target -Algorithm MD5).Hash.ToLowerInvariant()
        if ($actualMd5 -ne $expectedMd5.ToLowerInvariant()) {
            throw "MD5 mismatch: $target expected=$expectedMd5 actual=$actualMd5"
        }
        $sha256 = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
        $manifest.Add([pscustomobject]@{
            dataset = $record.Slug
            zenodo_record_id = $record.Id
            doi = $metadata.doi
            title = $metadata.metadata.title
            access_right = $metadata.metadata.access_right
            license = $metadata.metadata.license.id
            intended_use = $record.IntendedUse
            source_label_mapping_allowed = $false
            filename = $file.key
            bytes = [int64]$file.size
            source_url = $file.links.self
            expected_md5 = $expectedMd5.ToLowerInvariant()
            verified_md5 = $actualMd5
            sha256 = $sha256
            downloaded_utc = [DateTime]::UtcNow.ToString('o')
            local_path = $target
        })
    }
}

$manifestPath = Join-Path $Destination 'download_manifest.csv'
$manifest | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding UTF8

# Extract only the compact skeleton archive. Depth archives are intentionally
# excluded because they add ~38 GB without adding joints unavailable here.
$skeletonZip = Join-Path $Destination 'intellirehabds\raw\SkeletonData.zip'
$skeletonOut = Join-Path $Destination 'intellirehabds\extracted\SkeletonData'
if (-not (Test-Path -LiteralPath $skeletonOut)) {
    New-Item -ItemType Directory -Force -Path $skeletonOut | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($skeletonZip)
    try {
        $root = [System.IO.Path]::GetFullPath($skeletonOut + [System.IO.Path]::DirectorySeparatorChar)
        foreach ($entry in $archive.Entries) {
            $candidate = [System.IO.Path]::GetFullPath((Join-Path $skeletonOut $entry.FullName))
            if (-not $candidate.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "Unsafe ZIP entry: $($entry.FullName)"
            }
        }
    } finally {
        $archive.Dispose()
    }
    Expand-Archive -LiteralPath $skeletonZip -DestinationPath $skeletonOut
}

$summary = [ordered]@{
    completed_utc = [DateTime]::UtcNow.ToString('o')
    dataset_count = ($manifest.dataset | Sort-Object -Unique).Count
    file_count = $manifest.Count
    downloaded_bytes = ($manifest | Measure-Object bytes -Sum).Sum
    all_source_hashes_verified = $true
    source_labels_mapped_to_product_registry = $false
    training_started = $false
    note = 'Auxiliary research data only; audit/adaptation is required before training.'
}
$summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Destination 'DOWNLOAD_COMPLETE.json') -Encoding UTF8
$summary | ConvertTo-Json

& python (Join-Path $PSScriptRoot 'audit_public_auxiliary_datasets.py')
if ($LASTEXITCODE -ne 0) { throw "Public auxiliary structural audit failed ($LASTEXITCODE)" }
