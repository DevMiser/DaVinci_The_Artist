# the following program is provided by DevMiser - https://github.com/DevMiser

import boto3
import datetime
import io
import openai
import os
import pvcobra
import pvleopard
import pvporcupine
import pyaudio
import random
import struct
import sys
import textwrap
import threading
import time
import urllib.request
import paho.mqtt.publish as publish

from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

from colorama import Fore, Style
from PIL import Image,ImageDraw,ImageFont,ImageOps,ImageEnhance
from pvleopard import *
from pvrecorder import PvRecorder
from threading import Thread, Event
from time import sleep

import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
led1_pin=18
led2_pin=24
GPIO.setup(led1_pin, GPIO.OUT)
GPIO.output(led1_pin, GPIO.LOW)
GPIO.setup(led2_pin, GPIO.OUT)
GPIO.output(led2_pin, GPIO.LOW)

audio_stream = None
cobra = None
pa = None
polly = boto3.client('polly')
porcupine = None
recorder = None
wav_file = None

GPT_model = "gpt-3.5-turbo" # most capable GPT-3.5 model and optimized for chat
openai.api_key = "put your secret API key between these quotation marks"
pv_access_key= "put your secret access key between these quotation marks"

Clear_list = ["Clear the screen",
    "Clear the display",
    "Clear the canvas",
    "Clear the art frame",
    "Clean the screen",
    "Clean the display",
    "Clean the canvas",
    "Clean the art frame",
    "Wipe the screen",
    "Wipe the display",
    "Wipe the canvas",
    "Wipe the art frame",
    "Erase the screen",
    "Erase the display",
    "Erase the canvas",
    "Erase the art frame",
    "Erased the screen",
    "Erased the display",
    "Erased the canvas",
    "Erased the art frame",
    "Blank screen",
    "Blank display",]

Create_list = ["Draw",
    "Paint",
    "Create an image",
    "Create a painting",
    "Create a drawing",
    "Make an image",
    "Make a painting",
    "Make a drawing"
    ]

prompt = ["How may I assist you?",
    "How may I help?",
    "What can I do for you?",
    "Ask me anything.",
    "Yes?",
    "I'm here.",
    "I'm listening.",
    "What would you like me to do?"]

chat_log=[
    {"role": "system", "content": "You are a helpful assistant."},
    ]

#DaVinci will 'remember' earlier queries so that it has greater continuity in its response
#the following will delete that 'memory' five minutes after the start of the conversation
def append_clear_countdown():
    sleep(120)
    global chat_log
    chat_log.clear()
    chat_log=[
        {"role": "system", "content": "You are a helpful assistant."},
        ]    
    global count
    count = 0
    t_count.join

def ChatGPT(query):
    chat_log.append ({"role": "user", "content": query})
    response = openai.ChatCompletion.create(
    model=GPT_model,
    messages=chat_log
    )
    return str.strip(response['choices'][0]['message']['content'])
    chat_log.append({"role": "system", "content": response})

def clean_screen(transcript):
    
    global Chat
    
    for word in Clear_list:
        if word in transcript:
            print("\'"f"{word}\' detected")
            voice(f"I heard the phrase {word}.  I will instruct the Art Frame to erase its display.  It will take several minutes to complete.")
            current_time
            auth = {'username':"DaVinci", 'password':"PlaceYourPasswordHere"}
            publish.single("AI-Art-Frame", "Clean", hostname="PlaceYourArtFrameIPAddressHere")
            print("\nErase screen request sent to DALL-E 2 AI Art Frame.  It will take several minutes to complete.")
            Chat = 0
            sleep(1)

def current_time():

    time_now = datetime.datetime.now()
    formatted_time = time_now.strftime("%m-%d-%Y %I:%M %p\n")
    print("The current date and time is:", formatted_time)  

def detect_silence():

    cobra = pvcobra.create(access_key=pv_access_key)

    silence_pa = pyaudio.PyAudio()

    cobra_audio_stream = silence_pa.open(
                    rate=cobra.sample_rate,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=cobra.frame_length)

    last_voice_time = time.time()

    while True:
        cobra_pcm = cobra_audio_stream.read(cobra.frame_length)
        cobra_pcm = struct.unpack_from("h" * cobra.frame_length, cobra_pcm)
           
        if cobra.process(cobra_pcm) > 0.2:
            last_voice_time = time.time()
        else:
            silence_duration = time.time() - last_voice_time
            if silence_duration > 1.3:
                print("End of query detected\n")
                GPIO.output(led1_pin, GPIO.LOW)
                GPIO.output(led2_pin, GPIO.LOW)
                cobra_audio_stream.stop_stream                
                cobra_audio_stream.close()
                cobra.delete()
                last_voice_time=None
                break

def draw_request(transcript):
    
    global Chat
    
    def dall_e2(prompt):
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="512x512" #can also be 256x256 or 1024x1024
        )
        return (response['data'][0]['url'])
   
    for word in Create_list:
        if word in transcript:
            print("\'"f"{word}\' detected")
            voice(f"I heard the phrase {word}.  I'll create the requested image and send it to your Art Frame for viewing.") 
            prompt_full = (transcript.replace(word, "") + (" using vibrant colors"))                
            print("You requested the following image: " + prompt_full)
            print("\nCreating image...\n")
            image_url = dall_e2(prompt_full)
