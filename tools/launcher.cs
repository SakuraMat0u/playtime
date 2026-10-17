using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

static class Program
{
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int MessageBoxW(IntPtr hWnd, string text, string caption, uint type);

    private const uint MB_ICONERROR = 0x10;
    private const int ERROR_CANCELLED = 1223;

    [STAThread]
    private static void Main(string[] args)
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string target = Path.Combine(Path.Combine(root, "Playtime"), "Playtime.exe");
        string dataDir = Path.Combine(root, "userconfig");

        if (!File.Exists(target))
        {
            MessageBoxW(IntPtr.Zero,
                "找不到 Playtime 目录下的程序。\n\n请把启动器与 Playtime 文件夹放在同一目录后再运行。",
                "Playtime", MB_ICONERROR);
            return;
        }

        ProcessStartInfo psi = new ProcessStartInfo(target);
        psi.WorkingDirectory = root;
        psi.Arguments = BuildArguments(dataDir, args);

#if ADMIN
        // 提权必须经过外壳；普通启动走 CreateProcess，避免未签名 exe 的“安全警告”
        psi.UseShellExecute = true;
        psi.Verb = "runas";
#else
        psi.UseShellExecute = false;
#endif

        try
        {
            Process.Start(psi);
        }
        catch (Win32Exception ex)
        {
            if (ex.NativeErrorCode != ERROR_CANCELLED)
            {
                MessageBoxW(IntPtr.Zero, "启动失败：" + ex.Message, "Playtime", MB_ICONERROR);
            }
        }
        catch (Exception ex)
        {
            MessageBoxW(IntPtr.Zero, "启动失败：" + ex.Message, "Playtime", MB_ICONERROR);
        }
    }

    private static string BuildArguments(string dataDir, string[] args)
    {
        StringBuilder sb = new StringBuilder();
        sb.Append("--data-dir \"").Append(dataDir).Append('"');
        foreach (string a in args)
        {
            sb.Append(" \"").Append(a.Replace("\"", "\\\"")).Append('"');
        }
        return sb.ToString();
    }
}