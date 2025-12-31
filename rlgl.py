print("Python Started!")
import os
os.environ['SDL_AUDIODRIVER'] = 'alsa'
os.environ['SDL_VIDEODRIVER'] = 'dummy'

import pygame
from picamera2 import Picamera2, Preview
from PIL import Image, ImageChops
import RPi.GPIO as GPIO
import numpy as np
import time, math

#Define GPIO
BUTTON_START = 22
BUTTON_FINISH = 18
LED_R = 19
LED_G = 21
LED_B = 23

#Define the game modes
MODE_IDLE = 0
MODE_SELECT = 1
MODE_CALIBRATE = 2
MODE_GREEN = 3
MODE_YELLOW = 4
MODE_RED = 5
MODE_LOSE = 6
MODE_WIN = 7

#Define colors
COLOR_OFF = 0
COLOR_RED = 1
COLOR_YELLOW = 2
COLOR_GREEN = 3
COLOR_BLUE = 4
COLOR_PURPLE = 5
COLOR_WHITE = 6

#Other constants
TIME_ANNOUNCE_DIFFICULTY = 1.1
TIME_ANNOUNCE_DONE = 3.5
TIME_GRACE_PERIOD = 0.3
TIME_READY_SET_GO = 3.5
TIME_LOSE = 2.0
TIME_WIN = 5.0
TIME_SCALING = 45.0
TIME_SCALE_FACTOR = 6.0
TIME_ELIMINATED = 2.5

#Initialize pygame audio mixer
print("Initializing pygame mixer...")
pygame.mixer.pre_init(44100, -16, 2, 1024)
pygame.mixer.init()

#Load the music
print("Loading music...")
pygame.mixer.music.load("/home/pi/RLGL/Audio/music.mp3")

#Load audio tracks
print("Loading audio tracks...")
snd_lose = pygame.mixer.Sound("/home/pi/RLGL/Audio/lose.wav")
snd_red = pygame.mixer.Sound("/home/pi/RLGL/Audio/red.wav")
snd_win = pygame.mixer.Sound("/home/pi/RLGL/Audio/win.wav")
snd_beep = pygame.mixer.Sound("/home/pi/RLGL/Audio/beep.wav")
snd_players = [pygame.mixer.Sound("/home/pi/RLGL/Audio/singleplayer.wav"),
               pygame.mixer.Sound("/home/pi/RLGL/Audio/twoplayer.wav")]
snd_difficulty = [pygame.mixer.Sound("/home/pi/RLGL/Audio/easy.wav"),
                  pygame.mixer.Sound("/home/pi/RLGL/Audio/medium.wav"),
                  pygame.mixer.Sound("/home/pi/RLGL/Audio/hard.wav")]
snd_ready = pygame.mixer.Sound("/home/pi/RLGL/Audio/ready.wav")
snd_leftout = pygame.mixer.Sound("/home/pi/RLGL/Audio/leftout.wav")
snd_rightout = pygame.mixer.Sound("/home/pi/RLGL/Audio/rightout.wav")

#Setup GPIO
print("Initializing GPIO...")
GPIO.setmode(GPIO.BOARD)
GPIO.setup(BUTTON_START, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_FINISH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_R, GPIO.OUT)
GPIO.setup(LED_G, GPIO.OUT)
GPIO.setup(LED_B, GPIO.OUT)

#Define level parameters
PARAM_IDLE_THRESH = 0    #Moving more than this triggers yellow transition.
PARAM_MIN_GREEN_TIME = 1 #Minimum seconds green can last
PARAM_MAX_GREEN_TIME = 2 #Maximum seconds green can last
PARAM_YELLOW_TIME = 3    #Seconds to show yellow light
PARAM_MIN_RED_TIME = 4   #Minimum seconds red can last
PARAM_MAX_RED_TIME = 5   #Maximum seconds red can last
PARAM_NUM_PLAYERS = 6    #Number of players
PARAM_DIFFICULTY = 7     #1-easy 2-medium 3-hard

#Difficulty levels
LEVELS = [(8000, 0.7, 9.0, 1.30, 2.0, 4.0, 1, 1),
          (5000, 0.5, 8.5, 1.10, 2.5, 4.5, 1, 2),
          (2000, 0.3, 8.0, 0.85, 3.0, 5.5, 1, 3),
          (8000, 0.7, 9.0, 1.30, 2.0, 4.0, 2, 1),
          (5000, 0.5, 8.5, 1.10, 2.5, 4.5, 2, 2),
          (2000, 0.3, 8.0, 0.85, 3.0, 5.5, 2, 3),]

