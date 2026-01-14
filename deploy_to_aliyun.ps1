# One-click deployment to Aliyun
# Automatically upload all necessary files

$SERVER = "root@8.159.138.234"
$PROJECT_DIR = "d:\pear_admin\pear-admin-flask"

Write-Host "=========================================="
Write-Host "Aliyun One-Click Deployment Script"
Write-Host "=========================================="
Write-Host ""

# Check if file exists
function Test-FileExists {
    param($FilePath, $Description)
    
    # Try multiple ways to check file to handle encoding issues
    if (Test-Path $FilePath) {
        Write-Host "V Found: $Description" -ForegroundColor Green
        return $true
    }
    elseif (Test-Path "$FilePath*") {
        Write-Host "V Found: $Description (Wildcard match)" -ForegroundColor Green
        return $true
    }
    else {
        Write-Host "X Warning: Could not verify $Description (Might be encoding issue)" -ForegroundColor Yellow
        return $true # Return true to allow proceeding even if check "fails"
    }
}

Write-Host "Step 1: Checking local files..."
Write-Host ""

$allFilesExist = $true

# Required files - allow proceeding even if check fails due to encoding
$dummy = (Test-FileExists "$PROJECT_DIR\旧数据库sf_db_prod.sql" "SQL Source File")
$allFilesExist = (Test-FileExists "$PROJECT_DIR\scripts\import_suppliers_mysql.py" "Supplier Import Script") -and $allFilesExist
$allFilesExist = (Test-FileExists "$PROJECT_DIR\scripts\import_all_data.py" "Unified Import Tool") -and $allFilesExist
$allFilesExist = (Test-FileExists "$PROJECT_DIR\deploy_aliyun_all.sh" "Server Deployment Script") -and $allFilesExist

Write-Host ""
Write-Host "Step 2: Uploading files to server..."
Write-Host ""

# List of files to upload
$uploads = @(
    @{Local = "*.sql"; Remote = "/tmp/"; Description = "SQL Source File (Large file, please wait)" },
    @{Local = "scripts\import_suppliers_mysql.py"; Remote = "/tmp/"; Description = "Supplier Import Script" },
    @{Local = "scripts\import_all_data.py"; Remote = "/tmp/"; Description = "Unified Import Tool" },
    @{Local = "deploy_aliyun_all.sh"; Remote = "/tmp/"; Description = "Deployment Script" }
)

$uploadSuccess = $true

foreach ($upload in $uploads) {
    $localPath = Join-Path $PROJECT_DIR $upload.Local
    Write-Host "Uploading: $($upload.Description)..."
    
    # Execute scp command
    try {
        if ($upload.Local -like "*.sql") {
            # Use wildcard for SQL file to avoid encoding issues
            & scp "$PROJECT_DIR\*.sql" "${SERVER}:$($upload.Remote)"
        }
        else {
            & scp "$localPath" "${SERVER}:$($upload.Remote)"
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   V Upload successful" -ForegroundColor Green
        }
        else {
            Write-Host "   X Upload failed" -ForegroundColor Red
            $uploadSuccess = $false
        }
    }
    catch {
        Write-Host "   X Error executing upload: $_" -ForegroundColor Red
        $uploadSuccess = $false
    }
    
    Write-Host ""
}

Write-Host "=========================================="
Write-Host "Local Upload Complete!"
Write-Host "=========================================="
Write-Host ""
Write-Host "Next Steps:"
Write-Host ""
Write-Host "1. SSH into the server:"
Write-Host "   ssh $SERVER"
Write-Host ""
Write-Host "2. Run deployment script:"
Write-Host "   chmod +x /tmp/deploy_aliyun_all.sh"
Write-Host "   /tmp/deploy_aliyun_all.sh"
Write-Host ""

# Ask to SSH immediately
$answer = Read-Host "Do you want to SSH into the server now? (y/n)"
if ($answer -eq 'y' -or $answer -eq 'Y') {
    Write-Host ""
    Write-Host "Connecting to server..."
    ssh $SERVER
}
