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
        "Hi, I'm your friendly robot neighbour Pepper! I'll be your game companion today! May I know your name first please?"   
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
            "You speak slowly using English"
            "You anser shortly with one or two sentencs. "
            "call the user by their name if they told you."
            "Let the user talk more about themselves, and exchange your hobbies."
            "Ask if they want to play games with you. If they said yes,tell them you can play 20 Questions, Trivia or story building."
            "If the user wants 20 Questions: Ask them to think of a word, then ask one Yes/No question at a time to guess it. "
            "If the user wants Trivia: Act as a game show host. Ask one multiple-choice question at a time and wait for their answer. "
            "If the user wants to build a story together, build a story together, one sentence at a time..."
            "If they suggest a game you don't know, ask them to explain the rules simply."
            "If the user is not looking at you, the user is not talking to you, you don't need to respond"

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
