// white_noise_cs.cs — белый шум с таймером сна на C# (NAudio)

using System;
using System.Threading;
using NAudio.Wave;
using NAudio.Wave.SampleProviders;

class WhiteNoiseGenerator : ISampleProvider
{
    private readonly Random rand = new Random();
    public WaveFormat WaveFormat { get; } = WaveFormat.CreateIeeeFloatWaveFormat(44100, 1);
    private float volume = 0.7f;
    private string noiseType = "white";
    private float pinkState = 0f;
    private float brownState = 0f;

    public void SetVolume(float vol) => volume = Math.Max(0, Math.Min(1, vol));
    public void SetNoiseType(string type) => noiseType = type;

    public int Read(float[] buffer, int offset, int count)
    {
        for (int i = 0; i < count; i++)
        {
            float sample;
            if (noiseType == "white")
            {
                sample = (float)(rand.NextDouble() * 2 - 1);
            }
            else if (noiseType == "pink")
            {
                float w = (float)(rand.NextDouble() * 2 - 1);
                pinkState = 0.998f * pinkState + 0.05f * w;
                sample = pinkState;
            }
            else // brown
            {
                float w = (float)(rand.NextDouble() * 2 - 1);
                brownState += w * 0.02f;
                brownState = Math.Max(-1, Math.Min(1, brownState));
                sample = brownState;
            }
            buffer[offset + i] = sample * volume;
        }
        return count;
    }
}

class Program
{
    static void Main()
    {
        var waveOut = new WaveOutEvent();
        var generator = new WhiteNoiseGenerator();
        var volumeProvider = new VolumeSampleProvider(generator);

        int timerMinutes = 30;
        bool running = true;
        DateTime startTime = DateTime.Now;

        Console.WriteLine("🌊 Белый шум запущен. Таймер: " + timerMinutes + " мин.");
        Console.WriteLine("Команды: 's' - стоп, '+'/'-' - громкость, 't' - таймер, 'q' - выход");

        waveOut.Init(generator);
        waveOut.Play();

        // Отдельный поток для таймера и затухания
        Thread timerThread = new Thread(() =>
        {
            while (running)
            {
                Thread.Sleep(1000);
                var elapsed = (DateTime.Now - startTime).TotalSeconds;
                var remaining = timerMinutes * 60 - elapsed;
                if (remaining <= 0)
                {
                    running = false;
                    waveOut.Stop();
                    Console.WriteLine("\n⏹ Время вышло.");
                    break;
                }
                if (remaining < 60)
                {
                    float fade = (float)(remaining / 60.0);
                    generator.SetVolume(fade * 0.7f); // volume max 0.7
                }
            }
        });
        timerThread.IsBackground = true;
        timerThread.Start();

        while (running)
        {
            var key = Console.ReadKey(true).KeyChar;
            if (key == 's')
            {
                running = false;
                waveOut.Stop();
                Console.WriteLine("⏹ Звук остановлен.");
            }
            else if (key == '+')
            {
                float newVol = Math.Min(1f, generator.Volume + 0.05f);
                generator.SetVolume(newVol);
                Console.WriteLine("Громкость: " + (int)(newVol * 100) + "%");
            }
            else if (key == '-')
            {
                float newVol = Math.Max(0f, generator.Volume - 0.05f);
                generator.SetVolume(newVol);
                Console.WriteLine("Громкость: " + (int)(newVol * 100) + "%");
            }
            else if (key == 't')
            {
                Console.Write("Введите время в минутах (5-120): ");
                if (int.TryParse(Console.ReadLine(), out int mins))
                {
                    if (mins >= 5 && mins <= 120)
                    {
                        timerMinutes = mins;
                        startTime = DateTime.Now;
                        Console.WriteLine("Таймер установлен на " + mins + " мин.");
                    }
                }
            }
            else if (key == 'q')
            {
                running = false;
                waveOut.Stop();
                Console.WriteLine("⏹ Звук остановлен.");
            }
        }
        waveOut.Dispose();
    }
}
