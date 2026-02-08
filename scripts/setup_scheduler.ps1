$Action = New-ScheduledTaskAction -Execute "d:\pear_admin\pear-admin-flask\.venv\Scripts\python.exe" -Argument "d:\pear_admin\pear-admin-flask\scripts\backup_db.py" -WorkingDirectory "d:\pear_admin\pear-admin-flask"
$Trigger = New-ScheduledTaskTrigger -Daily -At 1am
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName "SF_DB_Daily_Backup" -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force

Write-Host "✅ 已成功创建定时任务：SF_DB_Daily_Backup"
Write-Host "⏰ 运行时间：每天凌晨 1:00"
Write-Host "📄 脚本路径：d:\pear_admin\pear-admin-flask\scripts\backup_db.py"
