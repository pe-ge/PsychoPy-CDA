# encoding: utf-8

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

EXP_IDENTIFIER = 'Contralateral_Delay_Activity_v9-0'
RESPONSE_DEVICE = 'mouse'  # 'mouse' or 'cedrus_keyboard'. 'cedrus_bits' will be added later

if RESPONSE_DEVICE == 'mouse':
    KEYS_ANS = {0: 'change', 2: 'same'}  # mapping from buttons to meaning
    KEYS_ADVANCE = [0]  # keys to continue here and there
    TRIGGERS_ANS = {0: 41, 2: 42}  # left and right. triggers to send on response onset
elif RESPONSE_DEVICE == 'cedrus_keyboard':
    KEYS_ANS = {'left': 'change', 'right': 'same'}  # mapping from buttons to meaning
    KEYS_ADVANCE = ['left']  # keys to continue here and there
    TRIGGERS_ANS = {'left': 41, 'right': 42}  # left and right. triggers to send on response onset

# Condition parameters (factorial design)
N_TARGETS = (1, 3)
N_DISTRACTORS = (0, 2)
PROBE_TYPES = ('same', 'change')
CUES = ['left', 'right']  # mapping of keys to x-axis multiplier for arrow vertices
# orig BLOCKS = {'experiment': 6, 'practice': 1}
BLOCKS = {'experiment': 1, 'practice': 1}
# orig REPETITIONS = {'experiment': 6, 'practice': 8}
REPETITIONS = {'experiment': 2, 'practice': 3}

# Durations (number of frames)
DURATIONS = {
    'experiment': {
        'cue': 12,
        'SOA': 12,
        'array1': 12,
        'retention': 54,
        'probe': 180,
        'ITI': 45
    },
    'practice': {
        'cue': 12,
        'SOA': 12,
        'array1': 12,
        'retention': 36,
        'probe': 120,
        'ITI': 45
    }
}

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

# Monitor
MON_DISTANCE = 70  # Distance between subject's eyes and monitor
MON_WIDTH = 34.7  # Width of your monitor in cm
MON_SIZE = [1360, 768]  # Pixel-dimensions of your monitor
MON_COLOR = (150, 150, 150)
MON_FRAMERATE = 60

# Instructions

TEXT_INTRO = u'Vitajte! V tomto experimente budeme testovať vašu schopnosť udržať niekoľko objektov v pracovnej pamäti. Experiment je zložený z viacerých pokusov. Na obrázku je znázornený priebeh jedného pokusu. Pohľad majte stále upretý na čiernu bodku v strede obrazovky! '
TEXT_BREAK = u'Teraz si môžete tri minúty oddýchnuť.'
TEXT_FINISH = u'Teraz ste úlohu dokončili!'

TEXT_INTRO_FIX = u'Každý pokus začne prázdnou obrazovkou. Zrak nechajte upretý na čiernej bodke zobrazenej nižšie. '
TEXT_INTRO_CUE = u'Ďalej sa zobrazí šípka. Ak šípka smeruje doľava, počas tohto pokusu zamerajte pozornosť na ľavú stranu obrazovky. Ak šípka smeruje doprava, zamerajte pozornosť na pravú stranu obrazovky. Opäť, počas celej doby držte pohľad uprený pevne na čiernej bodke v strede obrazovky! '
TEXT_INTRO_ARRAY1 = u'Ďalej uvidíte niekoľko farebných obdĺžnikov. Niektoré z nich budú červené. Ostatné môžu byť modré alebo zelené. Pozornosť venujte iba červeným obdĺžnikom, len na strane obrazovky, ktorú naznačila šípka. Opäť, počas tejto doby držte pohľad pevne na čiernej bodke v strede obrazovky! '
TEXT_INTRO_RETENTION = u'Po zmiznutí útvarov si udržte v pamäti orientáciu červených obdĺžnikov, ktoré ste práve videli. Sústreďte sa iba na červené obdĺžniky na tej strane obrazovky, ktorú naznačila šípka. Opäť, počas tejto doby držte oči pevne upreté na čiernej bodke v strede obrazovky a pokúste sa nežmurkať! '
TEXT_INTRO_PROBE = u'Nakoniec sa objavia dva obdĺžniky (jeden na každej strane obrazovky). Vyhodnoťte obdĺžnik na tej strane obrazovky, ktorú označuje šípka. Ak sa zmenila jeho orientácia, stlačte zelené (ľavé) tlačidlo. Ak je jeho orientácia rovnaká ako v predchádzajúcej scéne, stlačte červené (pravé) tlačidlo. '

