import traceback
import dotenv
dotenv.load_dotenv()
import threading, time, json, os
from datetime import datetime

import oai_dialogue.pepper_command as pepper_command
from oai_dialogue.speech_to_text.pepper_text_speaker import PepperTextSpeaker
from oai_dialogue.speech_to_text import pcm_utils
from oai_dialogue.speech_to_text import subtitles
from oai_dialogue.speech_to_text.oaichat_integrated import OaiChatIntegrated, Query
import oai_dialogue.comm as comm

dotenv.load_dotenv(os.getenv('DIALOGUE_ENV', 'dialogue.env'))

def main():
    command_sender = pepper_command.CommandSender()
    
    def init_robot():
        command_sender.send(pepper_command.ConfigSpeech(language=os.getenv('LANGUAGE', 'Swedish'), animated=True))
        command_sender.send(pepper_command.ConfigAudio(output_volume=70))
        wifi_ssid = os.getenv('TABLET_WIFI_SSID')
        if wifi_ssid:
            print("Configuring tablet wifi:", wifi_ssid)
            command_sender.send(pepper_command.ConfigTabletWifi(
                ssid=wifi_ssid,
                pwd=os.getenv('TABLET_WIFI_PWD', ''),
                security_type=os.getenv('TABLET_WIFI_SECURITY', 'wpa')
            ))
    
    init_robot()
    pts = PepperTextSpeaker(
        command_sender=command_sender,
        subtitle_server=subtitles.SubtitleServer()
    )

    #pts.push_text("Det enda ja äter, är sill o puttäter. Sillsillsill och puttputtputtäter.")
    pts.push_text(os.getenv('SAY', ''))
    def on_robot_state_change(state:comm.RobotState):
        print(state)
        if state.just_started:
            init_robot()
        pts.on_robot_state_change(state)
        if state.head_touched:
            oai.cancel_current()
    robot_state_listener = comm.RobotStateListener(on_robot_state_change)
    
    logdir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logdir, exist_ok=True)
    logfile = os.path.join(logdir, datetime.now().strftime('dialogue_%Y-%m-%d_%H%M%S.log'))
    print('Logging to', logfile)

    def log_query(query:Query):
        entry = {
            'time': datetime.fromtimestamp(query.start_time).isoformat(),
            'user': query.query_text.strip(),
            'response': query.response_text.strip(),
            'duration': round(query.duration, 2)
        }
        with open(logfile, 'a', encoding='utf-8') as f:
            json.dump(entry, f, ensure_ascii=False)
            f.write(',\n')

    def on_query_update(query:Query):
        if query.query_text and not query.response_text:
            print("USER:", query.query_text.strip())
        if query.done:
            print(query)
            log_query(query)
    
    intermediate_response_text_callback = pts.push_text
    oai = OaiChatIntegrated(
        system_prompt=os.getenv('PROMPT', ''),
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
