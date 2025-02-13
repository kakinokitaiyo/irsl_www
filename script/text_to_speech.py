import os
import azure.cognitiveservices.speech as speechsdk

def text_to_speech(in_text):
    # This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"
    speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), region=os.environ.get('SPEECH_REGION'))
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

    # The language of the voice that speaks.
    # 音声の種類を選べる: https://learn.microsoft.com/ja-jp/azure/cognitive-services/speech-service/language-support?tabs=tts#supported-languages
    #speech_config.speech_synthesis_voice_name='en-US-JennyNeural' ## 英語
    speech_config.speech_synthesis_voice_name='ja-JP-KeitaNeural' ## 日本語

    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    # Get text from the console and synthesize to the default speaker.
    #print("Enter some text that you want to speak >")
    #text = input()

    speech_synthesis_result = speech_synthesizer.speak_text_async(in_text).get()

    if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized for text [{}]".format(text))

    elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_synthesis_result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            if cancellation_details.error_details:
                print("Error details: {}".format(cancellation_details.error_details))
                print("Did you set the speech resource key and region values?")
