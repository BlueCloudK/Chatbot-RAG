using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;

namespace EduChatbot.RazorPages.Services
{
    public class PythonAIServiceRunner : IHostedService, IDisposable
    {
        private Process? _pythonProcess;
        private IntPtr _jobHandle = IntPtr.Zero;
        private readonly ILogger<PythonAIServiceRunner> _logger;
        private readonly IWebHostEnvironment _environment;
        private readonly IConfiguration _configuration;

        public PythonAIServiceRunner(
            ILogger<PythonAIServiceRunner> logger,
            IWebHostEnvironment environment,
            IConfiguration configuration)
        {
            _logger = logger;
            _environment = environment;
            _configuration = configuration;
        }

        public async Task StartAsync(CancellationToken cancellationToken)
        {
            var aiBaseUrl = _configuration["AiService:BaseUrl"] ?? "http://127.0.0.1:8000";

            if (await IsAiServiceAvailable(aiBaseUrl, cancellationToken))
            {
                _logger.LogInformation("Python AI Service is already running at {AiBaseUrl}.", aiBaseUrl);
                return;
            }

            var aiServiceDir = ResolveAiServiceDirectory();
            if (aiServiceDir == null)
            {
                _logger.LogError("Cannot find AiService directory. Expected it in the repository root.");
                return;
            }

            var pythonExecutable = _configuration["AiService:PythonExecutable"]
                ?? Environment.GetEnvironmentVariable("PYTHON_EXE")
                ?? "python";

            _logger.LogInformation("Starting Python AI Service from {AiServiceDir}.", aiServiceDir);

            var startInfo = new ProcessStartInfo
            {
                FileName = pythonExecutable,
                Arguments = "-B -m uvicorn main:app --host 127.0.0.1 --port 8000",
                WorkingDirectory = aiServiceDir,
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };

            startInfo.Environment["PYTHONIOENCODING"] = "utf-8";
            startInfo.Environment["PYTHONUNBUFFERED"] = "1";

            try
            {
                CreateKillOnCloseJob();
                _pythonProcess = Process.Start(startInfo);
                if (_pythonProcess == null)
                {
                    _logger.LogError("Python AI Service process could not be started.");
                    return;
                }

                AssignProcessToJob(_pythonProcess);

                _pythonProcess.OutputDataReceived += (_, e) =>
                {
                    if (!string.IsNullOrWhiteSpace(e.Data))
                        _logger.LogInformation("[AiService] {Message}", e.Data);
                };
                _pythonProcess.ErrorDataReceived += (_, e) =>
                {
                    if (!string.IsNullOrWhiteSpace(e.Data))
                        _logger.LogWarning("[AiService] {Message}", e.Data);
                };
                _pythonProcess.BeginOutputReadLine();
                _pythonProcess.BeginErrorReadLine();

                await Task.Delay(1500, cancellationToken);
                if (_pythonProcess.HasExited)
                {
                    _logger.LogError(
                        "Python AI Service exited immediately with code {ExitCode}. Check Python packages in AiService/requirements.txt.",
                        _pythonProcess.ExitCode);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(
                    ex,
                    "Cannot start Python FastAPI. Check Python is installed and dependencies are installed with: pip install -r AiService/requirements.txt");
            }
        }

        public Task StopAsync(CancellationToken cancellationToken)
        {
            _logger.LogInformation("Stopping Python AI Service...");
            if (_pythonProcess != null && !_pythonProcess.HasExited)
            {
                _pythonProcess.Kill(true);
            }

            CloseJobHandle();
            return Task.CompletedTask;
        }

        public void Dispose()
        {
            _pythonProcess?.Dispose();
            CloseJobHandle();
        }

        private void CreateKillOnCloseJob()
        {
            if (!OperatingSystem.IsWindows() || _jobHandle != IntPtr.Zero)
                return;

            _jobHandle = CreateJobObject(IntPtr.Zero, null);
            if (_jobHandle == IntPtr.Zero)
            {
                _logger.LogWarning("Could not create Windows Job Object for Python AI Service.");
                return;
            }

            var info = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION
            {
                BasicLimitInformation = new JOBOBJECT_BASIC_LIMIT_INFORMATION
                {
                    LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                }
            };

            var length = Marshal.SizeOf<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>();
            var infoPtr = Marshal.AllocHGlobal(length);
            try
            {
                Marshal.StructureToPtr(info, infoPtr, false);
                if (!SetInformationJobObject(_jobHandle, JobObjectInfoType.ExtendedLimitInformation, infoPtr, (uint)length))
                {
                    _logger.LogWarning("Could not configure Windows Job Object for Python AI Service.");
                    CloseJobHandle();
                }
            }
            finally
            {
                Marshal.FreeHGlobal(infoPtr);
            }
        }

        private void AssignProcessToJob(Process process)
        {
            if (!OperatingSystem.IsWindows() || _jobHandle == IntPtr.Zero)
                return;

            if (!AssignProcessToJobObject(_jobHandle, process.Handle))
            {
                _logger.LogWarning("Could not attach Python AI Service to the Windows Job Object.");
            }
        }

        private void CloseJobHandle()
        {
            if (_jobHandle == IntPtr.Zero)
                return;

            CloseHandle(_jobHandle);
            _jobHandle = IntPtr.Zero;
        }

        private string? ResolveAiServiceDirectory()
        {
            var candidates = new[]
            {
                Path.Combine(_environment.ContentRootPath, "..", "AiService"),
                Path.Combine(_environment.ContentRootPath, "..", "..", "AiService"),
                Path.Combine(Directory.GetCurrentDirectory(), "AiService"),
                Path.Combine(Directory.GetCurrentDirectory(), "..", "..", "AiService"),
                Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "AiService"),
                Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "AiService")
            };

