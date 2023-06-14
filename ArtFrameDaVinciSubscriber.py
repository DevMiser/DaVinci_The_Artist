import datetime
import paho.mqtt.client as mqtt
import io
import schedule
import threading
import time
import urllib.request
from inky.auto import auto
from PIL import Image,ImageDraw,ImageFont,ImageOps,ImageEnhance
from threading import Thread,Event
from time import sleep

display = auto()

import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
led1_pin=4
GPIO.setup(led1_pin, GPIO.OUT)
GPIO.output(led1_pin, GPIO.LOW)

event=threading.Event()
event2=threading.Event()

count = 0

def clean_screen():
    cycles = 1
    colours = (display.RED, display.BLACK, display.WHITE, display.CLEAN)
    colour_names = (display.colour, "red", "black", "white", "clean")
    img = Image.new("P", (display.WIDTH, display.HEIGHT))
    for i in range(cycles):
        print("Cleaning cycle %i\n" % (i + 1))
        for j, c in enumerate(colours):
            print("- updating with %s" % colour_names[j+1])
            display.set_border(c)
            for x in range(display.WIDTH):
                for y in range(display.HEIGHT):
                    img.putpixel((x, y), c)
            display.set_image(img)
            display.show()
            time.sleep(1)
    print("\nCleaning complete")
    
def current_time():

    time_now = datetime.datetime.now()
    formatted_time = time_now.strftime("%m-%d-%Y %I:%M %p\n")
    print("The current date and time is:", formatted_time)
    
def fade_leds(event):

    pwm1 = GPIO.PWM(led1_pin, 200)

    event.clear()

    while not event.is_set():
        pwm1.start(0)
        for dc in range(0, 101, 5):
            pwm1.ChangeDutyCycle(dc)  
            time.sleep(0.05)
        time.sleep(0.75)
        for dc in range(100, -1, -5):
            pwm1.ChangeDutyCycle(dc)                
            time.sleep(0.05)
        time.sleep(0.75)

def on_connect(client, userdata, flags, rc):
#    print("\nConnected with result code "+str(rc)) #uncomment this line if you want to print the result code
    if rc == 0:
        print("\nConnection successful")
    else:
        print("Connection unsuccessful") 
    client.subscribe("AI-Art-Frame")

def on_message(client, userdata, msg):
    print("\nMessage received from DaVinci\n")
    current_time()

    global count
    
    if count ==0:
        
        print("Starting refresh thread - automatically refreshes screen every day at midnight...\n")    
        global refresh_schedule        
        refresh_schedule = RefreshSchedule()
        refresh_schedule._thread.start()
      
    else:
        pass

    count +=1

    msg.payload = msg.payload.decode("utf-8") #decodes the UTF8 message to text
    if msg.payload == "Clean":
        refresh_schedule.pause()
        print("Request to erase the screen received.  This will take several minutes.\n")
        clean_screen()

    else:

        global img_resized
        image_url = str(msg.payload)
        t_fade = threading.Thread(target=fade_leds, args=(event,))
        t_fade.start()
        raw_data = urllib.request.urlopen(image_url).read()
        img = Image.open(io.BytesIO(raw_data))
        img_bordered = ImageOps.expand(img, border=(76,0), fill='black')    
        img_resized = img_bordered.resize((600, 448), Image.ANTIALIAS)
        display.set_image(img_resized)
        display.set_border(display.BLACK)
        print("Rendering image...\n")
        display.show()
#        img.show() #uncomment this line if you also want to show the image on a connected display
        event.set()
        GPIO.output(led1_pin, GPIO.LOW)
        refresh_schedule.resume()
        print("Done")
        
def refresh_screen():
    
    now = datetime.datetime.now()
    compare_time = now.strftime("%H:%M")
#    print(compare_time)
    if compare_time == "00:00":

        print("\nThe screen refreshes every day at midnight to help prevent burn-in\n")
        current_time()
        clean_screen()
        sleep(2)
        display.set_image(img_resized)
        display.set_border(display.BLACK)    
        print("\nRe-rendering")
        display.show()
        print("\nDone\n")
        
    else:
        pass

class RefreshSchedule:
    def __init__(self):
        self._paused = False
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._thread = threading.Thread(target=self.run)

    def run(self):
        schedule.every().day.at("00:00").do(refresh_screen) 
        while True:
            with self._lock:
                while self._paused:
                    self._cond.wait()
                schedule.run_pending()
            time.sleep(1)

    def pause(self):
        with self._lock:
            self._paused = True

    def resume(self):
        with self._lock:
            self._paused = False
            self._cond.notify()

try:
    
    client = mqtt.Client()
    client.username_pw_set("DaVinci", "ImageExchange32")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("192.168.1.155", 1883, 60)
    client.loop_forever()
    
except KeyboardInterrupt:
    print ("\nExiting ArtFrameDaVinciSubscriber")
    GPIO.cleanup