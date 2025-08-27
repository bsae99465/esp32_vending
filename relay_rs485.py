# main.py
# สำหรับ ESP32-S3 ควบคุมรีเลย์ 8 ช่องผ่าน RS485 (Modbus RTU)

from machine import UART, Pin
import umodbus.rtu as modbus_rtu
import time

# --- การตั้งค่า ---
# ตั้งค่า UART ที่จะใช้เชื่อมต่อกับ RS485 to TTL Converter
# ESP32 มี UART หลายชุด, UART ID 2 คือ tx=17, rx=16
UART_ID = 2
BAUDRATE = 9600

# กำหนดขา GPIO สำหรับควบคุม DE/RE ของโมดูล MAX485
# ขานี้จะถูกตั้งเป็น HIGH ตอนส่งข้อมูล และ LOW ตอนรับข้อมูล
DE_RE_PIN = None

# ที่อยู่ของโมดูลรีเลย์ (Slave ID)
# ตรวจสอบจากคู่มือของโมดูลรีเลย์ (ปกติค่าเริ่มต้นคือ 1)
SLAVE_ID = 1

# --- จบการตั้งค่า ---


# ฟังก์ชันสำหรับควบคุมรีเลย์
def control_relay(modbus_master, relay_number, state):
    """
    ส่งคำสั่ง Modbus เพื่อควบคุมรีเลย์
    :param modbus_master: อ็อบเจกต์ ModbusRTU
    :param relay_number: หมายเลขรีเลย์ (1-8)
    :param state: สถานะที่ต้องการ (True=ON, False=OFF)
    """
    # ใน Modbus, Coil address เริ่มต้นที่ 0
    # ดังนั้น รีเลย์ 1 คือ Coil address 0
    coil_address = relay_number - 1
    
    try:
        print(f"กำลังสั่งให้รีเลย์ #{relay_number} {'เปิด' if state else 'ปิด'}...")
        # ใช้ Function Code 0x05 (Write Single Coil)
        # rt.write_single_coil(slave_addr, register_addr, value)
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
# ใช้ tx=17, rx=16 และขาควบคุม DE/RE ที่ GPIO 4
uart = UART(UART_ID, baudrate=BAUDRATE, tx=Pin(17), rx=Pin(16))
print("UART Initialized:", uart)

# 2. สร้างอ็อบเจกต์ Modbus RTU Master
# ส่ง uart และขา DE/RE เข้าไป
rtu_master = modbus_rtu.ModbusRTU(
    addr=SLAVE_ID,      # Address ของ Slave ที่จะสื่อสารด้วย (สามารถเปลี่ยนทีหลังได้)
    uart=uart
)
print("Modbus RTU Master Created.")

# 3. วนลูปทดสอบการทำงาน
print("\n--- เริ่มการทดสอบควบคุมรีเลย์ ---")
while True:
    for i in range(1, 9): # วนลูปสำหรับรีเลย์ 1 ถึง 8
        
        # เปิดรีเลย์
        control_relay(rtu_master, relay_number=i, state=True)
        time.sleep(1) # หน่วงเวลา 1 วินาที
        
        # ปิดรีเลย์
        control_relay(rtu_master, relay_number=i, state=False)
        time.sleep(1) # หน่วงเวลา 1 วินาที

