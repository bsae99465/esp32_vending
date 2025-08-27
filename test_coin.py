# ต่อเครื่องหยอดเหรียญเข้าขา GPIO 12 เพื่อทดสอบ
from machine import Pin
import time

coin_pin = Pin(12, Pin.IN, Pin.PULL_UP)
pulse_count = 0
last_pulse_time = 0
debounce_time = 200  # มิลลิวินาที, สำหรับป้องกันการนับพัลส์ซ้ำ

def pulse_handler(pin):
    global pulse_count, last_pulse_time
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_pulse_time) > debounce_time:
        pulse_count += 1
        last_pulse_time = current_time

coin_pin.irq(trigger=Pin.IRQ_FALLING, handler=pulse_handler)

print("Waiting for pulses...")

while True:
    if pulse_count > 0:
        if time.ticks_diff(time.ticks_ms(), last_pulse_time) > 500: # ถ้าหยุดรับพัลส์ไป 500ms
            if pulse_count == 1:
                print("1 Baht coin detected")
            elif pulse_count == 5:
                print("5 Baht coin detected")
            elif pulse_count == 10:
                print("10 Baht coin detected")
            else:
                print(f"Unknown coin with {pulse_count} pulses")
            pulse_count = 0  # Reset counter
    time.sleep(0.1)
