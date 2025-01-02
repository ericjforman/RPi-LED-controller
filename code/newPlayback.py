import sys
import time
import threading
import subprocess
from rpi_ws281x import PixelStrip, Color

class LEDPlayback:
    def __init__(self, filePath:str):
        print(f"  Playing back LED data: {filePath}...")
        metadataFile = open(filePath + "/metadata.txt")
        self.universeCount =        int(metadataFile.readline().split("#")[0].strip())
        self.stripCount =           int(metadataFile.readline().split("#")[0].strip())
        self.ledCounts =            [int(x) for x in metadataFile.readline().split("#")[0].strip().split(", ")]
        self.universe2strip =       [int(x) for x in metadataFile.readline().split("#")[0].strip().split(", ")]
        self.universe2substrip =    [int(x) for x in metadataFile.readline().split("#")[0].strip().split(", ")]
        self.strips = [None] * self.stripCount
        self.playbackFiles = [None] * self.universeCount
        self.playbackFrame = [0] * self.universeCount
        self.playbackDones = 0
        self.finished = True
        self.startTime = 0
        self.audioPlaybackProcess = None
        self.initStrips()
        self.openFiles(filePath)

    def initStrips(self):
        strip2GPIO = [18, 19, 21, 10]
        strip2Channel = [0, 1, 0, 0]  # NOTE: this should be called stripOutputs to avoid confusion with DMX channels
        for strip in range(self.stripCount):
            self.strips[strip] = PixelStrip(self.ledCounts[strip],  # PIXEL COUNT
                                        strip2GPIO[strip],          # DOUT PIN (10 for SPI)
                                        800000,                     # DOUT FREQUENCY (800khz is standard)
                                        10,                         # DMA CHANNEL (10 is a safe bet)
                                        False,                      # DOUT POLARITY (True to invert signal)
                                        255,                        # LED BRIGHTNESS
                                        strip2Channel[strip])       # LED OUTPUT
            self.strips[strip].begin()

    def openFiles(self, path:str):
        for universe in range(self.universeCount):
            self.playbackFiles[universe] = open(f"{path}/U{universe}.txt")

    def parseLine(self, universe:int):
        rawLine = self.playbackFiles[universe].readline()
        if rawLine == '': return False
        cleanLine = rawLine.strip().split()
        frameData = [float(cleanLine[0])]
        for i in range(1, len(cleanLine)):
            frameData.append(int(cleanLine[i]))
        return frameData

    def playCallback(self, universe:int):
#        print("  playCallback start")
        if self.finished: return
        frameData = self.parseLine(universe)
        if frameData == False:
            self.playbackDones += 1
            if self.playbackDones == self.universeCount:
                print("  no frame data, terminating audio.")
                self.audioPlaybackProcess.terminate()
                self.finished = True
            return
        for ledCount in range(170):
            if ledCount >= self.ledCounts[self.universe2strip[universe]]: break
            dataIndex = (ledCount*3)+1
            pixColor = Color(frameData[dataIndex], 
                             frameData[dataIndex+1], 
                             frameData[dataIndex+2])
            stripIndex = 170*self.universe2substrip[universe] + ledCount
            self.strips[self.universe2strip[universe]].setPixelColor(stripIndex, pixColor)
        self.playbackFrame[universe]+=1
        # NOTE: this always calls back twice before audio is started, something not quite right
        # NOTE: is this why audio playback skips tiny bit at start? 
        frameTimeStamp = frameData[0]
#        print(f"  {time.time()} - {self.startTime} = ")
        timeWait = frameTimeStamp - (time.time() - self.startTime)
#        print(f"  timeWait: {timeWait}")
        if timeWait < 0: timeWait = 0
        threading.Timer(timeWait, lambda: self.playCallback(universe)).start()
 #       print("  playCallback done")

    def refreshStrips(self):
        for strip in self.strips:
            strip.show()

    def play(self):
        self.finished = False
        self.playbackDones = 0
        self.startTime = time.time()        # used to be AFTER audioPlaybackProcess, doublecheck this doesn't cause other issues...
        # TODO: make file name based on LED data save, or based on argument in metadata.txt
        audioPlaybackArgs = ['./audio/TestAudio.wav', str(self.startTime)]
        # TODO: make path work for any venv name
        self.audioPlaybackProcess = subprocess.Popen(['./venv/bin/python3', './code/playbackAudio.py'] + audioPlaybackArgs)
        #self.startTime = time.time()       # moved above, because otherwise startTime is 0 for playbackAudio, which throws errors when syncing
        for universe in range(self.universeCount):
            self.playbackFiles[universe].seek(0)
 #           print("before playCallback")
            self.playCallback(universe)
 #           print("after playCallback")

    def stop(self):
        self.finished = True
        self.audioPlaybackProcess.terminate()

    def clear(self):                        # TO DO: make this function work for all files
        for universe in range(self.universeCount):
            for ledCount in range(170):
                if ledCount > self.ledCounts[self.universe2strip[universe]]: break
                dataIndex = (ledCount*3)+1
                pixColor = Color(0,0,0)
                stripIndex = 170*self.universe2substrip[universe] + ledCount
                self.strips[self.universe2strip[universe]].setPixelColor(stripIndex, pixColor)
        self.refreshStrips()


    def deinit(self):
        self.stop()
        time.sleep(0.2)
        for universe in range(self.universeCount):
            self.playbackFiles[universe].close()
        self.clear()


if __name__ == "__main__":
    playback = LEDPlayback("./saves/liveTest")
    playback.play()

    try:
        while True:
            playback.refreshStrips()
            if (playback.finished):
                print("test looping...")
                playback.play()                 # loop
    except (KeyboardInterrupt, SystemExit):
        playback.deinit()
        sys.exit()

#FOR LATER!
#Make sure to hook a signal handler for SIGKILL to do cleanup. From the handler make sure to call ws2811_fini(). 
#It'll make sure that the DMA is finished before program execution stops and cleans up after itself.
