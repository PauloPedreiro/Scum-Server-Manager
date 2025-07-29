@echo off
echo Limpando banco de jogadores...
del /Q "src\\data\\players\\players.json"
del /Q "src\\data\\players\\lastOnline.json"
echo Banco limpo! (O backend irá recriar os arquivos automaticamente)
pause