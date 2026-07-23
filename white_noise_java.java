// white_noise_java.java — белый шум с таймером сна на Java (JavaSound)

import javax.sound.sampled.*;
import java.util.Random;
import java.util.Scanner;
import java.util.concurrent.atomic.AtomicBoolean;

public class WhiteNoise {
    private static final int SAMPLE_RATE = 44100;
    private static final int SAMPLE_SIZE = 1024;
    private static final double FADE_DURATION = 60.0; // seconds

    private volatile boolean running = false;
    private volatile boolean stopRequested = false;
    private double volume = 0.7;
    private int timerMinutes = 30;
    private String noiseType = "white";
    private SourceDataLine line;
    private Thread audioThread;
    private long startTime;
    private Random rand = new Random();

    public void start() {
        try {
            AudioFormat format = new AudioFormat(SAMPLE_RATE, 16, 1, true, true);
            DataLine.Info info = new DataLine.Info(SourceDataLine.class, format);
            line = (SourceDataLine) AudioSystem.getLine(info);
            line.open(format);
            line.start();
            running = true;
            startTime = System.currentTimeMillis();

            audioThread = new Thread(this::play);
            audioThread.start();

            System.out.println("🌊 Белый шум запущен. Таймер: " + timerMinutes + " мин.");
            System.out.println("Команды: 's' - стоп, '+'/'-' - громкость, 't' - таймер, 'q' - выход");

            Scanner scanner = new Scanner(System.in);
            while (running) {
                String cmd = scanner.nextLine().trim();
                if (cmd.equals("s")) {
                    running = false;
                } else if (cmd.equals("+")) {
                    volume = Math.min(1.0, volume + 0.05);
                    System.out.println("Громкость: " + (int)(volume * 100) + "%");
                } else if (cmd.equals("-")) {
                    volume = Math.max(0.0, volume - 0.05);
                    System.out.println("Громкость: " + (int)(volume * 100) + "%");
                } else if (cmd.equals("t")) {
                    System.out.print("Введите время в минутах (5-120): ");
                    int mins = scanner.nextInt();
                    scanner.nextLine();
                    if (mins >= 5 && mins <= 120) {
                        timerMinutes = mins;
                        System.out.println("Таймер установлен на " + mins + " мин.");
                    }
                } else if (cmd.equals("q")) {
                    stopRequested = true;
                    running = false;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            if (line != null) {
                line.drain();
                line.close();
            }
        }
        System.out.println("⏹ Звук остановлен.");
    }

    private void play() {
        byte[] buffer = new byte[SAMPLE_SIZE * 2];
        while (running && !stopRequested) {
            float[] samples = generateSamples(SAMPLE_SIZE);
            // Кодирование в 16-bit PCM
            for (int i = 0; i < samples.length; i++) {
                short val = (short) (samples[i] * 32767);
                buffer[i*2] = (byte) (val & 0xff);
                buffer[i*2+1] = (byte) ((val >> 8) & 0xff);
            }
            // Проверка таймера и затухание
            long elapsed = (System.currentTimeMillis() - startTime) / 1000;
            long remaining = timerMinutes * 60 - elapsed;
            if (remaining <= 0) {
                running = false;
                break;
            }
            if (remaining < FADE_DURATION) {
                double fade = remaining / FADE_DURATION;
                // Применяем fade к samples и перекодируем (упрощённо)
            }
            line.write(buffer, 0, buffer.length);
        }
    }

    private float[] generateSamples(int count) {
        float[] samples = new float[count];
        if (noiseType.equals("white")) {
            for (int i = 0; i < count; i++) {
                samples[i] = (float) (rand.nextGaussian() * volume);
            }
        } else if (noiseType.equals("pink")) {
            // упрощённо
            static float state = 0;
            for (int i = 0; i < count; i++) {
                float w = (float) rand.nextGaussian();
                state = 0.998f * state + 0.05f * w;
                samples[i] = state * volume;
            }
        } else if (noiseType.equals("brown")) {
            static float state = 0;
            for (int i = 0; i < count; i++) {
                float w = (float) rand.nextGaussian();
                state += w * 0.02f;
                state = Math.max(-1.0f, Math.min(1.0f, state));
                samples[i] = state * volume;
            }
        }
        return samples;
    }

    public static void main(String[] args) {
        WhiteNoise wn = new WhiteNoise();
        wn.start();
    }
}
