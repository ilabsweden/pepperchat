import json
try:
    from micke import comm, udp
except:
    import comm, udp

_command_types = []
class Command(object):
    def __init__(self):
        self.command = self.__class__.__name__
        
class ConfigTabletWifi(Command):
    def __init__(self, ssid, pwd, security_type="wep"):
        # type (str, str, str) -> SetWifiCredentials
        super(ConfigTabletWifi, self).__init__()
        self.ssid = ssid
        self.pwd = pwd
        self.security_type = security_type
_command_types.append(ConfigTabletWifi)

class OpenUrlOnTablet(Command):
    def __init__(self, url):
        # type: (str) -> OpenUrlOnTablet
        super(OpenUrlOnTablet, self).__init__()
        self.url = url
_command_types.append(OpenUrlOnTablet)
        
class ConfigSpeech(Command):
    def __init__(self, language, animated):
        # type: (str, bool) -> ConfigSpeech
        super(ConfigSpeech, self).__init__()
        self.language = language
        self.animated = animated
_command_types.append(ConfigSpeech)

class Say(Command):
    def __init__(self, text):
        # type: (str) -> Say
        super(Say, self).__init__()
        self.text = text
_command_types.append(Say)

class ConfigAudio(Command):
    def __init__(self, output_volume):
        # type: (int) -> ConfigAudio
        super(ConfigAudio, self).__init__()
        self.output_volume = output_volume
_command_types.append(ConfigAudio)

def parse_json(jsn):
    dct = json.loads(jsn)
    command_name = dct.get("command")
    del dct["command"]
    for type in _command_types:
        if command_name == type.__name__:
            initstr = ",".join([key + "="+ (("\"" + val + "\"") if isinstance(val,str) else str(val)) for key,val in dct.items()])
            command = eval(command_name + "(" + initstr + ")")
            return command

class CommandSender(udp.UdpSender):
    def __init__(self):
        super(CommandSender, self).__init__(comm.COMMAND_UDP_PORT, comm.COMMAND_UDP_IP)
    def send(self, command):
        # type: (Command) -> None
        self.send_data(json.dumps(command.__dict__).encode("utf-8"))

class CommandReceiver(udp.UdpReceiver):
    def __init__(self, callback):
        # type: (callable[[Command], None]) -> CommandReceiver
        def cbck(data):
            command = parse_json(data.decode("utf-8"))
            if command:
                callback(command)

        super(CommandReceiver, self).__init__(cbck, comm.COMMAND_UDP_PORT, comm.COMMAND_UDP_IP)
        self.start()

