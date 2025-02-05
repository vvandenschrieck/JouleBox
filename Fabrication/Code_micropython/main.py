from machine import I2C, SoftI2C, ADC, Pin, Timer
import utime
import lin_gauge
import rad_gauge
import tm1637_7_seg as tm1637

from lcd_api import LcdApi
from pico_i2c_lcd import I2cLcd

utime.sleep(1)

# parameters
SDA_PIN = 16
SCL_PIN = 17
I2C_NUMMER = 0



###########################################################
# first check I2C adress of the screen (with screen alone)
###########################################################
sda=Pin(SDA_PIN)
scl=Pin(SCL_PIN)
i2c=I2C(I2C_NUMMER,sda=sda, scl=scl, freq=400000)
i2c=SoftI2C(sda=sda, scl=scl, freq=400000)
print('I2C address:')
print(i2c.scan(),' (decimal)')
print(hex(i2c.scan()[0]), ' (hex)')
###########################################################

I2C_ADDR = 0x27  # change here ! 
I2C_NUM_ROWS = 2 
I2C_NUM_COLS = 16


lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)





# Initialisation des 3 dispalys 4x7 segments
p_out_num_disp = tm1637.TM1637(clk=Pin(3,Pin.OUT), dio=Pin(2,Pin.OUT))
p_in_num_disp = tm1637.TM1637(clk=Pin(4,Pin.OUT), dio=Pin(2,Pin.OUT))
energy_num_disp = tm1637.TM1637(clk=Pin(5,Pin.OUT), dio=Pin(2,Pin.OUT))
p_out_num_disp.show('----')
p_in_num_disp.show('----')
energy_num_disp.show('----')


btn1 = Pin(20,Pin.IN,Pin.PULL_UP)
btn2 = Pin(19,Pin.IN,Pin.PULL_UP)
btn3 = Pin(18,Pin.IN,Pin.PULL_UP)

RELAY_PIN = 9

relay_pin = Pin(RELAY_PIN,Pin.OUT)

def power_on_off(on_off):
    relay_pin.value(on_off)

power_on_off(1)


utime.sleep(3)

p_out_num_disp.show('    ')
p_in_num_disp.show('    ')
energy_num_disp.show('    ')

LSB_TO_AMPS = 0.008171500
F_ECH_HS = 786
max_bat = 20
F_ECH_LS = 1

def get_current_u16():
    adc = ADC(Pin(28))               # create ADC object on ADC pin
    return (  adc.read_u16()>>4 ) #-i_measurement_offset_1         # read value, 0-65535 across voltage range 0.0v - 3.3v



timer1 = Timer()
timer2 = Timer()
#timer3 = Timer()

# Variables
last_time = 0
T_rotation = 0
speed = 0
speed_rpm = 0
wheel_circ = 0.6985*3.1416  # circonférence de ma roue x 24/27.5 pour les roues d'enfant
wheel_circ = 1.85  # circonférence de ma roue x 24/27.5 pour les roues d'enfant
debounce_time = 100000  


i_sum = 0
i_sum_of_squares = 0
int_count = 0
i_max = 1000000
i_min = 0
i_rms = 0
p_out = 0
p_in = 0




energy = max_bat #Wh

def hs_interrupt(timer):
    global int_count, i_sum, i_sum_of_squares, i_min, i_max
    i_inst = get_current_u16()
    i_sum += i_inst
    i_sum_of_squares += i_inst**2    

    # if i_inst>i_max:
    #     i1_max = i_inst

    # if i_inst<i_min:
    #     i_min = i_inst

    int_count += 1


def print_7_seg(display,value):
    display.number(int(value))

def ls_interrupt(timer):
    global int_count, i_sum, i_sum_of_squares, i_min, i_max, p_out, p_in, energy, last_time, T_rotation, speed,p_in
    current_time = utime.ticks_us()
    since_last_time = current_time - last_time
    if since_last_time>T_rotation:
        T_rotation = since_last_time
    
    if T_rotation>0:
        if T_rotation>5000000:
            speed = 0
            p_in = 0
        else:
            # speed_rpm = 60*1e6/T_rotation
            speed = wheel_circ/(T_rotation/1e6)*3.6  #km/h
            p_in = 2.47862037*speed+ 0.10765438*speed**2


    i_dc = i_sum/int_count
    #lcd.move_to(0,1)
    print("{}     ".format(int_count))

    i_av_sum_of_squares = i_sum_of_squares/int_count
    int_count = 0
    i_sum = 0
    i_sum_of_squares = 0
    int_count = 0

    i_rms = (abs(i_av_sum_of_squares - i_dc**2))**0.5*LSB_TO_AMPS
    if (i_rms<0.015):
        i_rms = 0
    p_out = i_rms*230 # W
    energy += (p_in-p_out)/3600/F_ECH_LS # every 1 second 
    if energy <= 0:
        energy = 0
        power_on_off(0)
        p_out = 0
    else:
        power_on_off(1)

def reed_switch_callback(pin):
    global last_time, T_rotation
    print("============================================Rotation detected")
    current_time_cb = utime.ticks_us()
    
    # Check if enough time has passed since the last trigger
    if ((current_time_cb - last_time) >= debounce_time):
        
        T_rotation = current_time_cb - last_time
        last_time = current_time_cb

    if (current_time_cb<last_time):
        last_time = current_time_cb

    


# Pin configuration
reed_switch_pin = Pin(21, Pin.IN,Pin.PULL_DOWN)

# Set up an interrupt on the reed switch pin
reed_switch_pin.irq(handler=reed_switch_callback, trigger=Pin.IRQ_RISING)    


timer1.init(freq=F_ECH_HS, mode=Timer.PERIODIC, callback=hs_interrupt)
timer2.init(freq=F_ECH_LS, mode=Timer.PERIODIC, callback=ls_interrupt)

display_backlight = 1

lcd.backlight_on()

#lcd.show_cursor()
lcd.clear() 
lcd.move_to(0,0)
#lcd.backlight_off()


try:
    while 1:
        rad_gauge.set_powers(p_in,p_out)
        print_7_seg(p_out_num_disp,p_out)
        print_7_seg(p_in_num_disp,p_in)
        print_7_seg(energy_num_disp,energy)
        lin_gauge.set_value(energy/max_bat*100)
        print("OUT : {} W   {}{}{}".format(p_out,btn1.value(),btn2.value(),btn3.value()))
        print("IN : {} W {} Wh  ".format(p_in,energy))
        print("SPEED {} kph".format(speed))
        print("T     {} s".format(T_rotation))
        if btn1.value()==0 :
            display_backlight = not display_backlight
            if display_backlight:
                lcd.backlight_on()
            else:
                lcd.backlight_off()

        if btn2.value()==0:

            if btn3.value()==0:
                increase_to = ((energy+10)//10*10)  # ajouter la quantité pour passer à la dizaine supérieure
                if (increase_to - energy)<1 :
                    increase_to += 10

                energy = increase_to
                max_bat = energy
            
        lcd.move_to(0,0)
        lcd.putstr("reste:{:4.2f} Wh".format(energy))

        utime.sleep(1)
        
       
except:

    timer1.deinit()
    timer2.deinit()
    print('dinit')

