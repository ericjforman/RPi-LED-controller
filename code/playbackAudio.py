import sys
import time
import wave
import pyaudio

audioPath = sys.argv[1]
startTime = float(sys.argv[2])


print(f"  Playing back audio: {audioPath}...")

# TO DO: audio start is cut off - playback starts about 0.25 seconds into the file, how could that much time elapse?
#   (maybe it is the lengthy ALSA and jack error output...)

try:
    with wave.open(audioPath, 'rb') as file:
        audioFile = file
        audioSampleRate = audioFile.getframerate()

        def audioCallback(in_data, frame_count, time_info, status):
            data = audioFile.readframes(frame_count)
            # If len(data) is less than requested frame_count, PyAudio automatically
            # assumes the stream is finished, and the stream stops.
            return (data, pyaudio.paContinue)

        p = pyaudio.PyAudio()

        # Open stream using callback
        stream = p.open(format=p.get_format_from_width(audioFile.getsampwidth()),
                        channels=audioFile.getnchannels(),
                        rate=audioSampleRate,
                        output=True,
                        stream_callback=audioCallback)

        # Wait for stream to finish
        while stream.is_active():
            timeElapsed = time.time()-startTime
#           print(f"  {time.time()} - {startTime} = ")
            print(f"  {timeElapsed} * {audioSampleRate} = {int(timeElapsed*audioSampleRate)}")
            audioFile.setpos(int(timeElapsed*audioSampleRate))
            time.sleep(10)

        stream.close()
        p.terminate()

except FileNotFoundError:
    print(f"Audio file {audioPath} not found!")
except PermissionError:
    print("Permission denied to access audio file!")
except Exception as e:
    print("An audio file error occurred: ", e)


"""
# previous code, without error handling:

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
"""