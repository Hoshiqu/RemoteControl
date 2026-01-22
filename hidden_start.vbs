Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "C:\PowerServer\user_start.bat" & Chr(34), 0, False
Set WshShell = Nothing 