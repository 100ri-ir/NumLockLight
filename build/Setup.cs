using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: AssemblyTitle("NumLock Light Setup")]
[assembly: AssemblyProduct("NumLock Light")]
[assembly: AssemblyVersion("1.1.0.0")]

class SetupProgram
{
    [STAThread]
    static int Main(string[] args)
    {
        Application.EnableVisualStyles();
        bool silent = args.Length > 0 &&
            (args[0] == "/S" || args[0] == "/silent" || args[0] == "/VERYSILENT");

        if (!silent)
        {
            var r = MessageBox.Show(
                "Install NumLock Light v1.1.0 on your computer?\n\nآیا مایل به نصب برنامه نام‌لاک لایت نسخه 1.1.0 هستید؟",
                "NumLock Light 1.1.0 Setup",
                MessageBoxButtons.YesNo, MessageBoxIcon.Question);
            if (r != DialogResult.Yes) return 0;
        }

        try
        {
            foreach (var p in Process.GetProcessesByName("NumLockLight"))
            {
                try { p.Kill(); p.WaitForExit(3000); } catch { }
            }

            string target = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Programs", "NumLockLight");

            if (Directory.Exists(target))
            {
                try { Directory.Delete(target, true); } catch { }
            }
            Directory.CreateDirectory(target);

            string tempZip = Path.Combine(Path.GetTempPath(),
                "nll_" + Guid.NewGuid().ToString("N") + ".zip");
            using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream("Payload.zip"))
            using (FileStream fs = File.Create(tempZip))
            {
                s.CopyTo(fs);
            }
            ZipFile.ExtractToDirectory(tempZip, target);
            try { File.Delete(tempZip); } catch { }

            string exePath = Path.Combine(target, "NumLockLight.exe");
            CreateShortcut(Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.Programs),
                "NumLock Light.lnk"), exePath, target);
            CreateShortcut(Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                "NumLock Light.lnk"), exePath, target);

            using (RegistryKey k = Registry.CurrentUser.OpenSubKey(
                @"Software\Microsoft\Windows\CurrentVersion\Run", true))
            {
                if (k != null) k.SetValue("NumLockLight100ri", "\"" + exePath + "\"");
            }

            Process.Start(new ProcessStartInfo(exePath) { WorkingDirectory = target });

            if (!silent)
            {
                MessageBox.Show(
                    "NumLock Light v1.1.0 has been installed and launched!\n\nنصب با موفقیت انجام شد و برنامه در نوار وظیفه اجرا گردید.",
                    "NumLock Light Setup",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            return 0;
        }
        catch (Exception ex)
        {
            if (!silent)
                MessageBox.Show("Setup failed:\n" + ex.Message,
                    "NumLock Light Setup Error",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    static void CreateShortcut(string lnk, string targetPath, string workDir)
    {
        try
        {
            Type t = Type.GetTypeFromProgID("WScript.Shell");
            object shell = Activator.CreateInstance(t);
            object sc = t.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, shell, new object[] { lnk });
            Type st = sc.GetType();
            st.InvokeMember("TargetPath", BindingFlags.SetProperty, null, sc, new object[] { targetPath });
            st.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, sc, new object[] { workDir });
            st.InvokeMember("Save", BindingFlags.InvokeMethod, null, sc, null);
        }
        catch { }
    }
}
