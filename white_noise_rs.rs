// white_noise_rs.rs — белый шум с таймером сна на Rust (cpal)

use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use rand::distributions::{Distribution, StandardNormal};
use rand::thread_rng;
use std::sync::{Arc, Mutex};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};
use std::io::{self, Write};

struct WhiteNoise {
    running: Arc<AtomicBool>,
    volume: Arc<Mutex<f32>>,
    noise_type: Arc<Mutex<String>>,
    timer_minutes: Arc<Mutex<u32>>,
    start_time: Arc<Mutex<Instant>>,
    fade_duration: f64,
}

impl WhiteNoise {
    fn new() -> Self {
        WhiteNoise {
            running: Arc::new(AtomicBool::new(false)),
            volume: Arc::new(Mutex::new(0.7)),
            noise_type: Arc::new(Mutex::new("white".to_string())),
            timer_minutes: Arc::new(Mutex::new(30)),
            start_time: Arc::new(Mutex::new(Instant::now())),
            fade_duration: 60.0,
        }
    }

    fn start(&self) -> Result<(), Box<dyn std::error::Error>> {
        let host = cpal::default_host();
        let device = host.default_output_device().expect("No output device");
        let config = device.default_output_config().unwrap();
        let sample_rate = config.sample_rate().0;
        self.running.store(true, Ordering::SeqCst);
        *self.start_time.lock().unwrap() = Instant::now();

        let running = self.running.clone();
        let volume = self.volume.clone();
        let noise_type = self.noise_type.clone();
        let timer_minutes = self.timer_minutes.clone();
        let start_time = self.start_time.clone();
        let fade_duration = self.fade_duration;

        let stream = device.build_output_stream(
            &config.into(),
            move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
                if !running.load(Ordering::SeqCst) {
                    for sample in data.iter_mut() {
                        *sample = 0.0;
                    }
                    return;
                }
                let vol = *volume.lock().unwrap();
                let ntype = noise_type.lock().unwrap().clone();
                let timer = *timer_minutes.lock().unwrap();
                let elapsed = start_time.lock().unwrap().elapsed().as_secs_f64();
                let remaining = timer as f64 * 60.0 - elapsed;
                let mut fade = 1.0;
                if remaining <= 0.0 {
                    running.store(false, Ordering::SeqCst);
                    for sample in data.iter_mut() {
                        *sample = 0.0;
                    }
                    return;
                }
                if remaining < fade_duration {
                    fade = remaining / fade_duration;
                }
                let mut state = 0.0f32;
                for sample in data.iter_mut() {
                    let w: f32 = StandardNormal.sample(&mut thread_rng());
                    let val = match ntype.as_str() {
                        "white" => w,
                        "pink" => {
                            state = 0.998 * state + 0.05 * w;
                            state
                        }
                        "brown" => {
                            state += w * 0.02;
                            if state > 1.0 { state = 1.0; }
                            else if state < -1.0 { state = -1.0; }
                            state
                        }
                        _ => w,
                    };
                    *sample = val * vol * fade as f32;
                }
            },
            move |err| {
                eprintln!("Ошибка аудио: {}", err);
            },
        )?;
        stream.play()?;
        println!("🌊 Белый шум запущен. Таймер: {} мин.", *timer_minutes.lock().unwrap());
        println!("Команды: 's' - стоп, '+'/'-' - громкость, 't' - таймер, 'q' - выход");

        // Таймер проверки
        let running_clone = self.running.clone();
        std::thread::spawn(move || {
            while running_clone.load(Ordering::SeqCst) {
                std::thread::sleep(Duration::from_secs(1));
                let elapsed = start_time.lock().unwrap().elapsed().as_secs_f64();
                let timer = *timer_minutes.lock().unwrap();
                if elapsed >= timer as f64 * 60.0 {
                    running_clone.store(false, Ordering::SeqCst);
                    println!("\n⏹ Время вышло.");
                    break;
                }
            }
        });

        // Управление
        let mut input = String::new();
        while self.running.load(Ordering::SeqCst) {
            io::stdout().flush().unwrap();
            io::stdin().read_line(&mut input).unwrap();
            let cmd = input.trim();
            if cmd == "s" {
                self.running.store(false, Ordering::SeqCst);
                break;
            } else if cmd == "+" {
                let mut vol = self.volume.lock().unwrap();
                *vol = (*vol + 0.05).min(1.0);
                println!("Громкость: {}%", (*vol * 100.0) as i32);
            } else if cmd == "-" {
                let mut vol = self.volume.lock().unwrap();
                *vol = (*vol - 0.05).max(0.0);
                println!("Громкость: {}%", (*vol * 100.0) as i32);
            } else if cmd == "t" {
                println!("Введите время в минутах (5-120): ");
                let mut line = String::new();
                io::stdin().read_line(&mut line).unwrap();
                if let Ok(mins) = line.trim().parse::<u32>() {
                    if mins >= 5 && mins <= 120 {
                        *self.timer_minutes.lock().unwrap() = mins;
                        *self.start_time.lock().unwrap() = Instant::now();
                        println!("Таймер установлен на {} мин.", mins);
                    }
                }
            } else if cmd == "q" {
                self.running.store(false, Ordering::SeqCst);
                break;
            }
            input.clear();
        }
        drop(stream);
        println!("⏹ Звук остановлен.");
        Ok(())
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let wn = WhiteNoise::new();
    wn.start()?;
    Ok(())
}
