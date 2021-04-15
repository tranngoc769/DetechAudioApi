from tempfile import NamedTemporaryFile
import os
import os.path
import audioop
from pydub import AudioSegment
from pydub.utils import mediainfo
from flask import Flask, request, jsonify
app = Flask(__name__)
from config import *
import wave
def convertToWav(src, dst,bitrate="256k" ):
    sound = AudioSegment.from_mp3(src)
    sound.export(dst, format="wav", bitrate=bitrate)
def check_voice_mail(sample_path, compare_path):
    sample = wave.open(sample_path, 'r')
    compare = wave.open(compare_path, 'r')
    sample_frame = sample._nframes
    compare_frame = compare._nframes
    if (sample_frame > compare_frame):
        sample_frame = compare_frame
    if sample.readframes(sample_frame) == compare.readframes(sample_frame):
        return True
    else:
        return False
def downsampleWav(src, dst, outrate=16000):
    with wave.open(src, "rb") as wave_file:
        frame_rate = wave_file.getframerate()
        inchannels=wave_file.getnchannels()
        outchannels=inchannels
    if not os.path.exists(src):
        print('Source not found!')
        return False
    try:
        s_read = wave.open(src, 'r')
        s_write = wave.open(dst, 'w')
    except:
        print('Failed to open files!')
        return False

    n_frames = s_read.getnframes()
    data = s_read.readframes(n_frames)
    try:
        converted = audioop.ratecv(data, 2, inchannels, frame_rate, outrate, None)
        if outchannels == 1 & inchannels != 1:
            converted[0] = audioop.tomono(converted[0], 2, 1, 0)
    except Exception as errr:
        print('Failed to downsample wav')
        print(errr)
        return False

    try:
        s_write.setparams((outchannels, 2, outrate, 0, 'NONE', 'Uncompressed'))
        s_write.writeframes(converted[0])
    except:
        print('Failed to write wav')
        return False

    try:
        s_read.close()
        s_write.close()
    except:
        print('Failed to close wav files')
        return False
    return True
def convertMp3ToWav16(src, dst):     
    temp=os.path.dirname(src)+"/temp.wav"                                                             
    convertToWav(src, temp)
    status = downsampleWav(temp, dst, outrate=16000)
    return status
def ConvertAudioToWav(path, file_extension):
    status = True
    temp_audio_path     =   path 
    if (file_extension.lower()==".mp3"):
            #chuyen mp3->wav 16000Hz
        src= temp_audio_path
        dst=src.replace("mp3", "wav")
        status = convertMp3ToWav16(src, dst)
        path = dst
    if (file_extension.lower()==".wav"):
        status = downsampleWav(path,path)
    return status, path
def getExtension(path):
    return path.split(".")[-1]
@app.route('/voicemail', methods=['POST'])
def compare():
    voicemail_path = ""
    voice_path = ""
    if 'voicemail' not in request.files and 'voice' not in request.files:
        return jsonify({'code' : 404,'result': 'erro', 'message':'Required voicemail and voice file'})
    # 
    voicemail_file = request.files['voicemail']
    voice_file = request.files['voice']
    _, voice_file_extension = os.path.splitext(voice_file.filename)
    _, voicemail_file_extension = os.path.splitext(voicemail_file.filename)
    if voice_file_extension not in ALLOWS_EXTENSION and voicemail_file_extension not in ALLOWS_EXTENSION:
        return jsonify({'code' : 404,'result': 'erro', 'message':'File extension is not allowed'})
    # 
    with NamedTemporaryFile(prefix="audio_",suffix=voicemail_file_extension, dir='/tmp', delete=False) as voicemail_file_audio:
        voicemail_file.save(voicemail_file_audio.name)
        voicemail_path = voicemail_file_audio.name
    with NamedTemporaryFile(prefix="audio_",suffix=voice_file_extension, dir='/tmp', delete=False) as voice_file_audio:
        voice_file.save(voice_file_audio.name)
        voice_path = voice_file_audio.name
    status, voicemail_path = ConvertAudioToWav(voicemail_path, voicemail_file_extension)
    if status == False:
        return jsonify( {'code' : 404,'result': 'erro', 'message':'Failed to convert audio'})
    status, voice_path = ConvertAudioToWav(voice_path, voice_file_extension)
    if status == False:
        return jsonify( {'code' : 404,'result': 'erro', 'message':'Failed to convert audio'})
    result = check_voice_mail(voicemail_path, voice_path)
    try:
        os.remove(voice_path)
        os.remove(voicemail_path)
    except:
        pass
    return jsonify( {'code' : 200,'result': 'success', 'message':result})
if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8000,debug=True)