TEXT_PRACTICE0 = u"""Poďme si to precvičiť. Nezabudnite:
* Pohľad držte upretý na čiernej bodke v strede obrazovky
* Pozornosť zamerajte na stranu naznačenú šípkou
* Zapamätajte si len orientáciu červených obdĺžnikov
* Stlačte zelené tlačidlo, ak sa orientácia zmenila
* Stlačte červené tlačidlo, ak orientácia zostala rovnaká """
TEXT_PRACTICE1 = u"""Teraz skúsme niekoľko zácvičných pokusov. Na konci každého pokusu sa pozastavíme a preberieme si správnu odpoveď.

Môžeme?"""
TEXT_PRACTICE2 = u"""Teraz skúsme niekoľko zácvičných pokusov s použitím rýchlosti, akou bude experiment naozaj bežať.

Môžeme?"""
TEXT_CONTINUE = u'Pokračujte stlačením myši ...'

"""
INITIATE STIMULUS OBJECTS
"""

# Setting up psychopy stuff: stimuli and helpers
from psychopy.visual import Window, Rect, Circle, ShapeStim, TextStim, ImageStim  # import specific components to reduce memory load
from psychopy.monitors import Monitor
from psychopy import event, core
import tools.barcode

my_monitor = Monitor('testMonitor', width=MON_WIDTH, distance=MON_DISTANCE)  # Create monitor object from the variables above. This is needed to control size of stimuli in degrees.
my_monitor.setSizePix(MON_SIZE)
win = Window(monitor=my_monitor, screen=0, units='cm', color=MON_COLOR, colorSpace='rgb255', fullscr=True, allowGUI=False)  # Initiate psychopy Window as the object "win", using the myMon object from last line. Use degree as units!

# Mouse has to be import after a Window is created!
from stimsoft_common import waitMousePressed, getMousePressed, record_utc, csvWriter, parallel, get_start_info

barcode = tools.barcode.BarcodePulse(win)
rect = Rect(win, width=RECT_SIZE[0], height=RECT_SIZE[1], lineColor=None)
fix = Circle(win, radius=FIX_RADUS, fillColor='black', lineColor=None)
instruct = TextStim(win, pos=(0, 5), color='black', height=0.5, wrapWidth=25)
instruct_continue = TextStim(win, text=TEXT_CONTINUE, pos=(0, -5.5), color='black', height=0.5, wrapWidth=25)

image_task = ImageStim(win, image='intros/pfizer-cda.png')
# image_response_pad = ImageStim(win, image='intros/cda_response_pad_t.png', pos=(0, -0.6))
image_response_pad = ImageStim(win, image='intros/buttons-sk.jpg', pos=(0, -0.6))
image_response_pad.size = image_response_pad.size / 1.9  # downscale

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
    elif RESPONSE_DEVICE == 'cedrus_keyboard':
        key = event.waitKeys(keyList=keyList)[0]
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
        'ans': '', 'rt': '', 'response.corr': '', 'itiUTC': '', 'arrowUTC': '',
        'soaUTC': '', 'memoryArrayUTC': '', 'retentionUTC': '', 'testArrayUTC': '',
        
        # Barcode
        'EventCode': '', 'StartBarcodeUTC': '',
        
        # General session info
        'exp_phase': exp_phase,
        'date': start_info['start_time'],
        'session': start_info['session'],
        'frameRate': start_info['frame_rate'],
        'expName': EXP_IDENTIFIER,
        'participant': start_info['save_file_path'],
        'response_device': RESPONSE_DEVICE
    }

