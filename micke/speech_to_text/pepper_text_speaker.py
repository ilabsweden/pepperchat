import traceback
import __parentdir
import pepper_command
import subtitles
import threading
import time
import comm

class PepperTextSpeaker:
    class Worker:
        def __init__(self, pepper_speak:"PepperTextSpeaker"):
            self.pepper_speak = pepper_speak
            self.sentences = []
            self.unsentenced_text = ""
            self.robot_talking = False
            self.last_text_receive_time = 0
            self.done = False
            def loop():
                next_sentence_idx = 0
                while not self.done:
                    if self.last_text_receive_time > 0:
                        sentence_cnt = len(self.sentences)
                        got_all_text = time.time() - self.last_text_receive_time > .5
                        if sentence_cnt <= next_sentence_idx:
                            if got_all_text:
                                if self.unsentenced_text:
                                    self.sentences.append(self.unsentenced_text)
                                    self.unsentenced_text = ""
                                else:
                                    self.done = True

                        elif not self.robot_talking:
                            sentences = self.sentences.copy()
                            sentence = sentences[next_sentence_idx]
                            pepper_speak.say(sentence)
                            print("say:",sentence)
                            next_sentence_idx += 1
                            if pepper_speak.subtitle_server:
                                pepper_speak.subtitle_server.set_text("".join(sentences[:next_sentence_idx]))
                    time.sleep(.2)
            threading.Thread(target=loop, daemon=True).start()
        
        def push_text(self, text:str):
            self.last_text_receive_time = time.time()
            self.unsentenced_text += text
            if sentences := subtitles.split_into_sentences(self.unsentenced_text):
                self.unsentenced_text = self.unsentenced_text.removeprefix("".join(sentences))
                self.sentences += sentences

    def __init__(self, command_sender:pepper_command.CommandSender, subtitle_server:subtitles.SubtitleServer=None):
        self.command_sender = command_sender
        if subtitle_server:
            command_sender.send(pepper_command.OpenUrlOnTablet(subtitle_server.url))
        self.subtitle_server = subtitle_server
        self.worker = PepperTextSpeaker.Worker(self)

    def say(self, text:str):
        self.command_sender.send(pepper_command.Say(text))

    def push_text(self, text:str):
        if self.worker.done:
            self.worker = PepperTextSpeaker.Worker(self)
        self.worker.push_text(text)

    def on_robot_state_change(self, state:comm.RobotState):
        self.worker.robot_talking = state.talking
        if state.head_touched:
            self.worker.done=True