#Set the color of the LEDs
def set_color(c):
    r,g,b = 0,0,0
    if c == COLOR_RED:
        r,g,b = 1,0,0
    elif c == COLOR_YELLOW:
        r,g,b = 1,1,0
    elif c == COLOR_GREEN:
        r,g,b = 0,1,0
    elif c == COLOR_BLUE:
        r,g,b = 0,0,1
    elif c == COLOR_PURPLE:
        r,g,b = 1,0,1
    elif c == COLOR_WHITE:
        r,g,b = 1,1,1
    GPIO.output(LED_R, GPIO.LOW if r == 0 else GPIO.HIGH)
    GPIO.output(LED_G, GPIO.LOW if g == 0 else GPIO.HIGH)
    GPIO.output(LED_B, GPIO.LOW if b == 0 else GPIO.HIGH)

#Initialize game settings
mode = MODE_IDLE
timer = time.perf_counter()
totalTime = time.perf_counter()
level = 0
lastImage = None
lastCaptureTime = 0
interval = 0.0
announce_difficulty = False
background_noise = 1e20
set_color(COLOR_OFF)

#Open camera for capture
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": "RGB888"}))
picam2.set_controls({
    "AeEnable": True,
    "AwbEnable": True,
})
#picam2.start_preview(Preview.QTGL, x=100, y=100, width=640, height=480)
picam2.start_preview(Preview.NULL, width=640, height=480)
picam2.start()

