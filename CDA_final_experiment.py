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

TEXT_START = 'Press the mouse to generate trials'
TEXT_EXPERIMENT = u'We will begin the task now.'
TEXT_CONTINUE = 'Press the mouse to continue...'

def show_gui_dlg():
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
            except (ValueError, NameError) as e:
                gui.warnDlg(prompt='ERROR: wrong value')
                continue
            
            if '' not in data: 
                break
            else: 
                gui.warnDlg(prompt='ERROR: some fields are not filled!')
        else: 
            return None, None, None

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

    experiment_params = {
        'Ntargets': Ntargets,
        'Ndistractors': Ndistractors,
        'Nruns': Nruns,
        'Nrepetitions': Nrepetitions
    }
    
    return experiment_params, subject_data, filename


# show GUI dialogue
experiment_params, subject_data, filename = show_gui_dlg()
# if cancel clicked -> quit
if experiment_params is None and filename is None:
    core.quit()

# Condition parameters (factorial design)
N_TARGETS = experiment_params['Ntargets']
N_DISTRACTORS = experiment_params['Ndistractors']
PROBE_TYPES = ('same', 'change')
CUES = ['left', 'right']  # mapping of keys to x-axis multiplier for arrow vertices
BLOCKS = {'experiment': experiment_params['Nruns']}
REPETITIONS = {'experiment': experiment_params['Nrepetitions']}

my_monitor = Monitor('testMonitor', width=MON_WIDTH, distance=MON_DISTANCE)  # Create monitor object from the variables above. This is needed to control size of stimuli in degrees.
my_monitor.setSizePix(MON_SIZE)
win = Window(monitor=my_monitor, screen=0, units='cm', color=MON_COLOR, colorSpace='rgb255', fullscr=False, allowGUI=False)  # Initiate psychopy Window as the object "win", using the myMon object from last line. Use degree as units!
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

def spaced_xys(N, side):
    """ 
    Brute force N coordinates until they meet the MIN_DIST criterion.
    Reasonable combinations of N, MIN_DIST and FIELD_HEIGHT/WIDTH are required
    for this to not go into infinite loops.
    """
    while True:
        # list of (x,y) coordinates, rounded.
        coords = [(round(random.uniform(CENTER_DIST, CENTER_DIST+FIELD_WIDTH)*side, 3),
                   round(random.uniform(-FIELD_HEIGHT/2, FIELD_HEIGHT/2), 3))
                   for i in range(N)]

        # Loop through combinations and check if they are good
        combinations = itertools.combinations(coords, 2)  # pairwise combinations
        for c in combinations:
            if math.sqrt((c[1][0] - c[0][0])**2 + (c[1][1]-c[0][1])**2) < MIN_DIST:  # pythagoras
                break  # break for loop
        else:  # if for loop wasn't broken (all coords are good)
            return coords
        
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


def make_empty_trial(exp_phase):
    """ Get the correct trial structure. Useful for barpulses in which we do not
    want all these fields filled out with stuff that's never shown. """
    return {
        # Trial info. Will be filled out later
        'CueSide':'', 'block':'', 'numTargets':'', 'numDistracts':'', 'Probe':'',
        'Condition':'', 'ProbeCode':'', 'CueCode':'', 'xys':'', 'oris':'', 
        'colors':'', 'targets':'', 'probe_id':'', 'probe_ori': '', 'no_block':'',
        'no_total': '',

        # Placeholders for data. Will be filled out later.
        #'ans': '', # 'rt': '', 'response.corr': '',
        'itiUTC': '', 'arrowUTC': '',
        'soaUTC': '', 'memoryArrayUTC': '', 'retentionUTC': '', 'testArrayUTC': '',
        
        # Barcode
        'EventCode': '', #'StartBarcodeUTC': '',
        
        # General session info
        'exp_phase': exp_phase,
        'date': start_info['start_time'],
        'session': start_info['session'],
        'frameRate': start_info['frame_rate'],
        'expName': EXP_IDENTIFIER,
        'participant': start_info['save_file_name'],
        'response_device': RESPONSE_DEVICE
    }


