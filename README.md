# PepperChat

The code aims to give Pepper basic conversation abilities, this includes a speech recognition module, a conversational engine to formulate the answers and the speech synthesis.

This is a fork of Igor Lirussi's [Pepper Dialogue System](https://github.com/igor-lirussi/Dialogue-Pepper-Robot).

## Installation
With git bash you have to clone, possibly with SSH, the repository with the following command. <br>
**Pay attention to clone also the submodules with the --recurse-submodules or some parts of the project will miss**
```
git clone --recurse-submodules <repo_link>
```

## Setup

NaoQi is old and run on Python 2.7, it therefore takes a bit of manaul work to get it all set up. Here's a step by step guide for setup on Windows 11.

1. Install [Python 2.7](https://www.python.org/downloads/release/python-2718/). Select the 32 msi bit installer.
1. Add ```C:\Python27``` to the environment PATH.
1. Open a termiinal and verify that python refers to Python2.7
1. Install numpy using pip: ```python -m pip install numpy```
2. Install VS Code
3. Download and install [Choreographe 2.5.10.7](https://www.softbankrobotics.com/emea/en/support/pepper-naoqi-2-9/downloads-softwares/former-versions?os=45&category=108).
4. Download and extract [NaoQi Python SDK](https://www.softbankrobotics.com/emea/en/support/pepper-naoqi-2-9/downloads-softwares/former-versions?os=45&category=108) to a folder (pynaoqi-python2.7-2.5.7.1-win32-vs2013/lib) of your choice and add its path the PYTHONPATH environment variable in Windows. 
5. Check out this repository and open the folder in VS Code

## Run
Make sure you've gone through all steps in the Setup guide above beofre you start. 

Start Google's text to speech recognition servicefor Pepper by opening a terminal, change directory into ```./pepperspeechrecognition``` and execute ```python .\module_speechrecognition.py --pip pepper.local``` (where _pepper.local_ refers to your robot's ip).

Next, start the dialogue service by opening another terminal and executing ```python .\module_dialogue.py --pip 192.168.1.132```

Pepper should now be ready to chat!

## Dependencies <a class="anchor" id="dependencies"></a>
The __Speech Synthesis__ works with
* **Python 2.7** ,  because it uses
* [Pepper API (NAOqi 2.5) ](https://developer.softbankrobotics.com/pepper-naoqi-25/naoqi-developer-guide/naoqi-apis)

The __Speech Recognition__ module was built to be able to run ON Pepper computer (in the head) it's only dependencies are
* **Python 2.7** ,  because it uses
* [Pepper API (NAOqi 2.5) ](https://developer.softbankrobotics.com/pepper-naoqi-25/naoqi-developer-guide/naoqi-apis)
* **numpy**

## Built With

* Python 2.7.18

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments
* Erik Billing @ University of Skövde, Sweden - for adapting this library with improved dialogue design. 
* Igor Lirussi @ Cognitive Learning and Robotics Laboratory at Boğaziçi University, Istanbul - for releasing the base module on which this project is built. 
* Johannes Bramauer @ Vienna University of Technology - for the [PepperSpeechRecognition](https://github.com/JBramauer/pepperspeechrecognition)
* Anthony Zang (Uberi) and his [SpeechRecognition](https://github.com/Uberi/speech_recognition)
