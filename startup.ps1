Write-Host "Starting Ollama..."
Start-Process ollama -ArgumentList "serve"

Start-Sleep -Seconds 3

Write-Host "Starting Docker services..."
docker compose up -d --build

Write-Host "All services started."