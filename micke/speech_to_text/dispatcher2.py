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
    
    def init_robot():
        command_sender.send(pepper_command.ConfigSpeech(language="English", animated=True))
        command_sender.send(pepper_command.ConfigAudio(output_volume=100))
    
    init_robot()
    pts = PepperTextSpeaker(
        command_sender=command_sender,
        subtitle_server=subtitles.SubtitleServer()
    )

    #pts.push_text("Det enda ja äter, är sill o puttäter. Sillsillsill och puttputtputtäter.")
    pts.push_text(
        "So let's play 20 questions. Think about a word and I will try to figure out which one."
    )
    def on_robot_state_change(state:comm.RobotState):
        print(state)
        if state.just_started:
            init_robot()
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
            "Act like the social robot Pepper. "
            "You anser shortly with one or two sentencs. "
            "I would like you to play 20 questions with me.  "
            "Start by asking me to think about a word and then follow up with questions so that you can guess which word it is."

        ),
        
        query_update_callback = on_query_update,
        state_callback=print,
        intermediate_response_text_callback=intermediate_response_text_callback
    )
    oai.silero.threshold = .5
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
