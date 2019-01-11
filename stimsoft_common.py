# -*- coding: utf-8 -*-
"""
Created on Wed Apr  6 09:56:13 2016

@author: jonas
"""
####################
# PsychoPy objects #
####################
import time
import os
import csv

#from tools import nasfiles # toto nie je treba RR
from os import path
from datetime import datetime  # cross-platform millisecond-timing

OUT_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'results')
save_file_name = "HK_Test1"
session = "1"

############
# Settings #
############



from psychopy import event, core
mouse = event.Mouse(visible=False)
clock = core.Clock()

# Dummy parallel if it isn't present on this system
# Nastavenie paraleleneho portu pre komunikaciu
try:
    from psychopy import parallel
    parallel.setPortAddress(0x3FF8)
    parallel.setData(0)
except Exception as err:
    print 'failed to use psychopy.parallel for the following reason:'
    print err
    class Parallel:
        def setData(self, code):
            #print 'just set parallel to %i' %code
            pass
    parallel = Parallel()

#########################
# Functions and classes #
#########################
def waitMousePressed(maxWait=float('inf'), keyList=[0,1,2], timeStamped=False, keyEvent='press', responseStart=0):
    """
    Equivalent to event.waitKeys but for the mouse.

    Returns the button_index if timeStamped=False (e.g. 2 for left key)
    Returns (button_index, duration) if timeStamped=True (e.g. (0, 4.343 for slow right key).
    Returns None if maxWait is exceeded. maxWait is infinite by default.
    keyEvent: 'press' to wait for presses of keyList, 'release' to wait for release of keyList.
    responseStart: minimum time (seconds) before starting to listen to responses
    """
    # Do not collect responses before this time has passed
    clock.reset()
    while clock.getTime() < responseStart:
        pass

    mouse.clickReset()
    mouse.mouseClock.reset()
    while True:
        if not mouse.mouseClock.getTime() >= maxWait:  # if we're still within the maxWait duration
            response = getMousePressed(keyList, timeStamped)
            if response is not None and response != (None, None):
                if keyEvent == 'release':
                    while getMousePressed(keyList) is not None:  # wait for mouse release
                        pass
                return response
        # Return None when maxWait is exceeded
        else:
            return (None, None) if timeStamped else None

def getMousePressed(keyList=[0,1,2], timeStamped=False):
    buttons, times = mouse.getPressed(getTime=True)  # get mouse presses
    for button in keyList:  # match presses with keyList
        if button is not None and buttons[button] == 1:
            return (button, times[button]) if timeStamped else button
    else:
        return (None, None) if timeStamped else None



def get_start_info(win):
    """ Gets script start info.
    Returns dictionary with the keys: save_file_path, session, start_time, frame_rate].
    Session is -1 if it is not detectible.
    If OUT_PATH doesn't exist, the data is saved in the script's directory.
    """
    #print 'get_start_info 1'
    # Get some data
    # save_file_name = nasfiles.get_latest_request_name()
    #print save_file_name
    #session = save_file_name.split('_')[-1]
    #if not session.isdigit():
    #    session = ''

    # Build return
    return_dict = {}
    #return_dict['save_file_path'] =  path.join(nasfiles.OUT_PATH, save_file_name) if os.path.exists(nasfiles.OUT_PATH) else save_file_name
    return_dict['save_file_path'] = OUT_PATH 
    return_dict['save_file_name'] = save_file_name 
    return_dict['session'] = session
    return_dict['start_time'] = datetime.strftime(datetime.now(), '%Y_%B_%d_%H%M')
    #return_dict['frame_rate'] = win.getActualFrameRate(nIdentical=30, threshold=0.5)
    #print 'framerate'
    #print return_dict['frame_rate']
    return_dict['frame_rate'] = 60

    return return_dict



# Timing
def get_utc(return_format='%Y-%m-%dT%H:%M:%S.%fZ'):
    """
    Get current time with millisecond precision.
    return_format can be 'unix' or a datetime.datetime.strftime format.
    """
    if return_format == 'unix':
        return (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
    else:
        return datetime.strftime(datetime.utcnow(), return_format)

def record_utc(trial, key, return_format='%Y-%m-%dT%H:%M:%S.%fZ'):
    """ Useful for win.callOnFlip(record_rt, trial, 'time_key') """
    trial[key] = get_utc(return_format)  # cross platform


class csvWriter(object):
    def __init__(self, prefix='', folder='', save_immediately=False, add_timestamp=False, delimiter='|'):
        """
        Creates a csv file and appends single rows to it using the csvWriter.write() function.
        Use this function to save trials. Writes a row in less than a millisecond.

        :prefix: str. The prefix to the file name.
        :folder: str. If empty, uses same directory as the py file
        :save_immediately: bool. whether to save to disk on each row (crash-safe but 2-3x) or flush on script exit (risk of data-loss on crash but 2-3x faster)
        :add_timestamp: bool. whether to add a timestamp as postfix to the file. Good to prevent overwriting!
        :delimiter: str. What to use as column delimiter in the save file.
        """
        self.delimiter = delimiter
        #print prefix 
        #print self 
        # Create folder if it doesn't exist
        if folder:
            folder += '/'
            if not os.path.isdir(folder):
                os.makedirs(folder)

        # Generate self.saveFile and self.writer
        self.saveFile = folder + str(prefix)
        if add_timestamp:
            self.saveFile += ' (' + time.strftime('%Y-%m-%d %H-%M-%S', time.localtime()) +').csv'  # Filename for csv. E.g. "myFolder/subj1_cond2 (2013-12-28 09-53-04).csv"
        if not save_immediately:
            self.writer = csv.writer(open(self.saveFile, 'a'), delimiter=delimiter).writerow  # The writer function to csv. It appends a single row to file
        else:
            self.writer = self._writer_immediate
        self.headerWritten = False

    def _write_immediate(self, trial):
        """
        Write a row to the csv file immediately and closing the file,
        thus making sure not to loose data on a crash. This is a bit slower
        than csvWriter.write by a factor of 3 or 4 but still <2ms.

        :trial: a dictionary.
        """
        #print 'pisem do suboru'
        #tsC = core.getTime()
        with open(self.saveFile, 'a') as file_object:
            if not self.headerWritten:
                self.headerWritten = True
                csv.writer(file_object, delimiter='|').writerow(trial.keys())
                #csv.writer(file_object, delimiter=',').writerow(trial.keys())
            csv.writer(file_object, delimiter='|').writerow(trial.values())
            #csv.writer(file_object, delimiter=',').writerow(trial.values())
        #print 'Writing time :', core.getTime() - tsC

    def write(self, trial):
        """Write a row to the csv. Note that this appends to an output buffer
        which is flushed to the file when python exits - also on most crashes.
        If this is unacceptable, use csvWriter._write_immediate. It is a bit
        slower.

        :trial: a dictionary"""
        # print 'pisem do suboru'
        # print trial
        if not self.headerWritten:
            self.headerWritten = True
            self.writer(trial.keys())
        self.writer(trial.values())