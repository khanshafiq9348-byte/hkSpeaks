' =========================================================================
' HK Speaks Platform - Silent Auto-Start Wrapper
' =========================================================================
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
RootDir = "C:\Users\RANA COMPUTERS\Desktop\HK speaks"
WshShell.CurrentDirectory = RootDir
PythonwExe = RootDir & "\backend\.venv\Scripts\pythonw.exe"
If Not FSO.FileExists(PythonwExe) Then
    PythonwExe = RootDir & "\backend\.venv\Scripts\python.exe"
End If
If Not FSO.FileExists(PythonwExe) Then
    PythonwExe = "pythonw.exe"
End If
SupervisorScript = RootDir & "\scripts\supervisor.py"
Cmd = """" & PythonwExe & """ """ & SupervisorScript & """ --daemon"
WshShell.Run Cmd, 0, False