#Motion detection
def detect_motion():
    #Handle first frame
    global lastImage, lastCaptureTime
    image = picam2.capture_image("main")
    captureTime = time.perf_counter()
    if lastImage is None:
        lastImage = image
        lastCaptureTime = captureTime
        return (0.0, 0.0)
    
    #Handle new frames
    diffImg = ImageChops.difference(image, lastImage)
    diffImg = diffImg.convert('L')
    motion = np.array(diffImg) > 10
    left_motion = motion[:,motion.shape[1]//2:].sum()
    right_motion = motion[:,:motion.shape[1]//2].sum()
    timeDelta = captureTime - lastCaptureTime
    
    lastImage = image
    lastCaptureTime = captureTime
    
    #result = (left_motion * timeDelta, right_motion * timeDelta)
    result = (left_motion, right_motion)
    return result

#Change the level and play sound effect
def select_level():
    global level, timer, announce_difficulty
    pygame.mixer.stop()
    announce_difficulty = False
    timer = time.perf_counter()
    level = (level + 1) % len(LEVELS)
    num_players = LEVELS[level][PARAM_NUM_PLAYERS]
    snd_players[num_players - 1].play()
    print("Selected Level: " + str(level))

#Callback for start button
def on_start_pressed(channel):
    global mode, level
    #Debounce
    time.sleep(0.01)
    if GPIO.input(BUTTON_START): return
    if mode == MODE_IDLE:
        level -= 1
        set_color(COLOR_PURPLE)
        mode = MODE_SELECT
        select_level()
    elif mode == MODE_SELECT:
        select_level()
    else:
        pygame.mixer.music.stop()
        pygame.mixer.stop()
        set_color(COLOR_BLUE)
        mode = MODE_IDLE

#Callback for finish trigger
def on_finished(channel):
    global mode, level
    #Debounce
    time.sleep(0.01)
    if not GPIO.input(BUTTON_FINISH): return
    if mode == MODE_GREEN or mode == MODE_YELLOW:
        mode = MODE_WIN
    elif mode == MODE_RED:
        if time.perf_counter() - timer <= TIME_GRACE_PERIOD:
            mode = MODE_WIN
        else:
            lose_game(0)

#Start green light
def start_green():
    global mode, timer, lastImage, interval
    set_color(COLOR_GREEN)
    pygame.mixer.music.play(start=32.0)
    mode = MODE_GREEN
    lastImage = None
    interval = LEVELS[level][PARAM_MAX_GREEN_TIME]
    timer = time.perf_counter()

def start_red():
    global mode, timer, lastImage, interval
    set_color(COLOR_RED)
    snd_red.play()
    mode = MODE_RED
    lastImage = None
    minRed = LEVELS[level][PARAM_MIN_RED_TIME]
    maxRed = LEVELS[level][PARAM_MAX_RED_TIME]
    interval = minRed + np.random.random() * (maxRed - minRed)
    timer = time.perf_counter()

def lose_game(player):
    global mode
    print("Player " + str(player) + " Lose!")
    pygame.mixer.stop()
    pygame.mixer.music.stop()
    snd_lose.play()
    time.sleep(TIME_LOSE)
    if player > 0:
        (snd_leftout if player == 1 else snd_rightout).play()
        time.sleep(TIME_ELIMINATED)
    else:
        time.sleep(1.0)
    mode = MODE_IDLE
    set_color(COLOR_BLUE)

def win_game():
    global mode
    print("You Win!")
    pygame.mixer.stop()
    pygame.mixer.music.stop()
    set_color(COLOR_GREEN)
    snd_win.play()
    time.sleep(TIME_WIN)
    mode = MODE_IDLE
    set_color(COLOR_BLUE)

def get_motion_thresh():
    t = max(TIME_SCALING - (time.perf_counter() - totalTime), 0.0)
    s = -math.log(TIME_SCALE_FACTOR) / TIME_SCALING
    motionScale = TIME_SCALE_FACTOR * math.exp(s * t)
    #s = t / TIME_SCALING
    #motionScale = (1.0 - s) * TIME_SCALE_FACTOR + s
    return background_noise + LEVELS[level][PARAM_IDLE_THRESH] * motionScale

def motion_test(motionL, motionR, motionThresh):
    if LEVELS[level][PARAM_NUM_PLAYERS] == 1:
        if (motionL + motionR) > motionThresh:
            return 0
        else:
            return -1
    else:
        if motionL > motionThresh:
            return 1
        elif motionR > motionThresh:
            return 2
        else:
            return -1

#Capture a single image on startup to debug focus if it becomes an issue
picam2.capture_image("main").save("debug_focus.png")

#Indicate that the game is ready to start
set_color(COLOR_BLUE)
GPIO.add_event_detect(BUTTON_START, GPIO.FALLING, callback=on_start_pressed, bouncetime=100)
GPIO.add_event_detect(BUTTON_FINISH, GPIO.RISING, callback=on_finished, bouncetime=100)
print("Waiting to start game.")

#Start the game loop
while True:
    if mode == MODE_IDLE:
        #Waiting for the start button to be pressed
        time.sleep(0.01)
    elif mode == MODE_SELECT:
        #Waiting for the timer to start the game
        time.sleep(0.01)
        if not announce_difficulty and time.perf_counter() - timer >= TIME_ANNOUNCE_DIFFICULTY:
            announce_difficulty = True
            difficulty = LEVELS[level][PARAM_DIFFICULTY]
            snd_difficulty[difficulty - 1].play()
        if time.perf_counter() - timer >= TIME_ANNOUNCE_DONE:
            print("Game starting...")
            snd_ready.play()
            set_color(COLOR_RED)
            lastImage = None
            background_noise = 1e20
            timer = time.perf_counter()
            mode = MODE_CALIBRATE
    elif mode == MODE_CALIBRATE:
        time.sleep(0.01)
        motionL, motionR = detect_motion()
        if motionL > 0.0 and motionR > 0.0:
            background_noise = min(background_noise, motionL + motionR)
        if time.perf_counter() - timer >= TIME_READY_SET_GO:
            print("Background Noise: " + str(background_noise))
            print("Game started!")
            totalTime = time.perf_counter()
            start_green()
    elif mode == MODE_GREEN:
        time.sleep(0.01)
        #Add grace period so LED lighting changes don't affect motion
        if time.perf_counter() - timer > LEVELS[level][PARAM_MIN_GREEN_TIME]:
            motionL, motionR = detect_motion()
            motionThresh = get_motion_thresh()
            test_result = motion_test(motionL, motionR, motionThresh)
            if time.perf_counter() - timer > interval or test_result >= 0:
                #pygame.mixer.music.stop()
                set_color(COLOR_YELLOW)
                mode = MODE_YELLOW
                timer = time.perf_counter()
    elif mode == MODE_YELLOW:
        time.sleep(0.01)
        if time.perf_counter() - timer > LEVELS[level][PARAM_YELLOW_TIME]:
            pygame.mixer.music.stop()
            start_red()
    elif mode == MODE_RED:
        time.sleep(0.01)
        #Add grace period so LED lighting changes don't affect motion
        if time.perf_counter() - timer > TIME_GRACE_PERIOD:
            motionL, motionR = detect_motion()
            motionThresh = get_motion_thresh()
            if time.perf_counter() - timer > interval:
                snd_red.stop()
                start_green()
            else:
                test_result = motion_test(motionL, motionR, motionThresh)
                if test_result >= 0:
                    lose_game(test_result)
    elif mode == MODE_WIN:
        win_game()
