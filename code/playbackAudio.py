import sys
import time
import wave
import pyaudio

audioPath = sys.argv[1]
startTime = float(sys.argv[2])

audioFile = wave.open(audioPath, 'rb')
audioSampleRate = audioFile.getframerate()

def audioCallback(in_data, frame_count, time_info, status):
    data = audioFile.readframes(frame_count)
    return (data, pyaudio.paContinue)

p = pyaudio.PyAudio()
stream = p.open(format=p.get_format_from_width(audioFile.getsampwidth()),
                channels=audioFile.getnchannels(),
                rate=audioSampleRate,
                output=True,
                stream_callback=audioCallback)
while stream.is_active():
    timeElapsed = time.time()-startTime
    audioFile.setpos(int(timeElapsed*audioSampleRate))
    time.sleep(10)
stream.close()
p.terminate()