def make_trial_list(exp_phase):
    """ Make a list list of trials for the full experiment """
    trial_list = []
    
    # Loop through blocks and randomize within blocks
    for block in range(BLOCKS['experiment']): # if exp_phase == 'experiment' else BLOCKS['practice']):  # practice or experiment
        trials_block = []
        
        # Now loop through parameters. Factorial design, so we can just make
        # a list of all combinations and loop through it.
#        if exp_phase == 'practice_experimenter':  # practice
#            parameter_sets = itertools.product(range(REPETITIONS['practice']), N_TARGETS, N_DISTRACTORS, [''], [''])
#        elif exp_phase == 'pulse':
#            parameter_sets = itertools.product([0], [1], [0], ['same'], ['left'])
#        else:  # experiment or otherwise
        parameter_sets = itertools.product(range(REPETITIONS['experiment']), N_TARGETS, N_DISTRACTORS, PROBE_TYPES, CUES)
        
        for repetition, n_targets, n_distractors, probe_type, cue in parameter_sets:
            # index of targets. First left indices and then right indices
            targets_left = random.sample(range(n_targets), n_targets)
            targets_right = random.sample(range(n_targets+n_distractors, n_distractors + 2*n_targets), n_targets)
            #if exp_phase == 'practice_experimenter':  # Just take random instead of factorial
            #    probe_type = random.choice(PROBE_TYPES)
            #    cue = random.choice(CUES)
            
            # calculate condition number
            condition = 1 + \
                             (PROBE_TYPES.index(probe_type)==1)*1 + \
                             (CUES.index(cue)==1)*2 + \
                             (N_DISTRACTORS.index(n_distractors)==1)*4 + \
                             (N_TARGETS.index(n_targets)==1)*8

            # Parameters of the trial type
            trial = make_empty_trial(exp_phase)
            trial['CueSide'] = cue
            trial['block'] = block + 1
            trial['numTargets'] = n_targets
            trial['numDistracts'] = n_distractors
            trial['Probe'] = probe_type
            trial['exp_phase'] = exp_phase
            trial['Condition'] = condition
            trial['ProbeCode'] = condition  # identical to as Condition. Delete?
            trial['CueCode'] = TRIGGERS_CUE[cue]
        
            # Parameters of the rectangles
            trial['xys'] = spaced_xys(n_targets + n_distractors, -1) + spaced_xys(n_targets + n_distractors, 1)
            trial['oris'] = np.random.choice(ORIS, 2*(n_distractors+n_targets), replace=True)
            trial['colors'] = [TARGET_COLOR if i in targets_left+targets_right else random.choice(DISTRACTOR_COLORS) for i in range(2*(n_targets+n_distractors))]
            trial['targets'] = targets_left + targets_right
            trial['probe_id'] = random.choice(targets_left) if cue is 'left' else random.choice(targets_right)
            # Set probe orientation
            if probe_type == 'change':
                trial['probe_ori'] = random.choice([ori for ori in ORIS if ori != trial['oris'][trial['probe_id']]])  # orientation if changed. choose a random non-current orientation for the probe
            elif probe_type == 'same':
                trial['probe_ori'] = trial['oris'][trial['probe_id']]  # same orientation as before
                
            trials_block += [trial]
            
        # Randomize order and extend trial_list with this block
        random.shuffle(trials_block)
        for no, trial in enumerate(trials_block):
            trial['no_block'] = no + 1  # start at 1
            trial_list += [trial.copy()]
    
    # Add absolute trial number for the sake of analysis of effects of time
    for no, trial in enumerate(trial_list):
        trial['no_total'] = no
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
    results_path = file_path[:-4] + '-results.csv'
    num_totals = {}
    num_correct = {}
    num_all_trials = 0
    num_all_correct = 0

    # count number of total and correct
    for trial in trial_list:
        response_corr = trial.get('response.corr', 0)
        numTargets = trial['numTargets']
        numDistracts = trial['numDistracts']
        
        # incr total
        if (numTargets, numDistracts) not in num_totals:
            num_totals[(numTargets, numDistracts)] = 0
        num_totals[(numTargets, numDistracts)] += 1
        
        # incr correct
        if (numTargets, numDistracts) not in num_correct:
            num_correct[(numTargets, numDistracts)] = 0
        num_correct[(numTargets, numDistracts)] += response_corr
        
        num_all_trials += 1
        num_all_correct += response_corr
        
    # evaluate accuracy
    with open(results_path, 'w') as f:
        print 'Accuracy for each class:'
        f.write('Accuracy for each class:\n')
        # sort items first by target num, then by distractor num
        sorted_items = sorted(num_totals.items(), key= lambda ((t, d), v): 100 * t + d)
        for ((numTargets, numDistracts), total) in sorted_items:
            print 'T=%d, D=%d: %.2f%%' % (numTargets, numDistracts, 100 * num_correct[(numTargets, numDistracts)] / total)
            f.write('T=%d, D=%d: %.2f%%\n' % (numTargets, numDistracts, 100 * num_correct[(numTargets, numDistracts)] / total))

        print 'Final accuracy: %.2f%%' % (100 * num_all_correct / num_all_trials)
        f.write('Final accuracy: %.2f%%' % (100 * num_all_correct / num_all_trials))

