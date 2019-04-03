from __future__ import division
import itertools
import random
import math
import numpy as np
import time
import os
import json

# Setting up psychopy stuff: stimuli and helpers
from psychopy.visual import Window, Rect, Circle, ShapeStim, TextStim, ImageStim  # import specific components to reduce memory load
from psychopy.monitors import Monitor
from psychopy import event, core
from psychopy import gui

import tools.barcode


EXP_IDENTIFIER = 'CDA_rrLab'

KEYS_ANS = {0: 'change', 2: 'same', None: 'none'}  # mapping from buttons to meaning
KEYS_ADVANCE = [0]  # keys to continue here and there

# Durations (number of frames)
# Durations MON_FRAMERATE 32; frames (number of frames)
DURATIONS = {
    'experiment': {
        'cue': 12,
        'SOA': 12,
        'array1': 12,
        'retention': 54,
        'probe': 180,
        'ITI': 45
    },
}

# Monitor
MON_DISTANCE = 75  # Distance between subject's eyes and monitor
MON_WIDTH = 59.5 # was 34.7  # Width of your monitor in cm
MON_SIZE = [2560, 1440]  # Pixel-dimensions of your monitor
MON_COLOR = (150, 150, 150) # background 255,255,255 white 0,0,0 black was: 150,150,150

# Mapping from gTec Dig-I/O-2 channels to LPT output pins
DIO2_TO_LPT = {
    (5, ):        0b0001,
    (6, ):        0b0010,
    (7, ):        0b0100,
    (8, ):        0b1000,
    (5, 6):       0b0011,
    (5, 7):       0b0101,
    (5, 8):       0b1001,
    (6, 7):       0b0110,
    (6, 8):       0b1010,
    (7, 8):       0b1100,
    (5, 6, 7):    0b0111,
    (5, 6, 8):    0b1011,
    (5, 7, 8):    0b1101,
    (6, 7, 8):    0b1110,
    (5, 6, 7, 8): 0b1111
}

# Mapping of cues to Dig-I/O-2
LPT_ARR_LEFT = (5, )
LPT_ARR_RIGHT = (6, )
LPT_SAME = (7, )
LPT_CHANGE = (8, )
LPT_TEST_ARRAY = (5, 6)  # was LPT_TEST_ARRAY = (5, 6, 7, 8)

ARR_DIRECTION_TO_DIO2 = {1: LPT_ARR_LEFT, -1: LPT_ARR_RIGHT}
PROBE_TO_DIO2 = {'same': LPT_SAME, 'change': LPT_CHANGE}

# Field parameters
MIN_DIST = 2.3  # cm
FIELD_HEIGHT = 7.6  # cm from bottom to top
FIELD_WIDTH = 4.8  # cm from center to extreme
CENTER_DIST = 1.5  # distance from vertical centerline to closest possible rect

# Rectangle parameters
ORIS = (0, 45, 90, 135)  # truly randomly sampled with replacement during experiment
TARGET_COLOR = 'red'
DISTRACTOR_COLORS = ('blue', 'green')
RECT_SIZE = (1.5, 0.5)  # in cm

# Other stuff
ARROW_SHAFT_WIDTH = 0.25 # cm
ARROW_POINT_BASE = 3.0 # cm
ARROW_SIZE = 2 # Some scalar value that works.
FIX_RADUS = 0.15  # cm
KEYS_QUIT = ['escape']

INSTRUCTION_RESPONSE_START = 2  # minimum number of seconds before accepting responses
TRIGGERS_CUE = {'left': 22, 'right': 21}  # swapped compared to original

# Instructions
TEXT_BREAK = 'You are now allowed to take up to three minutes break.'
TEXT_FINISH = 'You have completed this task now!'

TEXT_EXPERIMENT = u'We will begin the task now.'
TEXT_CONTINUE = 'Press the mouse to continue...'


