# encoding: utf-8

# Setting up psychopy stuff: stimuli and helpers
from psychopy.visual import Window, TextStim, ImageStim  # import specific components to reduce memory load
from psychopy.monitors import Monitor
from psychopy import event, core

INSTRUCTION_RESPONSE_START = 2  # minimum number of seconds before accepting responses
KEYS_ADVANCE = [0]  # keys to continue here and there
KEYS_QUIT = ['escape']

# Monitor
MON_DISTANCE = 70  # Distance between subject's eyes and monitor
MON_WIDTH = 34.7  # Width of your monitor in cm
MON_SIZE = [1360, 768]  # Pixel-dimensions of your monitor
MON_COLOR = (150, 150, 150)

# Instructions

TEXT_TASK = u"""Pokyny:
* Svoj pohľad fixujte na hráča v strede
* Každých pár sekúnd presuňte svoje pohľad na niektorú loptu a vráťte sa naspäť na hráča
* Vaše rozhodnutie zmeniť pohľad oznamujete stlačením tlačídla
* Celý presun pohľadu (tam a naspäť) by nemal trvať viac ako 1 sekundu"""
TEXT_CONTINUE = u'Pokračujte stlačením myši ...'

"""
INITIATE STIMULUS OBJECTS
"""

my_monitor = Monitor('testMonitor', width=MON_WIDTH, distance=MON_DISTANCE)  # Create monitor object from the variables above. This is needed to control size of stimuli in
my_monitor.setSizePix(MON_SIZE)
win = Window(monitor=my_monitor, screen=0, units='cm', color=MON_COLOR, colorSpace='rgb255', fullscr=True, allowGUI=False)  # Initiate psychopy Window as the object "win", using the myMon object from last line. Use degree as units!

# Mouse has to be import after a Window is created!
from stimsoft_common import waitMousePressed

instruct = TextStim(win, pos=(0, 5), color='black', height=0.5, wrapWidth=25)
instruct_continue = TextStim(win, text=TEXT_CONTINUE, pos=(0, -5.5), color='black', height=0.5, wrapWidth=25)

image_task = ImageStim(win, image='images/collect_eog2.png')

    
def ask(text='', keyList=KEYS_ADVANCE):
    """
    Show a text and returns answer (keypress)
    and reaction time. Defaults to no text and keysAns.
    """
    #text = text.replace('    ', '').replace('    ', '')  # remove indents
    instruct.text = text
    instruct.draw()
    instruct_continue.draw()
    event.clearEvents()
    win.flip()
    
    # Halt everything and wait for (first) responses matching the keys given in the Q object.
    core.wait(INSTRUCTION_RESPONSE_START)
    key = waitMousePressed(keyList=keyList, keyEvent='release')
    if event.getKeys(keyList=KEYS_QUIT):
        core.quit()
    
    return key


ask(TEXT_TASK)
image_task.draw()
win.flip()
waitMousePressed(maxWait=float('inf'))