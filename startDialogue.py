from pathlib import Path
import sys
import threading
import time

import dotenv

BASE_DIR = Path(__file__).resolve().parent
SPEECH_TO_TEXT_DIR = BASE_DIR / "micke" / "speech_to_text"
MICKE_DIR = BASE_DIR / "micke"

if str(SPEECH_TO_TEXT_DIR) not in sys.path:
    sys.path.insert(0, str(SPEECH_TO_TEXT_DIR))
if str(MICKE_DIR) not in sys.path:
    sys.path.insert(0, str(MICKE_DIR))

import pepper_command
from pepper_text_speaker import PepperTextSpeaker
import pcm_utils
import subtitles
from oaichat_integrated import OaiChatIntegrated, Query
import comm


dotenv.load_dotenv()


def main():
    system_prompt = (BASE_DIR / "pepper.prompt").read_text(encoding="utf-8").strip()
    system_say = (BASE_DIR / "pepper.text").read_text(encoding="utf-8").strip()

    command_sender = pepper_command.CommandSender()

    def init_robot():
        command_sender.send(pepper_command.ConfigSpeech(language="Swedish", animated=True))
        command_sender.send(pepper_command.ConfigAudio(output_volume=70))

    init_robot()
    pts = PepperTextSpeaker(
        command_sender=command_sender,
        subtitle_server=subtitles.SubtitleServer()
    )

    pts.push_text(system_say)

    def on_robot_state_change(state: comm.RobotState):
        print(state)
        if state.just_started:
            init_robot()
        pts.on_robot_state_change(state)
        if state.head_touched:
            oai.cancel_current()

    robot_state_listener = comm.RobotStateListener(on_robot_state_change)

    def on_query_update(query: Query):
        if query.done:
            print(query)

    intermediate_response_text_callback = pts.push_text
    oai = OaiChatIntegrated(
        system_prompt=system_prompt,
        query_update_callback=on_query_update,
        state_callback=print,
        intermediate_response_text_callback=intermediate_response_text_callback,
    )
    oai.silero.threshold = 0.5

    def muter():
        unmute_time = 0
        while True:
            if oai.state == oai.STATE_RECEIVING_RESPONSE or robot_state_listener.state.talking:
                unmute_time = time.time() + 0.2
            oai.set_listening(time.time() > unmute_time)
            time.sleep(0.1)

    threading.Thread(target=muter, daemon=True).start()
    pcm_utils.listen_on_local_mic(48000, [oai.push_pcm16_frames], channel_cnt=1)


if __name__ == "__main__":
    main()
