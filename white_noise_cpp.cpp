// white_noise_cpp.cpp — белый шум с таймером сна на C++ (PortAudio)

#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <thread>
#include <chrono>
#include <atomic>
#include <portaudio.h>

using namespace std;

class WhiteNoise {
private:
    static constexpr int SAMPLE_RATE = 44100;
    static constexpr int FRAMES_PER_BUFFER = 1024;
    atomic<bool> running;
    atomic<bool> stopRequested;
    double volume;
    int timerMinutes;
    string noiseType;
    chrono::steady_clock::time_point startTime;
    double fadeDuration = 60.0; // seconds

    random_device rd;
    mt19937 gen;
    normal_distribution<float> dist;

public:
    WhiteNoise() : running(false), stopRequested(false), volume(0.7), timerMinutes(30),
                   noiseType("white"), gen(rd()), dist(0.0, 1.0) {}

    static int paCallback(const void* inputBuffer, void* outputBuffer,
                          unsigned long framesPerBuffer,
                          const PaStreamCallbackTimeInfo* timeInfo,
                          PaStreamCallbackFlags statusFlags,
                          void* userData) {
        auto* wn = static_cast<WhiteNoise*>(userData);
        float* out = static_cast<float*>(outputBuffer);
        if (!wn->running || wn->stopRequested) {
            memset(out, 0, framesPerBuffer * sizeof(float));
            return paContinue;
        }
        wn->generateFrame(out, framesPerBuffer);
        return paContinue;
    }

    void generateFrame(float* output, unsigned long frames) {
        for (unsigned long i = 0; i < frames; ++i) {
            float sample = 0.0f;
            if (noiseType == "white") {
                sample = dist(gen);
            } else if (noiseType == "pink") {
                // упрощённый розовый шум
                static float state = 0.0f;
                sample = dist(gen);
                state = 0.998f * state + 0.05f * sample;
                sample = state;
            } else if (noiseType == "brown") {
                static float state = 0.0f;
                sample = dist(gen);
                state += sample * 0.02f;
                sample = state;
                sample = max(-1.0f, min(1.0f, sample)); // ограничение
            }
            // Объём
            sample *= volume;
            // Таймер и затухание
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - startTime).count();
            double remaining = timerMinutes * 60.0 - elapsed;
            if (remaining <= 0) {
                running = false;
                sample = 0.0f;
            } else if (remaining < fadeDuration) {
                sample *= (remaining / fadeDuration);
            }
            output[i] = sample;
        }
    }

    void start() {
        PaError err = Pa_Initialize();
        if (err != paNoError) {
            cerr << "Ошибка инициализации PortAudio" << endl;
            return;
        }
        PaStream* stream;
        err = Pa_OpenDefaultStream(&stream, 0, 1, paFloat32, SAMPLE_RATE,
                                   FRAMES_PER_BUFFER, paCallback, this);
        if (err != paNoError) {
            cerr << "Ошибка открытия потока" << endl;
            return;
        }
        running = true;
        stopRequested = false;
        startTime = chrono::steady_clock::now();
        err = Pa_StartStream(stream);
        if (err != paNoError) {
            cerr << "Ошибка запуска потока" << endl;
            return;
        }
        cout << "🌊 Белый шум запущен. Таймер: " << timerMinutes << " мин." << endl;
        cout << "Команды: 's' - стоп, '+'/'-' - громкость, 't' - таймер, 'q' - выход" << endl;
        // Консольный ввод
        char cmd;
        while (running) {
            cin >> cmd;
            if (cmd == 's') {
                running = false;
            } else if (cmd == '+') {
                volume = min(1.0, volume + 0.05);
                cout << "Громкость: " << int(volume*100) << "%" << endl;
            } else if (cmd == '-') {
                volume = max(0.0, volume - 0.05);
                cout << "Громкость: " << int(volume*100) << "%" << endl;
            } else if (cmd == 't') {
                cout << "Введите время в минутах (5-120): ";
                int mins;
                cin >> mins;
                if (mins >= 5 && mins <= 120) {
                    timerMinutes = mins;
                    cout << "Таймер установлен на " << mins << " мин." << endl;
                }
            } else if (cmd == 'q') {
                stopRequested = true;
                running = false;
            }
        }
        Pa_StopStream(stream);
        Pa_CloseStream(stream);
        Pa_Terminate();
        cout << "⏹ Звук остановлен." << endl;
    }
};

int main() {
    WhiteNoise wn;
    wn.start();
    return 0;
}
