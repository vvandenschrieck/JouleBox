import neopixel, machine, time

PIN_NUMBER = 6
NUM_PIX = 60
pixels = neopixel.NeoPixel(machine.Pin(PIN_NUMBER), NUM_PIX)
 
yellow = (255, 100, 0)
orange = (200, 100, 0)
green = (0, 200, 0)
blue = (0, 0, 255)
red = (200, 0, 0)
color0 = red
black = (0,0,0)


#pixels.brightness(50)
#pixels.fill(orange)
#pixels.set_pixel_line_gradient(3, 13, green, blue)
#pixels.set_pixel_line(14, 16, red)
#pixels.set_pixel(20, (255, 255, 255))



def set_value(x):
    leds_to_turn_on = int(x/100*60)
    c = green
    if x<50:
        c = yellow
    if x < 10:
        c = red
    for i in range(NUM_PIX): 
        range_1 = i in range(0, int((leds_to_turn_on+1)//2)) 
        
        range_2 = i in range(59-int((leds_to_turn_on)//2)+1, 60)
        
        if (range_1 or range_2):
            pixels[i] = c
        else:
            pixels[i] = black
    
    pixels.write()

def test():
    for s in range(0,101):

        print(100-s)
        set_value(100-s)
        time.sleep_ms(500)

