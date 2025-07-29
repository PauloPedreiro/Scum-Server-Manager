@echo off
echo 🧹 Limpando arquivos JSON do bot...
echo.

cd /d "%~dp0"

echo {} > src\data\bot\linked_users.json
echo {} > src\data\bot\vehicle_registrations.json
echo {} > src\data\bot\pending_requests.json
echo {} > src\data\bot\cooldowns.json
echo {} > src\data\bot\processed_commands.json
echo {} > src\data\bot\vehicle_mount_registrations.json
echo {} > src\data\bot\pending_mount_requests.json
echo {} > src\data\bot\vehicle_mount_completed.json

echo ✅ Arquivos JSON limpos!
echo.
echo 📝 Arquivos limpos:
echo    - linked_users.json
echo    - vehicle_registrations.json
echo    - pending_requests.json
echo    - cooldowns.json
echo    - processed_commands.json
echo    - vehicle_mount_registrations.json
echo    - pending_mount_requests.json
echo    - vehicle_mount_completed.json
echo.
echo 🎯 Bot pronto para novos testes!
pause 