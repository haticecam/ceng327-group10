import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

def moving_average(x, N=5):
    return np.convolve(x, np.ones(N)/N, mode='valid')

def exponential_moving_average(x, alpha=0.1):
    y = np.zeros_like(x)
    y[0] = x[0]
    for i in range(1, len(x)):
        y[i] = alpha*x[i] + (1-alpha)*y[i-1]
    return y

# Generation of Synthetic Data
np.random.seed(0)
time = np.linspace(0, 10, 200)
true_temp = 25.0 + 0.5*np.sin(2*np.pi*0.5*time)

# Gaussian noise with std dev = 0.5
noise = np.random.normal(0, 0.5, size=time.size)
measured_temp = true_temp + noise

# Filters
window_size = 5
ma_smoothed = moving_average(measured_temp, N=window_size)
ema_smoothed = exponential_moving_average(measured_temp, alpha=0.2)
savgol_smoothed = savgol_filter(measured_temp, window_length=11, polyorder=2)

plt.figure(figsize=(12, 8))

# Noisy measurements
plt.plot(time, measured_temp, label='Noisy Measurements', alpha=0.5, color='gray')

# True temperature signal
plt.plot(time, true_temp, label='True Temperature', linewidth=2, color='black')

# Moving average method's results
valid_time = time[(window_size-1)//2:-(window_size-1)//2]
plt.plot(valid_time, ma_smoothed, label='Moving Average', linewidth=2, color='blue')

# Exponential moving average method's results
plt.plot(time, ema_smoothed, label='Exponential Moving Average', linewidth=2, color='red')

# Savitzky-Golay filter's results
plt.plot(time, savgol_smoothed, label='Savitzky-Golay', linewidth=2, color='green')

plt.title('Temperature Sensor Signal Smoothing')
plt.xlabel('Time (s)')
plt.ylabel('Temperature (°C)')
plt.legend()
plt.grid(True)
plt.show()
