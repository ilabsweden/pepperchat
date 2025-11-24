import traceback
import dotenv
import keyboard
import __parentdir

import pepper_command
from pepper_text_speaker import PepperTextSpeaker
import pcm_utils
import subtitles
dotenv.load_dotenv()
import os, json, base64, threading, queue, time
import numpy as np

from micke.speech_to_text.oaichat_integrated import OaiChatIntegrated, Query

import comm

class PepperSim:
    def __init__(self):
        self.audio_player = pcm_utils.AsyncAudioPlayer(16000)
        self.state_reporter = comm.RobotStateReporter()
        
        def loop():
            while True:
                head_touched = keyboard.is_pressed('h')
                if head_touched:
                    self.audio_player.clear_queue()
                self.state_reporter.report_talking(self.audio_player.is_playing())
                self.state_reporter.report_head_touched(head_touched)
                time.sleep(.1)
        threading.Thread(target=loop, daemon=True).start()

    def push_pcm16_frames(self, sample_rate:int, channel_cnt:int, frames:np.ndarray):
        self.audio_player.push_pcm16_frames(sample_rate, channel_cnt, frames)

        

def main():
    # pepper_sim: PepperSim = None
    # pepper_sim = PepperSim()
    command_sender = pepper_command.CommandSender()
    command_sender.send(pepper_command.ConfigSpeech(language="Swedish", animated=True))
    command_sender.send(pepper_command.ConfigAudio(output_volume=70))
    pepper_speak = PepperTextSpeaker(
        command_sender=command_sender,
        subtitle_server=subtitles.SubtitleServer()
    )

    def on_robot_state_change(state:comm.RobotState):
        print(state)
        pepper_speak.on_robot_state_change(state)
        if state.head_touched:
            oai.cancel_current()
    robot_state_listener = comm.RobotStateListener(on_robot_state_change)
    
    def on_query_update(query:Query):
        if query.done:
            print(query)
    # assp = subtitles.AudioSynchronizedSubtitleProvider()
    # intermediate_response_text_callback = assp.push_text
    
    intermediate_response_text_callback = pepper_speak.push_text

    def on_response_audio(sample_rate:int, channel_cnt:int, frames:np.ndarray):
        return
        pepper_sim.push_pcm16_frames(sample_rate, channel_cnt, frames)
        assp.push_pcm16_frames(sample_rate, channel_cnt, frames)

    oai = OaiChatIntegrated(
        system_prompt=(
            "Du är roboten Pepper."
            "Du är glad och artig."
            "Du pratar svenska. Långsamt, tydligt och kortfattat."
        ),
        voice=None,
        query_update_callback = on_query_update,
        response_audio_callback = on_response_audio,
        state_callback=print,
        intermediate_response_text_callback=intermediate_response_text_callback
    )
    def muter():
        unmute_time = 0
        while True:
            if oai.state == oai.STATE_RECEIVING_RESPONSE or robot_state_listener.state.talking:
                unmute_time = time.time() + .2
            oai.set_listening(time.time() > unmute_time)
            time.sleep(.1)
    threading.Thread(target=muter, daemon=True).start()
    pcm_utils.listen_on_local_mic(48000,[oai.push_pcm16_frames], channel_cnt=1)


if __name__ == "__main__":

    main()
