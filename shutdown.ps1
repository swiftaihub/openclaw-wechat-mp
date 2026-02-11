Write-Host "Stopping Docker services..."
docker compose down

Write-Host "Stopping Ollama..."
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force

Write-Host "All services stopped."