def make_trial_list(exp_phase):
    """ Make a list list of trials for the full experiment """
    trial_list = []
    
    # Loop through blocks and randomize within blocks
    for block in range(BLOCKS['experiment'] if exp_phase == 'experiment' else BLOCKS['practice']):  # practice or experiment
        trials_block = []
        
        # Now loop through parameters. Factorial design, so we can just make
        # a list of all combinations and loop through it.
        if exp_phase == 'practice_experimenter':  # practice
            parameter_sets = itertools.product(range(REPETITIONS['practice']), N_TARGETS, N_DISTRACTORS, [''], [''])
        elif exp_phase == 'pulse':
            parameter_sets = itertools.product([0], [1], [0], ['same'], ['left'])
        else:  # experiment or otherwise
            parameter_sets = itertools.product(range(REPETITIONS['experiment']), N_TARGETS, N_DISTRACTORS, PROBE_TYPES, CUES)
        
        for repetition, n_targets, n_distractors, probe_type, cue in parameter_sets:
            # index of targets. First left indices and then right indices
            targets_left = random.sample(range(n_targets), n_targets)
            targets_right = random.sample(range(n_targets+n_distractors, n_distractors + 2*n_targets), n_targets)
            if exp_phase == 'practice_experimenter':  # Just take random instead of factorial
                probe_type = random.choice(PROBE_TYPES)
                cue = random.choice(CUES)
            
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
    elif RESPONSE_DEVICE == 'cedrus_keyboard':
        win.callOnFlip(event.waitKeys, keyList=KEYS_ADVANCE)
def assess_timing(time_first, time_second, frames):
    """ Print comparison of actual and desired duration between two times. """
    actual = 1000*time_second - 1000*time_first
    desired = 1000*frames / MON_FRAMERATE
    print 'actual: %i ms, desired: %i ms, difference: %i ms' %(actual, desired, actual-desired)


def run_block(exp_phase, trial_list=False):
    """ Loops through trials. Generate a full trial_list if none is specified."""
    # Durations of the different routines differ between experiment and practice
    durations = DURATIONS['experiment'] if exp_phase == 'experiment' else DURATIONS['practice']
    
    # Loop through trials
    trial_list = make_trial_list(exp_phase) if not trial_list else trial_list
    for trial in trial_list:
        # BREAK on each new block except the first
        trial['exp_phase'] = exp_phase
        if trial['no_block'] == 1 and trial['block'] > 1:
            ask(TEXT_BREAK)
        
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
            win.callOnFlip(parallel.setData, trial['CueCode'])  # set trigger on first flip 
            ### toto je zatial dummy parallel , ale je to nastavene tak aby to poslalo CueCode ...
         
        if exp_phase == 'pace_all':
            show_instruct_on_first_frame(TEXT_INTRO_CUE)
        
        for frame in range(durations['cue']):
            barcode.draw()
            arrow.draw()
            fix.draw()
            win.flip()
            win.callOnFlip(parallel.setData, 0)  # reset parallel on second flip

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
            win.callOnFlip(parallel.setData, trial['ProbeCode'])  # Trigger is condition
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
            win.callOnFlip(parallel.setData, 0)  # reset parallel on second flip
        
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
        if exp_phase == 'experiment': win.callOnFlip(parallel.setData, 30)  # start trigger on next flip
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
            maxWait = response_end_time - core.getTime() if exp_phase in ('experiment', 'practice_experimenter') else float('inf')
            
            # Get response
            if RESPONSE_DEVICE == 'mouse':
                key = waitMousePressed(keyList=KEYS_ANS.keys(), maxWait=maxWait)  # desired duration from flip_time, but allow for 8 ms to catch the next win.flip()
            elif RESPONSE_DEVICE == 'cedrus_keyboard':
                key = event.waitKeys(keyList=KEYS_ANS.keys(), maxWait=maxWait)
                if key is not None:
                    key = key[0]
            
            # React to response
            if key is not None:
                # A basic transformations
                rt = core.monotonicClock.getTime() - flip_time  # time elapsed since probe onset, not since psychopy.core start
                
                # Send trigger for 1 frame
                if exp_phase == 'experiment': parallel.setData(TRIGGERS_ANS[key])
                core.wait(1/MON_FRAMERATE)
                parallel.setData(0)
                
                # Score trial
                trial['ans'] = KEYS_ANS[key]
                trial['response.corr'] = int(KEYS_ANS[key] == trial['Probe'])
                trial['rt'] = rt
                
                # Continue waiting until time has passed
                if exp_phase in ('experiment', 'practice_experimenter'):
                    core.wait(response_end_time - core.getTime(), 0.1)
            
            # React to timeout
            else:
                pass
        
        # SAVE non-practice trials if experiment was not exited.
        if event.getKeys(keyList=KEYS_QUIT):
            core.quit()
        writer.write(trial)
        
        # #Assess timing.
        # #Needs some renaming becaue trial key names were changed in the meantime
        #assess_timing(trial['iti_onset'], trial['cue_onset'], ITI)
        #assess_timing(trial['cue_onset'], trial['soa_onset'], CUE_DURATION)
        #assess_timing(trial['soa_onset'], trial['array1_onset'], SOA)
        #assess_timing(trial['array1_onset'], trial['retention_onset'], ARRAY1_DURATION)
        #assess_timing(trial['retention_onset'], trial['probe_onset'], RETENTION_DURATION)
        #print 'probe duration:', get_utc() - trial['probe_onset']
    
    # For practice, score responses and show feedback for experimenter.
    if exp_phase == 'practice_experimenter':
        experimenter_evaluation(trial_list)

