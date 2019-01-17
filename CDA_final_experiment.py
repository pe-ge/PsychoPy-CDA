"""
How I did this:
 * First began writing make_trial_list, adding "static" variables as needed.
   In total I spent around 3 hours getting this as simple and efficient as
   possible. In particular how to represent xys, oris, colors, and probes. 
   (I started out having fields called "xys_left", "xys_right", "oris_target", 
   "probes_xys" etc.)
 * Then wrote make_grids and added psychopy objects as needed.
 * Then wrote run_block and added arrow, fixation and duration-variables as needed
 * Then added extra stuff:
     1. record responses (initially using iohub and flip-loops until I 
        discovered that trigger and break happened immediately on key press.
     2. record UTC times and send triggers
     3. save trial
     4. add practice stuff
     

Improvements / additions as compared to Contralateral_Delay_Activity_v9-0.py:
 * Generates conditions and draws stimuli. The latter takes 1-3 ms on my laptop.
 * Has practice (according to spec)
 * Records UTC timestamps
 * Saves data
 * timing using frames rather than milliseconds.
 
Other changes relative relative to Contralateral_Delay_Activity_v9-0.py:
 * according to Len, the +/- 35 ms is allowed jitter, not desired, so no jitter here.
 * Some colors are changed so that they match the specification.
 * Fewer stimuli loaded (e.g. arrow directions are changed by multiplying)
 * More self-contained script


CONSIDER FOR LATER:
 * Add system "free" time using core.wait(0.010, hogCPUperiod=0.001) between flips?
 * Later: make a list of dicts representing rect-properties instead of separate
      columns in the trial_list (rect object is the meaningful unit, not property).
 * Maybe generate trials from hard-coded conditions
  * According to spec, fixation cross and arrow are both at +9.7 cm relative to 
      screen bottom. But the spec image shows the arrow above the fix?
"""


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
RESPONSE_DEVICE = 'mouse'  # 'mouse' or 'cedrus_keyboard'. 'cedrus_bits' will be added later

if RESPONSE_DEVICE == 'mouse':
    KEYS_ANS = {0: 'change', 2: 'same', None: 'none'}  # mapping from buttons to meaning
    KEYS_ADVANCE = [0]  # keys to continue here and there
    TRIGGERS_ANS = {0: 41, 2: 42}  # left and right. triggers to send on response onset

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
TRIGGERS_CUE = {'left': 21, 'right': 22}  # triggers to send on cue onset

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
    myDlg.addField('Condition: ', choices=['CDT', 'CDA','CAVE', 'EC', 'EO'])
    myDlg.addField('TimePoint type: ', choices=['preTRAIN', 'postTRAIN'])
    myDlg.addField('TimePoint number: ')
    myDlg.addField('Cohort number (xx): ')
    myDlg.addField('Location: ', choices=['KE', 'BA'])
    myDlg.addField('Visit number: ')
    
    myDlg.addText('Experiment parameters', color='purple')
    
    myDlg.addField('Number of targets: ')
    myDlg.addField('Number of distractors: ')
    myDlg.addField('Number of blocks: ')
    myDlg.addField('Number of repetitions: ')
    
    while True: 
        data = myDlg.show()
        if myDlg.OK:
            try:
                Ntargets = tuple(eval(data[8] + ','))
                Ndistractors = tuple(eval(data[9] + ','))
                Nruns = int(data[10])
                Nrepetitions = int(data[11])
            except (ValueError, NameError, SyntaxError) as e:
                gui.warnDlg(prompt='ERROR: incorrect value')
                continue
            
            if '' not in data:
                # attempt to find stored results
                experiment_params = {
                    'Ntargets': Ntargets,
                    'Ndistractors': Ndistractors,
                    'Nruns': Nruns,
                    'Nrepetitions': Nrepetitions
                } 
                trials_filename = 'T={Ntargets},D={Ndistractors},R={Nruns},B={Nrepetitions}.json'.format(**experiment_params)
                trials_file = os.path.join(trials_foldername, trials_filename)
                if not os.path.isdir(trials_foldername) or not os.path.isfile(trials_file):
                    gui.warnDlg(prompt='Please generate trials first')
                    continue
                with open(trials_file) as f:
                    full_trial_list = json.load(f)
                    
                visit_day_idx = int(data[7]) - 1
                if visit_day_idx < 0 or visit_day_idx >= len(full_trial_list):
                    gui.warnDlg(prompt='ERROR: Trials file does not have required day of visit')
                    continue
                trial_list = full_trial_list[visit_day_idx]
                break
            else: 
                gui.warnDlg(prompt='ERROR: some fields are not filled!')
        else: 
            return None

    subject_data = {
        'SubInt': data[0],
        'SubID': data[1],
        'Cond': data[2],
        'TPtype': data[3],
        'TPnum': data[4],
        'Cohort': data[5],
        'Location': data[6],
        'Visit': data[7],
        'current_time':  time.strftime('%d-%m-%Y %H-%M-%S')
    }
    
    filename = "{SubInt} {SubID} {Cond} {TPtype}{TPnum} C{Cohort}-L{Location}-D{Visit} {current_time}.csv".format(**subject_data)
    
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
BLOCKS = {'experiment': experiment_params['Nruns']}
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
    if RESPONSE_DEVICE == 'mouse':
        key = waitMousePressed(keyList=keyList, keyEvent='release')
    if event.getKeys(keyList=KEYS_QUIT):
        core.quit()
    
    return key

    
