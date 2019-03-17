function [sacc_threshold, bli_threshold] = read_thresholds(thresholds_fn)

fid = fopen(thresholds_fn, 'r');

% read and ignore header
fgets(fid);

% read thresholds
thresholds = textscan(fgets(fid), '%s', 'delimiter',',');
sacc_threshold = str2num(thresholds{1}{1});
bli_threshold = str2num(thresholds{1}{2});

fclose(fid);