def show_gui_dlg(trials_foldername='trials'):
    myDlg = gui.Dlg(title='Experiment parameters')
    
    myDlg.addText('Subject data', color='purple')
    
    myDlg.addField('Subject initials (XX): ')
    myDlg.addField('Subject ID (XX): ')
    myDlg.addField('Condition: ', choices=['CDT: t={2,3,4} b=5 r=2', 'CDA: t={2,3} b=5 r=3', 'CDA: t={3,4} b=5 r=3'])
    myDlg.addField('TimePoint number: ')
    myDlg.addField('Cohort number (xx): ')
    myDlg.addField('Location: ', choices=['KE', 'BA'])
    myDlg.addField('Dataset version: ', choices=['1', '2', '3'])
    
    while True: 
        data = myDlg.show()
        if myDlg.OK:
            cond, Ntargets, Nblocks, Nrepetitions = data[2].split(' ')
            cond = cond[:-1]  # remove ':' from end
            
            Ntargets = tuple(eval(Ntargets[3:-1]))
            Nblocks = int(Nblocks[2:])
            Nrepetitions = int(Nrepetitions[2:])
            Ndistractors = (0, 2)
            
            if '' not in data:
                # attempt to find stored results
                experiment_params = {
                    'Ntargets': Ntargets,
                    'Ndistractors': Ndistractors,
                    'Nblocks': Nblocks,
                    'Nrepetitions': Nrepetitions
                } 
                trials_filename = 'T={Ntargets},D={Ndistractors},B={Nblocks},R={Nrepetitions}.json'.format(**experiment_params)
                trials_file = os.path.join(trials_foldername, trials_filename)
                if not os.path.isdir(trials_foldername) or not os.path.isfile(trials_file):
                    gui.warnDlg(prompt='Please generate trials first')
                    continue
                with open(trials_file) as f:
                    full_trial_list = json.load(f)
                    
                dataset_idx = int(data[6]) - 1
                if dataset_idx < 0 or dataset_idx >= len(full_trial_list):
                    gui.warnDlg(prompt='ERROR: Trials file does not have required dataset version')
                    continue
                trial_list = full_trial_list[dataset_idx]
                break
            else: 
                gui.warnDlg(prompt='ERROR: some fields are not filled!')
        else: 
            return None

    subject_data = {
        'SubInt': data[0],
        'SubID': data[1],
        'Cond': cond,
        'TPnum': data[3],
        'Cohort': data[4],
        'Location': data[5],
        'Dataset': data[6],
        'current_time':  time.strftime('%d-%m-%Y %H-%M-%S')
    }
    
    filename = "{SubInt} {SubID} {Cond} {TPnum} C{Cohort}-L{Location}-D{Dataset} {current_time}.csv".format(**subject_data)
    
    return experiment_params, subject_data, filename, trial_list


# show GUI dialogue
gui_output = show_gui_dlg()
# if cancel clicked => quit
if gui_output is None:
    core.quit()
    
experiment_params, subject_data, filename, trial_list = gui_output

# Condition parameters (factorial design)
N_TARGETS = experiment_params['Ntargets']
N_DISTRACTORS = experiment_params['Ndistractors']
PROBE_TYPES = ('same', 'change')
CUES = ['left', 'right']  # mapping of keys to x-axis multiplier for arrow vertices
BLOCKS = {'experiment': experiment_params['Nblocks']}
REPETITIONS = {'experiment': experiment_params['Nrepetitions']}

my_monitor = Monitor('testMonitor', width=MON_WIDTH, distance=MON_DISTANCE)  # Create monitor object from the variables above. This is needed to control size of stimuli in degrees.
my_monitor.setSizePix(MON_SIZE)
win = Window(monitor=my_monitor, screen=0, units='cm', color=MON_COLOR, colorSpace='rgb255', fullscr=True, allowGUI=False)  # Initiate psychopy Window as the object "win", using the myMon object from last line. Use degree as units!
barcode = tools.barcode.BarcodePulse(win)

# Mouse has to be import after a Window is created!
from stimsoft_common import waitMousePressed, getMousePressed, record_utc, csvWriter, parallel, get_start_info

