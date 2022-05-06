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
Just control the [Dependencies](#dependencies), create an Anaconda environment or check in your system if everything is installed.


## Run
**Follow the steps in the notebook [Dialogue-Pepper.ipynb](Dialogue-Pepper.ipynb)** and
REMEMBER TO TURN ON THE RECOGNITION SERVICE with a shell in the speech-recognition folder. If the folder is empty probably you didn't clone with the submodules commands. <br> Use python 2.7, or activate the Anaconda environment, and run the service:
 ```
python module_speechrecognition.py --pip (your robot IP)
```
or, if you want to run the speech recognition service on the robot,
everything you need should already be installed, simply clone the pepperspeechrecognition folder to your robot, ssh into it and run:
 ```
python module_speechrecognition.py
```
## Video of the Result
[![Pepper Dialogue](http://i3.ytimg.com/vi/wBcfLlm5Hnc/maxresdefault.jpg)](https://youtu.be/wBcfLlm5Hnc "Pepper Dialogue Video")

## Run conversational engine locally
to run the conversational engine for manual tests execute the following command in a shell:
 ```
java -cp lib/Ab.jar Main bot=en
```
## Dependencies <a class="anchor" id="dependencies"></a>
The __Speech Synthesis__ works with
* **Python 2.7** ,  because it uses
* [Pepper API (NAOqi 2.5) ](https://developer.softbankrobotics.com/pepper-naoqi-25/naoqi-developer-guide/naoqi-apis)


The __Conversational Engine__ works with
* **Java** (because no AIML-2.0 systems in Python 2 were found)

The __Speech Recognition__ module was built to be able to run ON Pepper computer (in the head) it's only dependencies are
* **Python 2.7** ,  because it uses
* [Pepper API (NAOqi 2.5) ](https://developer.softbankrobotics.com/pepper-naoqi-25/naoqi-developer-guide/naoqi-apis)
* **numpy**

All of them are pre-installed on Pepper, if you want to run on your computer just create an environment that has all them.

## Built With

* Python 2.7.18

## Changelog

**Version 1.0** - Initial release, 05 August 2020

## Authors

* **Igor Lirussi** @ KTH Royal Institute of Technology - Department of Robotics, Perception and Learning

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Johannes Bramauer @ Vienna University of Technology - for the [PepperSpeechRecognition](https://github.com/JBramauer/pepperspeechrecognition)
* Anthony Zang (Uberi) and his [SpeechRecognition](https://github.com/Uberi/speech_recognition)
