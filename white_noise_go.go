// white_noise_go.go — белый шум с таймером сна на Go (PortAudio)

package main

import (
	"bufio"
	"fmt"
	"math"
	"math/rand"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/gordonklaus/portaudio"
)

type WhiteNoise struct {
	stream       *portaudio.Stream
	buffer       []float32
	volume       float32
	noiseType    string
	timerMinutes int
	running      bool
	startTime    time.Time
	fadeDuration float64
}

func NewWhiteNoise() *WhiteNoise {
	return &WhiteNoise{
		volume:       0.7,
		noiseType:    "white",
		timerMinutes: 30,
		fadeDuration: 60.0,
	}
}

func (wn *WhiteNoise) generateSamples(samples int) []float32 {
	data := make([]float32, samples)
	var state float32
	for i := 0; i < samples; i++ {
		var sample float32
		switch wn.noiseType {
		case "white":
			sample = float32(rand.NormFloat64())
		case "pink":
			w := float32(rand.NormFloat64())
			state = 0.998*state + 0.05*w
			sample = state
		case "brown":
			w := float32(rand.NormFloat64())
			state += w * 0.02
			if state > 1 {
				state = 1
			} else if state < -1 {
				state = -1
			}
			sample = state
		default:
			sample = float32(rand.NormFloat64())
		}
		data[i] = sample * wn.volume
	}
	return data
}

func (wn *WhiteNoise) start() error {
	err := portaudio.Initialize()
	if err != nil {
		return err
	}
	wn.buffer = make([]float32, 1024)
	wn.running = true
	wn.startTime = time.Now()

	stream, err := portaudio.OpenDefaultStream(0, 1, 44100, len(wn.buffer), wn.processAudio)
	if err != nil {
		return err
	}
	wn.stream = stream
	err = stream.Start()
	if err != nil {
		return err
	}
	fmt.Printf("🌊 Белый шум запущен. Таймер: %d мин.\n", wn.timerMinutes)
	fmt.Println("Команды: 's' - стоп, '+'/'-' - громкость, 't' - таймер, 'q' - выход")

	go wn.handleTimer()

	scanner := bufio.NewScanner(os.Stdin)
	for wn.running {
		if scanner.Scan() {
			cmd := scanner.Text()
			switch cmd {
			case "s":
				wn.running = false
			case "+":
				wn.volume = float32(math.Min(1.0, float64(wn.volume+0.05)))
				fmt.Printf("Громкость: %d%%\n", int(wn.volume*100))
			case "-":
				wn.volume = float32(math.Max(0.0, float64(wn.volume-0.05)))
				fmt.Printf("Громкость: %d%%\n", int(wn.volume*100))
			case "t":
				fmt.Print("Введите время в минутах (5-120): ")
				scanner.Scan()
				mins, err := strconv.Atoi(scanner.Text())
				if err == nil && mins >= 5 && mins <= 120 {
					wn.timerMinutes = mins
					wn.startTime = time.Now()
					fmt.Printf("Таймер установлен на %d мин.\n", mins)
				}
			case "q":
				wn.running = false
			}
		}
	}
	stream.Stop()
	stream.Close()
	portaudio.Terminate()
	fmt.Println("⏹ Звук остановлен.")
	return nil
}

func (wn *WhiteNoise) processAudio(in []float32) {
	if !wn.running {
		return
	}
	// Просто генерируем
	out := wn.generateSamples(len(in))
	copy(in, out)
}

func (wn *WhiteNoise) handleTimer() {
	for wn.running {
		time.Sleep(1 * time.Second)
		elapsed := time.Since(wn.startTime).Seconds()
		remaining := float64(wn.timerMinutes*60) - elapsed
		if remaining <= 0 {
			wn.running = false
			fmt.Println("\n⏹ Время вышло.")
			break
		}
		if remaining < wn.fadeDuration {
			fade := float32(remaining / wn.fadeDuration)
			wn.volume = fade * 0.7 // начальная громкость 0.7
		}
	}
}

func main() {
	rand.Seed(time.Now().UnixNano())
	wn := NewWhiteNoise()
	if err := wn.start(); err != nil {
		fmt.Println("Ошибка:", err)
	}
}
