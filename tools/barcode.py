#! C:\Program Files (x86)\PsychoPy2 python.exe
# -*- coding: utf-8 -*-
"""
This module presents the barcode pulses that signal the beginning
of a task to the photodiode hardware.
"""

from __future__ import division
from psychopy import core
from psychopy.visual.rect import Rect

from datetime import datetime

class BarcodePulse(Rect):
    """
    Square image underneath photodiode sensor.
    """
    def __init__(self, win, **kwargs):
        kwargs["units"] = "pix"
        kwargs["fillColor"] = "black"
        kwargs["lineColor"] = None
        # Constant position of the photodiode on the LCD screen.
        kwargs["width"] = 40
        kwargs["height"] = 40
        kwargs["pos"] = [-((win.size[0] - kwargs["width"]) / 2), 0]
        super(BarcodePulse, self).__init__(win, **kwargs)
        # Store a list of UTC times.
        self.utc_timestamps = []
        # These event codes are converted into int in BDF.
        self.triggers = ("p", "u", "l", "s", "e")
        # Frame durations
        self.num_frames_on = 2
        self.num_frames_off =  2
        self.num_pulses = 5

    def start(self):
        """draw the barcode sequence"""
        for i in xrange(self.num_pulses):
            self.fillColor = "white"
            for j in xrange(self.num_frames_on):
                self.draw()
                self.win.flip()
                if j == 0:
                    # Only store the time of the first occuring on frame.
                    self.utc_timestamps.append(datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S.%fZ'))
            self.fillColor = "black"
            for j in xrange(self.num_frames_off):
                self.draw()
                self.win.flip()

    def _add_utc(self):
        self.utc_timestamps.append(datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S.%fZ'))

    def run(self):
        self.fillColor = 'black'
        self.draw()
        self.win.flip()
        core.wait(1.000)
        for i in xrange(self.num_pulses):
            self.fillColor = "white"
            self.win.callOnFlip(self._add_utc)
            self.draw()
            self.win.flip()
            core.wait(float(self.num_frames_on) / 60.)
            self.fillColor = "black"
            self.draw()
            self.win.flip()
            core.wait(float(self.num_frames_off) / 60.)