rect = Rect(win, width=RECT_SIZE[0], height=RECT_SIZE[1], lineColor=None)
fix = Circle(win, radius=FIX_RADUS, fillColor='black', lineColor=None)
instruct = TextStim(win, pos=(0, 5), color='black', height=0.5, wrapWidth=25)
instruct_continue = TextStim(win, text=TEXT_CONTINUE, pos=(0, -5.5), color='black', height=0.5, wrapWidth=25)

ARROW_VERTICES = np.array((
    # Start at the tip in a counter-clockwise direction.
    (-0.5 * ARROW_POINT_BASE, 0),
    (-0.25 * ARROW_POINT_BASE, ARROW_SIZE * ARROW_SHAFT_WIDTH),
    (-0.25 * ARROW_POINT_BASE, 0.5 * ARROW_SHAFT_WIDTH),
    (0.5 * ARROW_POINT_BASE, 0.5 * ARROW_SHAFT_WIDTH),
    (0.5 * ARROW_POINT_BASE, -0.5 * ARROW_SHAFT_WIDTH),
    (-0.25 * ARROW_POINT_BASE, -0.5 * ARROW_SHAFT_WIDTH),
    (-0.25 * ARROW_POINT_BASE, -ARROW_SIZE * ARROW_SHAFT_WIDTH),
    (-0.5 * ARROW_POINT_BASE, 0)
    ))
arrow = ShapeStim(win, fillColor='black', pos=(0, 1.5), lineColor=None)

start_info = get_start_info(win)
start_info['save_file_name'] = '%s %s' % (subject_data['SubInt'], subject_data['SubID'])

MON_FRAMERATE = start_info['frame_rate']

"""
FUNCTIONS
"""

def ask(text='', keyList=KEYS_ADVANCE):
    """
    Show a text and returns answer (keypress)
    and reaction time. Defaults to no text and keysAns.
    """
    #barcode.draw()
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

    
def prepare_trials(trial_list):
    prepared_trial_list = []
    for current_block in trial_list:
        random.shuffle(current_block)
        # append no within block
        for no, trial in enumerate(current_block):
            trial['no_block'] = no + 1
            
        prepared_trial_list.extend(current_block)

    # then include additional info
    for trial in prepared_trial_list:
        trial['date'] = start_info['start_time']
        trial['session'] = start_info['session']
        trial['frameRate'] = start_info['frame_rate']
        trial['expName'] = EXP_IDENTIFIER
        trial['participant'] = start_info['save_file_name']
        trial['CueCode'] = TRIGGERS_CUE[trial['CueSide']]
        
    return prepared_trial_list
    

def show_instruct_on_first_frame(text):
    instruct.text = text
    instruct.draw()
    instruct_continue.draw()
    win.callOnFlip(core.wait, INSTRUCTION_RESPONSE_START)
    win.callOnFlip(waitMousePressed, keyList=KEYS_ADVANCE, keyEvent='release')
        
        
def assess_timing(time_first, time_second, frames):
    """ Print comparison of actual and desired duration between two times. """
    actual = 1000*time_second - 1000*time_first
    desired = 1000*frames / MON_FRAMERATE
    print 'actual: %i ms, desired: %i ms, difference: %i ms' %(actual, desired, actual-desired)