def prepare_trials(trial_list):
    random.shuffle(trial_list)
    for trial in trial_list:
        trial['date'] = start_info['start_time']
        trial['session'] = start_info['session']
        trial['frameRate'] = start_info['frame_rate']
        trial['expName'] = EXP_IDENTIFIER
        trial['participant'] = start_info['save_file_name']
        trial['response_device'] = RESPONSE_DEVICE
        trial['CueCode'] = TRIGGERS_CUE[trial['CueSide']]
    return trial_list
    

def show_instruct_on_first_frame(text):
    instruct.text = text
    instruct.draw()
    instruct_continue.draw()
    win.callOnFlip(core.wait, INSTRUCTION_RESPONSE_START)
    if RESPONSE_DEVICE == 'mouse':
        win.callOnFlip(waitMousePressed, keyList=KEYS_ADVANCE, keyEvent='release')
        
        
def assess_timing(time_first, time_second, frames):
    """ Print comparison of actual and desired duration between two times. """
    actual = 1000*time_second - 1000*time_first
    desired = 1000*frames / MON_FRAMERATE
    print 'actual: %i ms, desired: %i ms, difference: %i ms' %(actual, desired, actual-desired)


def write_performance(trial_list):
    from collections import defaultdict
    
    results_path = file_path[:-4] + '-results.csv'
    
    true_positive = defaultdict(int)
    condition_positive = defaultdict(int)
    false_negative = defaultdict(int)
    condition_negative = defaultdict(int)
    
    all_combinations = set()
    
    num_all_trials = 0
    num_all_correct = 0

    # count number of total and correct
    for trial in trial_list:
        response_corr = trial.get('response.corr', 0)  # 1 = correct, 0 = incorrect
        
        num_targets = trial['numTargets']
        num_distracts = trial['numDistracts']
        
        if trial['Probe'] == 'same':
            condition_negative[(num_targets, num_distracts)] += 1
            false_negative[(num_targets, num_distracts)] = 1 - response_corr
        elif trial['Probe'] == 'change':
            condition_positive[(num_targets, num_distracts)] += 1
            true_positive[(num_targets, num_distracts)] += response_corr
        else:
            print 'incorrect probe value (%s) :-(' % (trial['Probe'])
        
        all_combinations.add((num_targets, num_distracts))

    # evaluate accuracy
    with open(results_path, 'w') as f:
        print 'WMC for each class:'
        f.write('WMC for each class:\n')
        # sort items first by target num, then by distractor num
        sorted_items = sorted(list(all_combinations), key= lambda (t, d): 100 * t + d)
        for (num_targets, num_distracts) in sorted_items:
            hit_rate = true_positive[(num_targets, num_distracts)] / condition_positive[(num_targets, num_distracts)]
            false_alarm = false_negative[(num_targets, num_distracts)] / condition_negative[(num_targets, num_distracts)]
            
            wmc_1 = str((num_targets + num_distracts) * (hit_rate - false_alarm))
            wmc_2 = str((num_targets) * (hit_rate - false_alarm))
            
            wmc = wmc_1 if wmc_1 == wmc_2 else '%s %s' % (wmc_1, wmc_2)
            
            print 'T=%d, D=%d: %s' % (num_targets, num_distracts, wmc)
            f.write('T=%d, D=%d: %s\n' % (num_targets, num_distracts, wmc))

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
        if RESPONSE_DEVICE == 'mouse':
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
            write_performance(trial_list)
            core.quit()
        writer._write_immediate(trial)
    write_performance(trial_list)


file_path = os.path.join(start_info['save_file_path'], filename)
writer = csvWriter(file_path) # save I/O for when the experiment ends/python errors

# Run the real thing!
trial_list = prepare_trials(trial_list)
run_block(experiment_params, trial_list)
ask(TEXT_FINISH)