clc

DATA_FN = 'Data';
SUBJECT_FN = '014';
RECORDING_FN = '014 CDT preTRAIN1 C01-LKE-D1 15-03-2019 11-36-25';
MIN_GAP_SEC = 0.5;  % minimal gap between saccades/blinks in seconds

% prepare filenames
full_fn = [DATA_FN, '\', SUBJECT_FN, '\', RECORDING_FN];
eog_fn = [DATA_FN, '\', SUBJECT_FN, '\eog.hdf5'];
thresholds_fn = [DATA_FN, '\', SUBJECT_FN, '\thresholds.txt'];

%%%% if threshold not created yet
if ~exist(thresholds_fn, 'file')
    plot_eog_collect(eog_fn);
end

%%%% run conversion and create matlab file 
hdf5csv2mat(full_fn)

%%%% read thresholds from file
if  exist(thresholds_fn, 'file')
    [sacc_threshold, bli_threshold] = read_thresholds(thresholds_fn);
    
    detect_saccades_blinks(full_fn, sacc_threshold, bli_threshold, MIN_GAP_SEC);
else
    disp('Treshold file for given subject not provided.');
end

%%%% convert matlab file to edf 
mat2edf(full_fn)

%%%% compute performance amd writes results of to a csv file
compPerformance(full_fn)