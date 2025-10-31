# Script để push code lên GitHub repository
# Repository: Process-Data-chatbot-ICTU

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Push Code to GitHub" -ForegroundColor Cyan
Write-Host "Repository: Process-Data-chatbot-ICTU" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Chuyển đến thư mục project
cd "D:\Validate Data"

# 1. Kiểm tra git status
Write-Host "[1/5] Checking git status..." -ForegroundColor Yellow
git status --short
Write-Host ""

# 2. Hỏi xác nhận
Write-Host "Files sẽ được commit:" -ForegroundColor Cyan
git status --short
Write-Host ""
$confirm = Read-Host "Bạn có muốn tiếp tục? (y/n)"

if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Đã hủy." -ForegroundColor Red
    exit
}

# 3. Kiểm tra .env không được commit
Write-Host "[2/5] Checking for sensitive files..." -ForegroundColor Yellow
$envFiles = git ls-files | Where-Object { $_ -like "*.env*" }
if ($envFiles) {
    Write-Host "[WARNING] File .env được phát hiện sẽ được commit!" -ForegroundColor Red
    Write-Host "Files: $envFiles" -ForegroundColor Red
    $continue = Read-Host "Bạn có chắc chắn muốn commit .env? (y/n)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        Write-Host "Đã hủy. Vui lòng kiểm tra .gitignore." -ForegroundColor Red
        exit
    }
} else {
    Write-Host "[OK] Không có file .env sẽ được commit." -ForegroundColor Green
}

# 4. Add all files
Write-Host "[3/5] Adding files..." -ForegroundColor Yellow
git add .
Write-Host "[OK] Files đã được add." -ForegroundColor Green

# 5. Commit
Write-Host "[4/5] Committing changes..." -ForegroundColor Yellow
$commitMessage = Read-Host "Nhập commit message (hoặc Enter để dùng default)"
if ([string]::IsNullOrWhiteSpace($commitMessage)) {
    $commitMessage = "Update: Vietnamese Legal Document Metadata Extractor with OpenAI GPT-4o integration"
}

git commit -m $commitMessage

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Commit thành công!" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Commit thất bại!" -ForegroundColor Red
    exit 1
}

# 6. Push
Write-Host "[5/5] Pushing to GitHub..." -ForegroundColor Yellow
Write-Host "Remote: $(git remote get-url origin)" -ForegroundColor Cyan

# Check branch
$branch = git branch --show-current
Write-Host "Branch: $branch" -ForegroundColor Cyan
Write-Host ""

# Push
git push -u origin $branch

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] Code đã được push lên GitHub thành công!" -ForegroundColor Green
    Write-Host "Repository: https://github.com/nmhung311/Process-Data-chatbot-ICTU" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "[ERROR] Push thất bại! Kiểm tra lại:" -ForegroundColor Red
    Write-Host "  - Authentication với GitHub" -ForegroundColor Yellow
    Write-Host "  - Network connection" -ForegroundColor Yellow
    Write-Host "  - Remote branch tồn tại" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Hoàn tất!" -ForegroundColor Green

