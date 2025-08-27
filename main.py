# main.py
import machine
import time
import tm1637

# --- 1. กำหนดค่าและ khởi tạoอุปกรณ์ ---

# -- ค่าคงที่ของระบบ --
ITEM_PRICE = 10
BUTTON_LIGHT_RELAY = 7
CABINET_LIGHT_RELAY = 8

# -- RS485 (ใช้ UART หมายเลข 2) --
uart = machine.UART(2, baudrate=9600, tx=17, rx=18)

# -- TM1637 Display --
display = tm1637.TM1637(clk=machine.Pin(10), dio=machine.Pin(11))
display.brightness(2)

# -- Push Buttons (ใช้ Internal Pull-up) --
button_pins_nums = [19, 20, 21, 47, 48]
buttons = [machine.Pin(p, machine.Pin.IN, machine.Pin.PULL_UP) for p in button_pins_nums]

# -- Inputs with Interrupts --
coin_pin = machine.Pin(12, machine.Pin.IN)
motor_sensor_pin = machine.Pin(13, machine.Pin.IN)


# --- 2. ตัวแปรสำหรับจัดการสถานะ (State Variables) ---
app_state = {
    'credit': 0,
    'motor_cycle_done': False,
    'button_light_on': False # เพิ่มตัวแปรเช็คสถานะไฟปุ่มกด
}

# --- 3. ฟังก์ชัน Interrupt Handler (ISR) ---
last_coin_pulse = 0
def coin_handler(pin):
    global last_coin_pulse
    now = time.ticks_ms()
    if time.ticks_diff(now, last_coin_pulse) > 100:
        app_state['credit'] += 1
        print(f"Coin Inserted! Current Credit: {app_state['credit']}")
        last_coin_pulse = now

def motor_cycle_handler(pin):
    app_state['motor_cycle_done'] = True
    print("Motor cycle completed!")

# ผูก Interrupt เข้ากับ Pin
coin_pin.irq(trigger=machine.Pin.IRQ_RISING, handler=coin_handler)
motor_sensor_pin.irq(trigger=machine.Pin.IRQ_FALLING, handler=motor_cycle_handler)


# --- 4. ฟังก์ชันสำหรับควบคุม Relay ผ่าน RS485 ---
def set_relay_state(channel, state):
    """
    ฟังก์ชันสำหรับส่งคำสั่งควบคุมรีเลย์ผ่าน RS485
    channel: หมายเลขรีเลย์ (1-8)
    state: True สำหรับเปิด (ON), False สำหรับปิด (OFF)
    """
    # !!! สำคัญ: โปรโตคอลส่วนนี้ต้องปรับแก้ให้ตรงกับคู่มือของ Relay Board ที่คุณใช้ !!!
    # ตัวอย่างนี้ใช้โปรโตคอลสมมติ [Start, Channel, State, End]
    # 0xA0 = Start Byte
    # 0x01 = ON, 0x00 = OFF
    # 0xA1 = End Byte
    
    command_state = 0x01 if state else 0x00
    command = bytearray([0xA0, channel, command_state, 0xA1])
    
    state_text = "ON" if state else "OFF"
    print(f"Setting Relay {channel} to {state_text}. Command: {command.hex()}")
    uart.write(command)
    time.sleep_ms(50) # หน่วงเวลาเล็กน้อยหลังส่งคำสั่ง


# --- 5. Setup เริ่มต้นการทำงาน ---
print("Vending Machine Controller is starting...")
# เปิดไฟตู้ (Relay 8) ทันทีเมื่อเครื่องพร้อมทำงาน
set_relay_state(CABINET_LIGHT_RELAY, True) 
display.number(0)


# --- 6. Loop หลักของโปรแกรม ---
while True:
    # -- 6.1 อัปเดตหน้าจอแสดงผล --
    # ใช้ try-except ป้องกันกรณีค่า credit เปลี่ยนขณะกำลังแสดงผล
    try:
        current_credit = app_state['credit']
        display.number(current_credit)
    except Exception as e:
        pass

    # -- 6.2 ควบคุมไฟปุ่มกด (Relay 7) ตามจำนวนเงิน --
    if current_credit >= ITEM_PRICE and not app_state['button_light_on']:
        # ถ้าเงินพอ และไฟยังไม่เปิด -> ให้เปิดไฟ
        set_relay_state(BUTTON_LIGHT_RELAY, True)
        app_state['button_light_on'] = True
    elif current_credit < ITEM_PRICE and app_state['button_light_on']:
        # ถ้าเงินไม่พอ และไฟยังเปิดอยู่ -> ให้ปิดไฟ
        set_relay_state(BUTTON_LIGHT_RELAY, False)
        app_state['button_light_on'] = False

    # -- 6.3 ตรวจสอบการกดปุ่มเลือกสินค้า --
    for i, button in enumerate(buttons):
        if not button.value(): # ปุ่มถูกกด (Active Low)
            selected_item_relay = i + 1 # Relay 1 ถึง 5
            print(f"Button for item {selected_item_relay} pressed.")
            
            if current_credit >= ITEM_PRICE:
                # 1. ปิดไฟปุ่มทันที
                set_relay_state(BUTTON_LIGHT_RELAY, False)
                app_state['button_light_on'] = False
                
                # 2. หักเงิน
                app_state['credit'] -= ITEM_PRICE
                print(f"Dispensing item {selected_item_relay}... New credit: {app_state['credit']}")
                display.number(app_state['credit']) # อัปเดตหน้าจอทันที
                
                # 3. สั่งจ่ายสินค้า (เปิด Relay)
                set_relay_state(selected_item_relay, True)
                
                # 4. รอจนกว่ามอเตอร์จะหมุนครบรอบ
                print("Waiting for motor...")
                start_wait_time = time.ticks_ms()
                while not app_state['motor_cycle_done']:
                    # มี Timeout ป้องกันกรณีเซ็นเซอร์ไม่ทำงาน
                    if time.ticks_diff(time.ticks_ms(), start_wait_time) > 5000: # รอสูงสุด 5 วินาที
                        print("Error: Motor sensor timeout!")
                        break
                    time.sleep_ms(50)
                
                # 5. หยุดจ่ายสินค้า (ปิด Relay)
                set_relay_state(selected_item_relay, False)
                
                # 6. รีเซ็ตสถานะเซ็นเซอร์
                app_state['motor_cycle_done'] = False
                print("Dispensing process finished.")
            
            else:
                print("Not enough credit!")
                # อาจจะแสดงผลบนจอว่า "Lo" (Low credit)
                display.show('Lo-C')
                time.sleep(1)

            # หน่วงเวลาเพื่อป้องกันการกดซ้ำ
            time.sleep_ms(300)

    time.sleep_ms(50) # หน่วงเวลาหลักของ Loop
