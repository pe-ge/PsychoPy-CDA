function compPerformance(path_recordings)

disp('Calculating performance')

%%%% get matlab filename
filename_mat = strsplit(path_recordings, filesep);
filename_mat = filename_mat(end);
filename_mat = filename_mat{1};
filename_mat = [path_recordings, filesep, filename_mat, '.mat'];

%%%% prepare filename for results and open file
filename_results = [path_recordings, filesep, 'performance.txt'];
fid = fopen(filename_results, 'w');

%%%% load matlab file
load(filename_mat,'data','markerCSV','annotation','header');

nTrials=length(markerCSV.probe);

if nTrials~=length(markerCSV.nDist) | nTrials~=length(markerCSV.nTgt)
    error('s.t. wrong with numb probe and nDist or nTgt')
end

for i=1:nTrials
    sType{i}=[markerCSV.nTgt{i}, markerCSV.nDist{i}];
end

stimT=unique(sType);
lenStimT=length(stimT);

for s=1:lenStimT
    %%%% select indices for given combination of T + D
    idxs                   = find(strcmp(sType,stimT{s})==1);
    
    %%%% select responses and probes for given combination of T + D
    responses              = markerCSV.resp(idxs);
    probes                 = markerCSV.probe(idxs);
    
    %%%% count probes=change and response=Correct
    true_positive          = sum(strcmp(responses(find(strcmp(probes, 'change'))), 'Correct'));
    %%%% count probes=change and response=InCorrect
    false_positive         = sum(strcmp(responses(find(strcmp(probes, 'change'))), 'InCorrect'));
    %%%% count probes=change
    condition_positive     = sum(strcmp(probes, 'change'));
    
    %%%% count probes=change and response=Correct
    true_negative         = sum(strcmp(responses(find(strcmp(probes, 'same'))), 'Correct'));
    %%%% count probes=change and response=InCorrect
    false_negative        = sum(strcmp(responses(find(strcmp(probes, 'same'))), 'InCorrect'));
    %%%% count probes=change
    condition_negative    = sum(strcmp(probes, 'same'));
    
    num_total             = length(idxs);
    num_correct           = sum(strcmp(responses,'Correct'));
    num_missed            = sum(strcmp(responses,'Missed'));
    num_targets           = stimT{s}(1);
    num_distractors       = stimT{s}(2);
    
    %%%% caculate performance
    hit_rate = true_positive / condition_positive;
    false_alarm = false_negative / condition_negative;
    wmc = num_targets * (hit_rate - false_alarm);
    precision = true_positive / (true_positive + false_positive);
    recall = true_positive / (true_positive + false_negative);
    accuracy = num_correct / num_total;

    %%%% show in console
    str_performance = sprintf('T=%c, D=%c: MC=%.2f TP=%d FN=%d FP=%d TN=%d P=%.2f R=%.2f Acc=%.2f Miss=%d\n', num_targets, num_distractors, wmc, true_positive, false_negative, false_positive, true_negative, precision, recall, accuracy, num_missed);
    disp(str_performance)
    
    %%%% write to file
    fprintf(fid, 'T=%c, D=%c: MC=%.2f TP=%d FN=%d FP=%d TN=%d P=%.2f R=%.2f Acc=%.2f Miss=%d\n', num_targets, num_distractors, wmc, true_positive, false_negative, false_positive, true_negative, precision, recall, accuracy, num_missed);
end

fclose(fid);