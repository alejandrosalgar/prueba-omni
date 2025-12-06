# Script simple para subir CSV
$API_URL = "https://e9yczp0zwb.execute-api.us-east-1.amazonaws.com/v1/"
$csvPath = "emails.csv"

if (-not (Test-Path $csvPath)) {
    Write-Host "ERROR: No se encontró emails.csv" -ForegroundColor Red
    exit
}

$csvPath = (Resolve-Path $csvPath).Path
$boundary = [System.Guid]::NewGuid().ToString()
$fileBytes = [System.IO.File]::ReadAllBytes($csvPath)
$fileName = [System.IO.Path]::GetFileName($csvPath)
$bodyLines = "--$boundary`r`nContent-Disposition: form-data; name=`"file`"; filename=`"$fileName`"`r`nContent-Type: text/csv`r`n`r`n" + [System.Text.Encoding]::UTF8.GetString($fileBytes) + "`r`n--$boundary--"
$bodyBytes = [System.Text.Encoding]::GetEncoding("iso-8859-1").GetBytes($bodyLines)

$response = Invoke-WebRequest -Uri "${API_URL}upload" -Method Post -Body $bodyBytes -ContentType "multipart/form-data; boundary=$boundary" -UseBasicParsing
$result = $response.Content | ConvertFrom-Json
Write-Host "Batch ID: $($result.batchId)" -ForegroundColor Green
$result.batchId

