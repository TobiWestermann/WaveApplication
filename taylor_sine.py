import math
import matplotlib.pyplot as plt
import numpy as np
import time

sampling_rate = 96000
duration = 3.0
frequency = 440
phase_shift = 10
periods = 3

period_duration = periods / frequency
num_samples = int(sampling_rate * period_duration)

t = [i / sampling_rate for i in range(num_samples)]

def taylor_sine_optimized(x, n_terms=10):
    sine_approx = x
    term = x
    for n in range(1, n_terms):
        term *= -x * x / ((2 * n) * (2 * n + 1))
        sine_approx += term
    return sine_approx

start_time = time.time()

sinus_manual = []
for time_point in t:
    x = 2 * math.pi * frequency * time_point
    x = ((x + math.pi) % (2 * math.pi)) - math.pi
    sinus_value = taylor_sine_optimized(x)
    sinus_manual.append(sinus_value)

end_time = time.time()
print(f"Berechnungszeit (manuelle Taylor-Reihe): {end_time - start_time} Sekunden")

start_time = time.time()
phase_radians = np.deg2rad(phase_shift)
sinus_numpy = np.sin(2 * np.pi * frequency * np.array(t) + phase_radians)
end_time = time.time()
print(f"Berechnungszeit (numpy.sin): {end_time - start_time} Sekunden")

plt.figure(figsize=(10, 6))
plt.plot(t, sinus_manual, label='Manuell berechnet (Taylor-Reihe)', alpha=0.7)
plt.plot(t, sinus_numpy, label=f'Numpy sin (Phasenverschiebung: {phase_shift}°)', linestyle='--', alpha=0.7)
plt.xlabel('Zeit (s)')
plt.ylabel('Amplitude')
plt.title(f'Vergleich zwischen manuell berechnetem Sinus und numpy.sin (Frequenz: {frequency} Hz, 3 Perioden)')
plt.legend()
plt.grid()
plt.show()
