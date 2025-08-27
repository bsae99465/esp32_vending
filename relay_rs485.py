# main.py
# สำหรับ ESP32-S3 ควบคุมรีเลย์ RS485 
# โดยใช้โมดูล RS485 to TTL แบบ "ควบคุมทิศทางอัตโนมัติ" (ไม่มีขา DE/RE)

from machine import UART, Pin
import umodbus.rtu as modbus_rtu
import time

# --- การตั้งค่า ---
# ตั้งค่า UART ที่จะใช้เชื่อมต่อ
UART_ID = 2
BAUDRATE = 9600

# ที่อยู่ของโมดูลรีเลย์ (Slave ID)
SLAVE_ID = 1
# --- จบการตั้งค่า ---


def control_relay(modbus_master, relay_number, state):
    """
    ส่งคำสั่ง Modbus เพื่อควบคุมรีเลย์
    :param modbus_master: อ็อบเจกต์ ModbusRTU
    :param relay_number: หมายเลขรีเลย์ (1-8)
    :param state: สถานะที่ต้องการ (True=ON, False=OFF)
    """
    coil_address = relay_number - 1
    
    try:
        print(f"กำลังสั่งให้รีเลย์ #{relay_number} {'เปิด' if state else 'ปิด'}...")
        result = modbus_master.write_single_coil(
            slave_addr=SLAVE_ID, 
            register_addr=coil_address, 
            value=0xFF00 if state else 0x0000
        )
        print(f"สำเร็จ! ผลลัพธ์: {result}")
        return True
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการสื่อสารกับรีเลย์ #{relay_number}: {e}")
        return False

# --- ส่วนโปรแกรมหลัก ---

# 1. เริ่มต้นการทำงานของ UART
# ใช้ tx=17, rx=16
uart = UART(UART_ID, baudrate=BAUDRATE, tx=Pin(17), rx=Pin(16))
print("UART Initialized:", uart)

# 2. สร้างอ็อบเจกต์ Modbus RTU Master
# *** จุดที่เปลี่ยนแปลง ***
# เราไม่ต้องใส่พารามิเตอร์ de_pin อีกต่อไป
rtu_master = modbus_rtu.ModbusRTU(
    addr=SLAVE_ID,
    uart=uart
)
print("Modbus RTU Master Created (Auto Direction Control).")

# 3. วนลูปทดสอบการทำงาน
print("\n--- เริ่มการทดสอบควบคุมรีเลย์ ---")
while True:
    for i in range(1, 9): # วนลูปสำหรับรีเลย์ 1 ถึง 8
        
        # เปิดรีเลย์
        control_relay(rtu_master, relay_number=i, state=True)
        time.sleep(1)
        
        # ปิดรีเลย์
        control_relay(rtu_master, relay_number=i, state=False)
        time.sleep(1)

