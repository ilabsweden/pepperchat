Some while ago I wrote a short tutorial about how to create an AIML chatbot and output its text
via espeak (https://iniy.org/?p=68).

AFter years I stumbled over this post again and now here is a second part which loads the AI Foundation's A.L.I.C.E.
AIML from http://www.alicebot.org/aiml.html .

To be honest I was a bit surprised about how little and hard to find documentation there is on the
net to get this simple aiml files to run. There is a bit hard to find google code page:
https://code.google.com/archive/p/aiml-en-us-foundation-alice/

But the AIML is optimized for the Pandorabots online plattform and I wanted just to play around
a bit with this stuff locally.

So here is a repository with batteries included:

- Based on aiml-en-us-foundation-alice-1.9 zip file from the AI Foundation google code website
- removed Pandorabots specific syntax
- added std-startup.aiml with the (I think) correct load-order of the aiml files
- minimal version of a python chatbot

## Setup

Requires python3 (but porting this minimal script to python 2 is very easy)


    pip3 install python-aiml

Then just run

    ./chatbot.py
    
## Where to go from here

This minimal script doesn't implement a preprocessor and due to the removal of some pandorabots
special syntax it might give some odd answers, but it is a starting point.

Add your own AIML files at the bottom of the std-startup.aiml (so they have highest priority)
and play around making the bot smarter.

Including the espeak output from my other blog post also might be fun (https://iniy.org/?p=68).

## General Documentation (from AI Foundation google code website)

As I had a hard time finding the loading order information I include this here in the repo.


### Using the A.L.I.C.E. AIML files

The aiml-en-us-foundation-alice files contain a number of categories with duplicate patterns. Depending on the AIML interpreter used, duplicates are handled differently.

On Pandorabots the rule is: The files are loaded in order from the top of the list (under the "AIML Files" section) to the bottom. When a category is loaded that has the same pattern path (i.e. same input pattern, that pattern and topic pattern--remember that <that> and <topic> are set to implicitly), then Pandorabots discards the earlier category and selects the response template from the most recently loaded category.

To give an example: Suppose a file A.aiml has a category <category> <pattern>TEST</pattern> <template>This is the response from file A.</template> </category> and a file B.aiml has a category <category> <pattern>TEST</pattern> <template>This is the response from file B.</template> </category>

Provided that the files are loaded in alphabetical order, the A.aiml loaded before the B.aiml, then the response to the input "Test" should be "This is the response from file B."
A.L.I.C.E. AIML File Order

The A.L.I.C.E. AIML files in aiml-en-us-foundation-alice should be loaded in the following order:

- First load the Safe reduction files reducation0.safe.aiml,...,reduction4.safe.aiml and reductions.update.aiml.
- Second, load the Mindpixel files mp0.aiml,...,mp6.aiml.
- Then load all remaining AIML files.
- Pandorabots will always load the file update.aiml as the last file.

### AIML utilizes a preprocessing step called Normalization.

This AIML set is designed to work with the default AIML preprocessor supplied with Pandorabots.com.

    The preprocessor

    Corrects some spelling errors and colloquialisms (e.g. "wanna" --> "want to")
    Substitutes words for common emoticons (e.g. ":-)" --> "SMILE")
    Expands contractions (e.g. "isn't" --> "is not")
    Removes intra-sentence punctuation (e.g. "Dr. Wallace lives on St. John St. --> "Dr Wallace lives on St John St.")

We refer to the above substitution steps as Normalization.

The last preprocessing step

    Splits sentences based on predefined punctuation characters ".", "!", ";" and "?"

All of these preprocessing steps are defined in the configuration file. In addition the configuration file

    Defines substitutions for <gender>, <person> and <person2>

The preprocessor normalizes the inputs to the bot by running through a series of substitutions, then splits the input into sentences and feeds these one at a time to the bot.