            return candidates
                .Select(Path.GetFullPath)
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .FirstOrDefault(Directory.Exists);
        }

        private static async Task<bool> IsAiServiceAvailable(string baseUrl, CancellationToken cancellationToken)
        {
            try
            {
                using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };
                using var response = await client.GetAsync(baseUrl, cancellationToken);
                return response.IsSuccessStatusCode;
            }
            catch
            {
                return false;
            }
        }

        private const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;

        private enum JobObjectInfoType
        {
            ExtendedLimitInformation = 9
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct JOBOBJECT_BASIC_LIMIT_INFORMATION
        {
            public long PerProcessUserTimeLimit;
            public long PerJobUserTimeLimit;
            public uint LimitFlags;
            public UIntPtr MinimumWorkingSetSize;
            public UIntPtr MaximumWorkingSetSize;
            public uint ActiveProcessLimit;
            public UIntPtr Affinity;
            public uint PriorityClass;
            public uint SchedulingClass;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct IO_COUNTERS
        {
            public ulong ReadOperationCount;
            public ulong WriteOperationCount;
            public ulong OtherOperationCount;
            public ulong ReadTransferCount;
            public ulong WriteTransferCount;
            public ulong OtherTransferCount;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION
        {
            public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
            public IO_COUNTERS IoInfo;
            public UIntPtr ProcessMemoryLimit;
            public UIntPtr JobMemoryLimit;
            public UIntPtr PeakProcessMemoryUsed;
            public UIntPtr PeakJobMemoryUsed;
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
        private static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string? lpName);

        [DllImport("kernel32.dll")]
        private static extern bool SetInformationJobObject(
            IntPtr hJob,
            JobObjectInfoType jobObjectInfoType,
            IntPtr lpJobObjectInfo,
            uint cbJobObjectInfoLength);

        [DllImport("kernel32.dll")]
        private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);

        [DllImport("kernel32.dll")]
        private static extern bool CloseHandle(IntPtr hObject);
    }
}