def run_block(exp_phase, experiment_params, trial_list=False):
    """ Loops through trials. Generate a full trial_list if none is specified."""
    ask(TEXT_START)

    trialN = 1
    blockN = 1
    # Durations of the different routines differ between experiment and practice
    durations = DURATIONS['experiment'] # if exp_phase == 'experiment' else DURATIONS['practice']
    
    # Loop through trials
    trial_list = make_trial_list(exp_phase) if not trial_list else trial_list
    ask(TEXT_EXPERIMENT)
    for trial in trial_list:
        print "Trial#:", trialN , "Block#:",blockN 
        trialN = trialN + 1 
        # BREAK on each new block except the first
        trial['exp_phase'] = exp_phase
        if trial['no_block'] == 1 and trial['block'] > 1:
            ask(TEXT_BREAK)
            blockN = blockN + 1 
            trialN = 1
        
        # ITI
        barcode.fillColor = 'black'
        win.callOnFlip(record_utc, trial, 'itiUTC')
        if exp_phase == 'pace_all':
            show_instruct_on_first_frame(TEXT_INTRO_FIX)

        for frame in range(durations['ITI']):
            barcode.draw()
            fix.draw()
            win.flip()
        
        # CUE
        direction = -1 + 2*(trial['CueSide']=='left')  # -1 or 1 for left or right pointing cue
        arrow.vertices = ARROW_VERTICES * [direction, 1]  # Just mirror vertices around y-axis
        
        barcode.fillColor = 'white'
        win.callOnFlip(record_utc, trial, 'arrowUTC')
        
        if exp_phase == 'experiment':
            # send arrow direction to LPT
            win.callOnFlip(parallel.setData, DIO2_TO_LPT[ARR_DIRECTION_TO_DIO2[direction]])
         
        if exp_phase == 'pace_all':
            show_instruct_on_first_frame(TEXT_INTRO_CUE)
        
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
        if exp_phase == 'experiment':
            win.callOnFlip(parallel.setData, DIO2_TO_LPT[PROBE_TO_DIO2[trial['Probe']]])
            
        if exp_phase == 'pace_all':
            show_instruct_on_first_frame(TEXT_INTRO_ARRAY1)
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
        if exp_phase == 'pace_all':
            show_instruct_on_first_frame(TEXT_INTRO_RETENTION)

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
        if exp_phase == 'experiment':
            win.callOnFlip(parallel.setData, DIO2_TO_LPT[LPT_TEST_ARRAY])  # start trigger on next flip

        win.callOnFlip(record_utc, trial, 'testArrayUTC')
        if exp_phase == 'pace_all':
            show_instruct_on_first_frame(TEXT_INTRO_PROBE)
        flip_time = win.flip()
        
        # Stop trigger
        core.wait(1/MON_FRAMERATE)  # one frame's duration
        parallel.setData(0)
        
        # Record response
        if not exp_phase == 'pace_all':
            response_end_time = flip_time + durations['probe']/MON_FRAMERATE - 0.008  # the time of core.getTime() when response time has ended.
            maxWait = response_end_time - core.getTime() if exp_phase in ('experiment') else float('inf')
            
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
            if key is not None and exp_phase in ('experiment', 'practice_experimenter'):
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

run_block('experiment', experiment_params)
ask(TEXT_FINISH)