def run_block(experiment_params, trial_list):
    trialN = 1
    blockN = 1
    # Durations of the different routines differ between experiment and practice
    durations = DURATIONS['experiment']
    
    # Loop through trials
    ask(TEXT_EXPERIMENT)
    for trial in trial_list:
        print "Trial#:", trialN , "Block#:",blockN 
        trialN = trialN + 1 
        if trial['no_block'] == 1 and trial['block'] > 1:
            ask(TEXT_BREAK)
            blockN = blockN + 1 
            trialN = 1
        
        # ITI
        barcode.fillColor = 'black'
        win.callOnFlip(record_utc, trial, 'itiUTC')

        for frame in range(durations['ITI']):
            barcode.draw()
            fix.draw()
            win.flip()
        
        # CUE
        direction = -1 + 2*(trial['CueSide']=='left')  # -1 or 1 for left or right pointing cue
        arrow.vertices = ARROW_VERTICES * [direction, 1]  # Just mirror vertices around y-axis
        
        barcode.fillColor = 'white'
        win.callOnFlip(record_utc, trial, 'arrowUTC')
        
        # send arrow direction to LPT
        win.callOnFlip(parallel.setData, DIO2_TO_LPT[ARR_DIRECTION_TO_DIO2[direction]])
         
        for frame in range(durations['cue']):
            barcode.draw()
            arrow.draw()
            fix.draw()
            win.flip()
            # reset parallel on second flip
            win.callOnFlip(parallel.setData, 0)

        
        # SOA
        barcode.fillColor = 'black'
        win.callOnFlip(record_utc, trial, 'soaUTC')
        
        for frame in range(durations['SOA']):
            barcode.draw()
            fix.draw()
            win.flip()
        
        # ARRAY 1
        barcode.fillColor = 'white'
        win.callOnFlip(record_utc, trial, 'memoryArrayUTC')
        # send probe type (same/change) to LPT
        win.callOnFlip(parallel.setData, DIO2_TO_LPT[PROBE_TO_DIO2[trial['Probe']]])
            
        for frame in range(durations['array1']):
            # Use rect to draw all the appropriate stimuli
            for i in range(len(trial['xys'])):
                rect.pos = trial['xys'][i]
                rect.ori = trial['oris'][i]
                rect.fillColor = trial['colors'][i]
                rect.draw()
            barcode.draw()
            fix.draw()
            win.flip()
            # reset parallel on second flip
            win.callOnFlip(parallel.setData, 0)
        
        # RETENTION
        barcode.fillColor = 'black'
        win.callOnFlip(record_utc, trial, 'retentionUTC')

        for frame in range(durations['retention']):
            barcode.draw()
            fix.draw()
            win.flip()
            
        # PROBE
        # Do not time using frames since we want to react to key presses immediately
        # Use rect to draw all the appropriate stimuli
        barcode.fillColor = 'white'
        barcode.draw()
        for i in range(len(trial['xys'])):
            rect.pos = trial['xys'][i]
            rect.ori = trial['probe_ori'] if i == trial['probe_id'] else trial['oris'][i]
            rect.fillColor = trial['colors'][i]
            rect.draw()
        fix.draw()
        
        # Ready to display. Line up functions to be executed on flip
        # send test array appearance to LPT
        win.callOnFlip(parallel.setData, DIO2_TO_LPT[LPT_TEST_ARRAY])

        win.callOnFlip(record_utc, trial, 'testArrayUTC')
        flip_time = win.flip()
        
        # Stop trigger
        core.wait(1/MON_FRAMERATE)  # one frame's duration
        parallel.setData(0)
        
        # Record response
        response_end_time = flip_time + durations['probe']/MON_FRAMERATE - 0.008  # the time of core.getTime() when response time has ended.
        maxWait = response_end_time - core.getTime()
        
        # Get response
        key = waitMousePressed(keyList=KEYS_ANS.keys(), maxWait=maxWait)  # desired duration from flip_time, but allow for 8 ms to catch the next win.flip()
            
        # React to response

        # A basic transformations
        rt = core.monotonicClock.getTime() - flip_time  # time elapsed since probe onset, not since psychopy.core start
        
        # Score trial
        trial['ans'] = KEYS_ANS[key]
        trial['response.corr'] = int(KEYS_ANS[key] == trial['Probe'])
        trial['rt'] = rt
        
        # Continue waiting until time has passed
        if key is not None:
            core.wait(response_end_time - core.getTime(), 0.1)

        # SAVE non-practice trials if experiment was not exited.
        if event.getKeys(keyList=KEYS_QUIT):
            core.quit()
        writer._write_immediate(trial)
    

file_path = os.path.join(start_info['save_file_path'], filename)
writer = csvWriter(file_path) # save I/O for when the experiment ends/python errors

# Run the real thing!
trial_list = prepare_trials(trial_list)
run_block(experiment_params, trial_list)
ask(TEXT_FINISH)