#            print(image_url) #uncomment this line if you want to print the generated image's URL
            auth = {'username':"DaVinci", 'password':"PlaceYourPasswordHere"}
            publish.single("AI-Art-Frame", image_url, hostname="PlaceYourArtFrameIPAddressHere")
            print("Image URL sent to DALL-E 2 AI Art Frame for display")
            Chat = 0

def fade_leds(event):
    pwm1 = GPIO.PWM(led1_pin, 200)
    pwm2 = GPIO.PWM(led2_pin, 200)

    event.clear()

    while not event.is_set():
        pwm1.start(0)
        pwm2.start(0)
        for dc in range(0, 101, 5):
            pwm1.ChangeDutyCycle(dc)  
            pwm2.ChangeDutyCycle(dc)
            time.sleep(0.05)
        time.sleep(0.75)
        for dc in range(100, -1, -5):
            pwm1.ChangeDutyCycle(dc)                
            pwm2.ChangeDutyCycle(dc)
            time.sleep(0.05)
        time.sleep(0.75)
        
def listen():

    cobra = pvcobra.create(access_key=pv_access_key)

    listen_pa = pyaudio.PyAudio()

    listen_audio_stream = listen_pa.open(
                rate=cobra.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=cobra.frame_length)

    print("Listening...")

    while True:
        listen_pcm = listen_audio_stream.read(cobra.frame_length)
        listen_pcm = struct.unpack_from("h" * cobra.frame_length, listen_pcm)
           
        if cobra.process(listen_pcm) > 0.3:
            print("Voice detected")
            listen_audio_stream.stop_stream
            listen_audio_stream.close()
            cobra.delete()
            break

def responseprinter(chat):
    for word in chat:
       time.sleep(0.055)
       print(word, end="", flush=True)
    print()

def voice(chat):
   
    voiceResponse = polly.synthesize_speech(Text=chat, OutputFormat="mp3",
                    VoiceId="Matthew") #other options include Amy, Joey, Nicole, Raveena and Russell
    if "AudioStream" in voiceResponse:
        with voiceResponse["AudioStream"] as stream:
            output_file = "speech.mp3"
            try:
                with open(output_file, "wb") as file:
                    file.write(stream.read())
            except IOError as error:
                print(error)

    else:
        print("did not work")

    pygame.mixer.init()     
    pygame.mixer.music.load(output_file)
#    pygame.mixer.music.set_volume(0.8) # uncomment to control the the playback volume (from 0.0 to 1.0  
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pass
    sleep(0.2)

def wake_word():

    porcupine = pvporcupine.create(keywords=["computer", "jarvis", "DaVinci",],
                            access_key=pv_access_key,
                            sensitivities=[0.1, 0.1, 0.1], #from 0 to 1.0 - a higher number reduces the miss rate at the cost of increased false alarms
                                   )
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    
    wake_pa = pyaudio.PyAudio()

    porcupine_audio_stream = wake_pa.open(
                    rate=porcupine.sample_rate,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=porcupine.frame_length)
    
    Detect = True

    while Detect:
        porcupine_pcm = porcupine_audio_stream.read(porcupine.frame_length)
        porcupine_pcm = struct.unpack_from("h" * porcupine.frame_length, porcupine_pcm)

        porcupine_keyword_index = porcupine.process(porcupine_pcm)

        if porcupine_keyword_index >= 0:

            GPIO.output(led1_pin, GPIO.HIGH)
            GPIO.output(led2_pin, GPIO.HIGH)

            print(Fore.GREEN + "\nWake word detected\n")
            current_time()
            porcupine_audio_stream.stop_stream
            porcupine_audio_stream.close()
            porcupine.delete()         
            os.dup2(old_stderr, 2)
            os.close(old_stderr)
            Detect = False

class Recorder(Thread):
    def __init__(self):
        super().__init__()
        self._pcm = list()
        self._is_recording = False
        self._stop = False

    def is_recording(self):
        return self._is_recording

    def run(self):
        self._is_recording = True

        recorder = PvRecorder(device_index=-1, frame_length=512)
        recorder.start()

        while not self._stop:
            self._pcm.extend(recorder.read())
        recorder.stop()

        self._is_recording = False

    def stop(self):
        self._stop = True
        while self._is_recording:
            pass

        return self._pcm

try:

    o = create(
        access_key=pv_access_key,
        )
    
    event = threading.Event()

    count = 0

    while True:
        
        Chat = 1
        if count == 0:
            t_count = threading.Thread(target=append_clear_countdown)
            t_count.start()
        else:
            pass   
        count += 1
        wake_word()
# comment out the next line if you do not want DaVinci to verbally respond to his name        
        voice(random.choice(prompt))
        recorder = Recorder()
        recorder.start()
        listen()
        detect_silence()
        transcript, words = o.process(recorder.stop())
        t_fade = threading.Thread(target=fade_leds, args=(event,))
        t_fade.start()
        recorder.stop()
        print("You said: " + transcript)
        draw_request(transcript)
        clean_screen(transcript)
        if Chat == 1:        
            (res) = ChatGPT(transcript)
            print("\nChatGPT's response is:\n")        
            t1 = threading.Thread(target=voice, args=(res,))
            t2 = threading.Thread(target=responseprinter, args=(res,))

            t1.start()
            t2.start()

            t1.join()
            t2.join()
        event.set()
        GPIO.output(led1_pin, GPIO.LOW)
        GPIO.output(led2_pin, GPIO.LOW)        
        recorder.stop()
        o.delete
        recorder = None
        
except KeyboardInterrupt:
    print("\nExiting ChatGPT Virtual Assistant")
    o.delete
    GPIO.cleanup()




