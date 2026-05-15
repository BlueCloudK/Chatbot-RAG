param(
    [int[]]$Ports = @(5099, 5101, 5102, 8000, 8010)
)

$ErrorActionPreference = "SilentlyContinue"

foreach ($port in $Ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        $process = Get-Process -Id $connection.OwningProcess
        if ($null -eq $process) {
            continue
        }

        $commandLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine
        $isEduChatbotProcess =
            $process.ProcessName -eq "EduChatbot.Web" -or
            $process.ProcessName -eq "EduChatbot.RazorPages" -or
            $process.ProcessName -eq "EduChatbot.ProductGroup" -or
            $commandLine -like "*EduChatbot.Web*" -or
            $commandLine -like "*EduChatbot.RazorPages*" -or
            $commandLine -like "*EduChatbot.ProductGroup*" -or
            $commandLine -like "*AiService*" -or
            $commandLine -like "*RblService*" -or
            ($commandLine -like "*uvicorn*" -and $commandLine -like "*main:app*")

        if ($isEduChatbotProcess) {
            Write-Host "Stopping $($process.ProcessName) PID $($process.Id) on port $port"
            Stop-Process -Id $process.Id -Force
        }
        else {
            Write-Host "Skip PID $($process.Id) on port $port because it does not look like EduChatbot"
        }
    }
}
