# white_noise_python.py — белый шум с таймером сна на Python

import numpy as np
import pyaudio
import threading
import time
import json
import os
import sys
import signal

class WhiteNoise:
    def __init__(self):
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 1
        self.RATE = 44100
        self.CHUNK = 1024
        self.volume = 0.7
        self.noise_type = 'white'  # 'white', 'pink', 'brown'
        self.timer_minutes = 30
        self.running = False
        self.stream = None
        self.audio = pyaudio.PyAudio()
        self.lock = threading.Lock()
        self.start_time = 0
        self.elapsed = 0
        self.fade_out_duration = 60  # секунд
        self.config_file = 'whitenoise_config.json'
        self.load_config()

    def generate_noise(self, samples):
        if self.noise_type == 'white':
            noise = np.random.normal(0, 1, samples)
        elif self.noise_type == 'pink':
            # Розовый шум через фильтр
            noise = self._pink_noise(samples)
        elif self.noise_type == 'brown':
            # Коричневый шум (интегрированный белый)
            noise = self._brown_noise(samples)
        else:
            noise = np.random.normal(0, 1, samples)
        return noise * self.volume

    def _pink_noise(self, samples):
        # Простой фильтр для розового шума
        b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
        a = [1, -2.494956002, 2.017265875, -0.522189400]
        state = np.zeros(len(b) - 1)
        noise = np.random.normal(0, 1, samples)
        filtered = np.zeros(samples)
        for i in range(samples):
            filtered[i] = b[0] * noise[i] + state[0]
            for j in range(1, len(b)):
                state[j-1] = b[j] * noise[i] - a[j] * filtered[i] + (state[j] if j < len(state) else 0)
        return filtered

    def _brown_noise(self, samples):
        # Интеграция белого шума
        noise = np.random.normal(0, 1, samples)
        brown = np.cumsum(noise)
        # Нормализация
        brown = brown / np.max(np.abs(brown))
        return brown

    def audio_callback(self, in_data, frame_count, time_info, status):
        if not self.running:
            return (np.zeros(frame_count, dtype=np.float32).tobytes(), pyaudio.paContinue)
        with self.lock:
            samples = frame_count
            data = self.generate_noise(samples)
            # Проверка таймера
            if self.timer_minutes > 0:
                elapsed = time.time() - self.start_time
                remaining = self.timer_minutes * 60 - elapsed
                if remaining <= 0:
                    self.running = False
                    return (np.zeros(samples, dtype=np.float32).tobytes(), pyaudio.paComplete)
                # Затухание за 60 секунд до конца
                if remaining < self.fade_out_duration:
                    fade_factor = remaining / self.fade_out_duration
                    data *= fade_factor
            return (data.astype(np.float32).tobytes(), pyaudio.paContinue)

    def start(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.stream = self.audio.open(format=self.FORMAT,
                                      channels=self.CHANNELS,
                                      rate=self.RATE,
                                      output=True,
                                      frames_per_buffer=self.CHUNK,
                                      stream_callback=self.audio_callback)
        self.running = True
        self.start_time = time.time()
        self.stream.start_stream()
        print(f"🌊 Белый шум запущен. Таймер: {self.timer_minutes} мин.")
        print("Команды: 's' - стоп, '+'/'-' - громкость, 't' - таймер, 'q' - выход")

    def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        print("⏹ Звук остановлен.")

    def set_volume(self, delta):
        self.volume = max(0.0, min(1.0, self.volume + delta))
        print(f"Громкость: {int(self.volume * 100)}%")

    def set_timer(self, minutes):
        self.timer_minutes = max(1, min(120, minutes))
        print(f"Таймер установлен на {self.timer_minutes} мин.")

    def set_noise_type(self, ntype):
        if ntype in ['white', 'pink', 'brown']:
            self.noise_type = ntype
            print(f"Тип шума: {ntype.capitalize()}")

    def save_config(self):
        config = {
            'volume': self.volume,
            'noise_type': self.noise_type,
            'timer_minutes': self.timer_minutes
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f)

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.volume = config.get('volume', 0.7)
                self.noise_type = config.get('noise_type', 'white')
                self.timer_minutes = config.get('timer_minutes', 30)

    def run_cli(self):
        print("🌊 WhiteNoise Sleep Timer (Python)")
        print("Тип: {0}, Громкость: {1}%, Таймер: {2} мин".format(
            self.noise_type, int(self.volume*100), self.timer_minutes))
        self.start()
        try:
            while True:
                cmd = sys.stdin.read(1)
                if not cmd:
                    break
                if cmd == 's':
                    self.stop()
                elif cmd == '+':
                    self.set_volume(0.05)
                elif cmd == '-':
                    self.set_volume(-0.05)
                elif cmd == 't':
                    print("Введите время в минутах (5-120): ", end='')
                    sys.stdout.flush()
                    try:
                        mins = int(input())
                        self.set_timer(mins)
                    except:
                        pass
                elif cmd == 'q':
                    self.stop()
                    break
                elif cmd == 'w':
                    self.set_noise_type('white')
                elif cmd == 'p':
                    self.set_noise_type('pink')
                elif cmd == 'b':
                    self.set_noise_type('brown')
        except KeyboardInterrupt:
            pass
        self.save_config()
        self.audio.terminate()

if __name__ == "__main__":
    wn = WhiteNoise()
    wn.run_cli()
