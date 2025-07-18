import sys, time, os, glob
from datetime import datetime
import RPi.GPIO as GPIO
from newPlayback import LEDPlayback
from newRecord import LEDRecord

DEBOUNCE_TIME = 0.5
GPIO_RECORD = 17
GPIO_PLAY = 27
# NOTE: use global variable for # of LEDs? Or read from text config file?

GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_RECORD, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(GPIO_PLAY,   GPIO.IN, pull_up_down=GPIO.PUD_UP)

mode = "Idle"

try:
    while True:
        if mode == "Idle":
            time.sleep(DEBOUNCE_TIME)
            print("LED Controller idle\nWaiting for button press...")
            while True:
                if not GPIO.input(GPIO_RECORD): 
                    # if necessary? if (GPIO.input(GPIO_RECORD) == 0):
                    mode = "Record"
                    break
                if not GPIO.input(GPIO_PLAY): 
                    mode = "Playback"
                    break
        elif mode == "Record":
            time.sleep(DEBOUNCE_TIME)
            print("Recording...")
            saveName = datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_save"
            recorder = LEDRecord([20])    # number of LED pixels on output 0
            recorder.record(saveName, './saves/')
            while True:
                recorder.refreshStrips()
                time.sleep(0.1)
                if not GPIO.input(GPIO_RECORD):
                    recorder.deinit()
                    del recorder
                    mode = "Idle"
                    break
        elif mode == "Playback":
            time.sleep(DEBOUNCE_TIME)
            print("Playback...")
            folders = glob.glob("./saves/*_save/")
            if folders:
                newestFolder = max(folders, key=os.path.getctime)
            #TO DO: error check if newestFolder doesn't exist
            playback = LEDPlayback(newestFolder)
            playback.play()
            while True:
                playback.refreshStrips()
                if (playback.finished):
                    playback.play()
                if not GPIO.input(GPIO_PLAY):
                    playback.deinit()
                    del playback
                    mode = "Idle"
                    break
        else:
            print(f"Invalid mode {mode}!")
            mode = "Idle"
except (KeyboardInterrupt, SystemExit):
    if mode == "Record":
        pass
    if mode == "Playback":
        playback.deinit()
        del playback
    sys.exit()
except Exception as e:
    print("Unknown error: ")
    print(e)
    if mode == "Record":
        pass
    if mode == "Playback":
        playback.deinit()
        del playback
    sys.exit()

#FOR LATER!
#Make sure to hook a signal handler for SIGKILL to do cleanup. From the handler make sure to call ws2811_fini(). 
#It'll make sure that the DMA is finished before program execution stops and cleans up after itself.
