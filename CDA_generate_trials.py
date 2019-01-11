from __future__ import division
import itertools
import random
import math
import numpy as np
import os
import json

from psychopy import core, gui

# Field parameters
MIN_DIST = 2.3  # cm
FIELD_HEIGHT = 7.6  # cm from bottom to top
FIELD_WIDTH = 4.8  # cm from center to extreme
CENTER_DIST = 1.5  # distance from vertical centerline to closest possible rect

# Rectangle parameters
ORIS = (0, 45, 90, 135)  # truly randomly sampled with replacement during experiment
TARGET_COLOR = 'red'
DISTRACTOR_COLORS = ('blue', 'green')

# Condition parameters (factorial design)
PROBE_TYPES = ('same', 'change')
CUES = ['left', 'right']
VISITS = 3

TRIALS_FOLDERNAME = 'trials'

# Functions

def show_gui_dlg():
    myDlg = gui.Dlg(title='Generate trials')

    myDlg.addField('Number of targets: ')
    myDlg.addField('Number of distractors: ')
    myDlg.addField('Number of blocks: ')
    myDlg.addField('Number of repetitions: ')
    
    while True: 
        data = myDlg.show()
        if myDlg.OK:
            try:
                Ntargets = tuple(eval(data[0] + ','))
                Ndistractors = tuple(eval(data[1] + ','))
                Nruns = int(data[2])
                Nrepetitions = int(data[3])
            except (ValueError, NameError, SyntaxError) as e:
                gui.warnDlg(prompt='ERROR: empty or incorrect values')
                continue

            break
        else: 
            return None

    trial_params = {
        'Ntargets': Ntargets,
        'Ndistractors': Ndistractors,
        'Nruns': Nruns,
        'Nrepetitions': Nrepetitions
    }
    
    return trial_params


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


def make_trial_list(trial_params):
    """ Make a list list of trials for the full experiment """
    trial_list = []
    for visit_day in range(VISITS):
        trial_list.append([])
        
        # Loop through blocks and randomize within blocks
        for block in range(trial_params['Nruns']):
            trials_block = []
            
            parameter_sets = itertools.product(range(trial_params['Nrepetitions']), trial_params['Ntargets'], trial_params['Ndistractors'], PROBE_TYPES, CUES)
            
            for repetition, n_targets, n_distractors, probe_type, cue in parameter_sets:
                # index of targets. First left indices and then right indices
                targets_left = random.sample(range(n_targets), n_targets)
                targets_right = random.sample(range(n_targets+n_distractors, n_distractors + 2*n_targets), n_targets)

                # calculate condition number
                condition = 1 + \
                                 (PROBE_TYPES.index(probe_type)==1)*1 + \
                                 (CUES.index(cue)==1)*2 + \
                                 (trial_params['Ndistractors'].index(n_distractors)==1)*4 + \
                                 (trial_params['Ntargets'].index(n_targets)==1)*8

                # Parameters of the trial type
                trial = {}
                trial['CueSide'] = cue
                trial['block'] = block + 1
                trial['numTargets'] = n_targets
                trial['numDistracts'] = n_distractors
                trial['Probe'] = probe_type
                trial['Condition'] = condition
                trial['ProbeCode'] = condition  # identical to as Condition. Delete?
            
                # Parameters of the rectangles
                trial['xys'] = spaced_xys(n_targets + n_distractors, -1) + spaced_xys(n_targets + n_distractors, 1)
                trial['oris'] = list(np.random.choice(ORIS, 2*(n_distractors+n_targets), replace=True))
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
                trial_list[-1] += [trial.copy()]
        
        # Add absolute trial number for the sake of analysis of effects of time
        for no, trial in enumerate(trial_list[-1]):
            trial['no_total'] = no
    return trial_list


if __name__ == '__main__':
    # show GUI dialogue
    trial_params = show_gui_dlg()
    # if Cancel clicked -> quit
    if trial_params is None:
        core.quit()

    # generate trials
    trial_list = make_trial_list(trial_params)
    
    # check whether trials folder exists
    if not os.path.isdir(TRIALS_FOLDERNAME):
        os.makedirs(TRIALS_FOLDERNAME)
        
    # prepare filename
    filename = 'T={Ntargets},D={Ndistractors},R={Nruns},B={Nrepetitions}.json'.format(**trial_params)
    # store trials
    with open(os.path.join(TRIALS_FOLDERNAME, filename), 'w') as f:
        json.dump(trial_list, f)