def experimenter_evaluation(trial_list):
    """Given a trial list, present a screen which allows the experimenter
    to assess the subject's performance and repeat the practice, if judged
    necessary."""
    
    scores = {1:{0:0, 2:0}, 3:{0:0, 2:0}}  # first level is number of targets. Second level is number of distractors
    counts = {1:{0:0, 2:0}, 3:{0:0, 2:0}}  # just for counting the number of trials in each condition although that should be REPETITIONS['practice']
    for trial in trial_list:
        scores[trial['numTargets']][trial['numDistracts']] += trial['response.corr'] if trial['response.corr'] != '' else 0  # change '' to 0
        counts[trial['numTargets']][trial['numDistracts']] += 1
    
    instruct.text = u"""
SS1+0: %.2f %% of %i trials.
SS1+2: %.2f %% of %i trials
SS3+0: %.2f %% of %i trials
SS3+2: %.2f %% of %i trials

Stlačte \"R\" na zopakovanie alebo \"C\" na pokračovanie...
""" %(scores[1][0]/counts[1][0]*100, counts[1][0],
      scores[1][2]/counts[1][2]*100, counts[1][2],
      scores[3][0]/counts[3][0]*100, counts[3][0],
      scores[3][2]/counts[3][2]*100, counts[3][2])
    
    instruct.draw()
    win.flip()
    
    # Now wait for the experimenter's response. Repeat intro or continue
    key = event.waitKeys(keyList=['r', 'c'])[0]
    if key == 'r':
        run_intro()

def run_intro():
    """Runs the full introduction. Also called from the 'pracice_experimenter condition"""
    # Collect the appropriate trials for practice (ugly method, but it's short and efficient)
    practice_trials = []
    PRACTICE_CONDITIONS = [2, 4, 5, 6, 13, 16]  # condition indices for practice trials
    while PRACTICE_CONDITIONS:
        trial_list = make_trial_list('instructions')
        for trial in trial_list:
            if PRACTICE_CONDITIONS and trial['Condition'] == PRACTICE_CONDITIONS[0]:
                practice_trials += [trial]
                PRACTICE_CONDITIONS.pop(0)  # remove
    
    # Run instructions and practice
    image_task.draw()
    ask(TEXT_INTRO)
    run_block('pace_all', trial_list=[practice_trials[0]])
    while RESPONSE_DEVICE == 'mouse' and getMousePressed() is not None:  # wait for mouse release
        pass
    
    # Run practice with wait-for-subject
    image_response_pad.draw()
    ask(TEXT_PRACTICE0)
    ask(TEXT_PRACTICE1)
    run_block('pace_array', trial_list=practice_trials[1:6])
    
    # Run the actual practice
    ask(TEXT_PRACTICE2)
    run_block('practice_experimenter')

"""
RUN IT
"""
writer = csvWriter(prefix=start_info['save_file_path'] + '.csv')  # save I/O for when the experiment ends/python errors

# Run introduction. This will self-loop until experimenter tells it to continue.
run_intro()
