import traceback
import dotenv
import __parentdir

import pepper_command
from pepper_text_speaker import PepperTextSpeaker
import pcm_utils
import subtitles
dotenv.load_dotenv()
import threading, time

from oaichat_integrated import OaiChatIntegrated, Query

import comm

def main():
    command_sender = pepper_command.CommandSender()
    command_sender.send(pepper_command.ConfigSpeech(language="Swedish", animated=True))
    command_sender.send(pepper_command.ConfigAudio(output_volume=70))
    pts = PepperTextSpeaker(
        command_sender=command_sender,
        subtitle_server=subtitles.SubtitleServer()
    )
    pts.push_text("Det enda ja äter, är sill o puttäter. Sillsillsill och puttputtputtäter.")
    def on_robot_state_change(state:comm.RobotState):
        print(state)
        pts.on_robot_state_change(state)
        if state.head_touched:
            oai.cancel_current()
    robot_state_listener = comm.RobotStateListener(on_robot_state_change)
    
    def on_query_update(query:Query):
        if query.done:
            print(query)
    
    intermediate_response_text_callback = pts.push_text
    oai = OaiChatIntegrated(

        system_prompt=(
            "Du agerar som den sociala roboten Pepper. "
            "Du svarar kortfattat med en eller två meningar. "
            "Vi befinner oss i Skaraborgs Hälsoteknikcentrum. "
            "Idag har vi besökare som har kommit för att träffa dig. "
        ),
        
        query_update_callback = on_query_update,
        state_callback=print,
        intermediate_response_text_callback=intermediate_response_text_callback
    )
    oai.silero.threshold = .8
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
