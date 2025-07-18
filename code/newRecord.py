import os
import sys
import time
import math
from rpi_ws281x import PixelStrip, Color
from stupidArtnet import StupidArtnetServer
# from newPlayback import clear  # this doesn't work because clear is inside class LEDPlayback

# one DMX universe = 512 channels = 170 RGB pixels max (last 2 channels unused)
# initialize up to 4 LED outputs/strips of up to 680 pixels each (4 universes each)

class LEDRecord:
    def __init__(self, ledCounts:int = [20], recTriggerVal:int = 0):
        # Input parameter sanity checks
        if len(ledCounts) > 4:
            print("  Unable to init more than 4 strips! Initing first 4 strips only.")
            ledCounts = ledCounts[:4]
        for i, count in enumerate(ledCounts):
            if count > 680:
                print(f"  Maximum of 680 LEDs per strip! LED count for strip {i} clipped to 680.")
                ledCounts[i] = 680
        print(f"  Record trigger (channel 512): {recTriggerVal}")
        if (recTriggerVal > 255 or recTriggerVal < 0):
            print(f"  Record trigger value of {recTriggerVal} is invalid. Setting to default of 0.")
            recTriggerVal = 0

        # Init data members
        self.ledCounts = ledCounts
        self.stripCount = len(ledCounts)
        self.strips = [None] * self.stripCount
        self.universe2strip = []
        self.universe2substrip = []

        # Allocate universes to strips
        for i, count in enumerate(self.ledCounts):
            if count < 170:
                universesNeeded = 1
            else:
                universesNeeded = int(math.ceil(count/170))
            self.universe2strip += [i] * universesNeeded
            self.universe2substrip += range(universesNeeded)
        self.universeCount = len(self.universe2strip)
        self.artnetServer = StupidArtnetServer()
        self.universeListeners = [None] * self.universeCount
        self.recTriggerVal = recTriggerVal
        self.recordFiles = [None] * self.universeCount
        self.recording = False
        self.postStartFlag = False
        self.startTime = 0

        # Init hardware
        self.initStrips()
        self.initListeners()


    def initStrips(self):
        strip2GPIO = [18, 19, 21, 10]    # RPi Zero pins (NOTE: channel2GPIO would be a clearer name)
        strip2Channel = [0, 1, 0, 0]     # ch0 uses pin 18, ch1 uses pin 19, ch2 and ch3 not used (# NOTE: this should be called strip2Output to avoid confusion)
        for strip in range(self.stripCount):
            self.strips[strip] = PixelStrip(self.ledCounts[strip],  # PIXEL COUNT
                                        strip2GPIO[strip],          # DOUT PIN (10 for SPI)
                                        800000,                     # DOUT FREQUENCY (800khz is standard)
                                        10,                         # DMA CHANNEL (10 is a safe bet)
                                                                    # NOTE: need diff DMA channel for addt'l outputs?
                                        False,                      # DOUT POLARITY (True to invert signal)
                                        255,                        # LED BRIGHTNESS
                                        strip2Channel[strip])       # LED OUTPUT
            self.strips[strip].begin()

    def initListeners(self):
        for i in range(self.universeCount):
            self.universeListeners[i] = self.artnetServer.register_listener(i, callback_function = lambda x, i=i:self.recordCallback(x, i))
            
    def refreshStrips(self):
        for strip in self.strips:
            strip.show()


    def recordCallback(self, data, universe:int):
        if not self.recording: return
        if universe == 0 and data[511] == self.recTriggerVal:       # DMX Channels numbered 1-512, but data is 0-511
            if not self.postStartFlag: 
                print("  Got trigger! Toggled recording start...")
                self.startTime = time.time()
            self.postStartFlag = True
        if universe == 0 and data[511] != self.recTriggerVal:
            if self.postStartFlag: 
                print("  Trigger removed! Toggled recording end...")
                self.recording = False
            self.postStartFlag = False
        if not self.postStartFlag: return
        self.recordFiles[universe].write(f'{time.time()-self.startTime} ')      # frame time stamp
        for ledCount in range(170):
            if ledCount >= self.ledCounts[self.universe2strip[universe]]: break      # make sure this writes all pixels, i.e. should be > ledCounts
            dataIndex = ledCount*3
            pixR, pixG, pixB = data[dataIndex], data[dataIndex+1], data[dataIndex+2]
            self.recordFiles[universe].write(f'{pixR} {pixG} {pixB} ')
            stripIndex = 170*self.universe2substrip[universe] + ledCount
            self.strips[self.universe2strip[universe]].setPixelColor(stripIndex, Color(pixR, pixG, pixB))
        self.recordFiles[universe].write(f'\n')

    def record(self, saveName:str, saveDir:str = "./saves/"):
        try:
            os.mkdir(f"{saveDir}/{saveName}/")
        except:
            print(f"  Save file with name {saveName} in {saveDir} already exists! Aborting...")
            return
        for universe in range(self.universeCount):
            dir = f"{saveDir}/{saveName}/"
            self.recordFiles[universe] = open(f"{dir}/U{universe}.txt", "w+")
        metadataFile = open(f"{dir}/metadata.txt", "w+")
        metadataFile.write(f"{self.universeCount} #UNIVERSE COUNT\n")
        metadataFile.write(f"{self.stripCount} #STRIP COUNT\n")
        metadataFile.write(f"{', '.join(str(count) for count in self.ledCounts)} #LED COUNTS\n")
        metadataFile.write(f"{', '.join(str(strip) for strip in self.universe2strip)} #UNIVERSE 2 STRIP\n")
        metadataFile.write(f"{', '.join(str(substrip) for substrip in self.universe2substrip)} #UNIVERSE 2 SUBSTRIP\n")
        metadataFile.close()
        print("  Enabled recording, waiting for trigger in universe 0, channel 512...")
        self.startTime = time.time()
        self.recording = True

    def stopRecord(self):
        self.recording = False
        self.postStartFlag = False
        for i in range(self.universeCount):
            try:
                self.recordFiles[i].close()
            except:
                print("  No open files to close!")

    def clear(self):                # TO DO: make this function work for all files
        for universe in range(self.universeCount):
            for ledCount in range(170):
                if ledCount > self.ledCounts[self.universe2strip[universe]]: break
                dataIndex = (ledCount*3)+1
                pixColor = Color(0,0,0)
                stripIndex = 170*self.universe2substrip[universe] + ledCount
                self.strips[self.universe2strip[universe]].setPixelColor(stripIndex, pixColor)
        self.refreshStrips()

    def deinit(self):
        self.stopRecord()
        time.sleep(0.2)
        del self.artnetServer
        self.clear()


if __name__ == "__main__":
    recorder = LEDRecord([20])
    recorder.record("liveTest")

    try:
        while True:
            recorder.refreshStrips()
            time.sleep(0.1)     # show slower updates to make sure record doesn't miss any data
    except (KeyboardInterrupt, SystemExit):
        recorder.deinit()
        sys.exit()


#FOR LATER!
#Make sure to hook a signal handler for SIGKILL to do cleanup. From the handler make sure to call ws2811_fini(). 
#It'll make sure that the DMA is finished before program execution stops and cleans up after itself.
