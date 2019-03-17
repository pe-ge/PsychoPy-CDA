function compPerformance(fn)

fn_mat = [fn, '.mat'];

%%%% load matlab file
load(fn_mat);

%%%% mark valid trials
if sum(cellfun(@sum, strfind(annotation.event, 'EOG'))) % if EOG markers present
    trial_id = 0;
    valid_trials = [];
    trial_started = 0;
    for i = 1:length(annotation.event)
        event_type = annotation.event(i);
        event_type = event_type{1};

        if strfind(event_type, 'arr') % start of the trial
            trial_started = 1;
            trial_id = trial_id + 1;
            valid_trial = 1;
        elseif sum(strfind(event_type, 'EOG')) && trial_started
            valid_trial = 0;
        elseif strfind(event_type, 'RB') % end of the trial
            trial_started = 0;
            if valid_trial
                valid_trials = [valid_trials, trial_id];
            end
        end
    end
    num_valid = length(valid_trials);
    num_invalid = length(markerCSV.probe) - num_valid;
    disp(['Num valid trials: ', num2str(num_valid)]);
    disp(['Num invalid trials: ', num2str(num_invalid)]);
    
    % remove invalid trials
    markerCSV.block = markerCSV.block(valid_trials);
    markerCSV.trial = markerCSV.trial(valid_trials);
    markerCSV.probe = markerCSV.probe(valid_trials);
    markerCSV.nDist = markerCSV.nDist(valid_trials);
    markerCSV.nTgt = markerCSV.nTgt(valid_trials);
    markerCSV.cueSide = markerCSV.cueSide(valid_trials);
    markerCSV.resp = markerCSV.resp(valid_trials);
    markerCSV.rt = markerCSV.rt(valid_trials);
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
disp('Calculating performance:');

nTrials = length(markerCSV.probe);
if nTrials ~= length(markerCSV.nDist) || nTrials ~= length(markerCSV.nTgt)
    error('s.t. wrong with numb probe and nDist or nTgt')
end

for i = 1:nTrials
    sType{i} = [markerCSV.nTgt{i}, markerCSV.nDist{i}];
end

stimT=unique(sType);
lenStimT=length(stimT);

%%%% prepare filename for results and open file
fn_results = [fn '.txt'];
fid = fopen(fn_results, 'w');

for s = 1:lenStimT
    %%%% select indices for given combination of T + D
    idxs = find(strcmp(sType,stimT{s})==1);
    
    %%%% select responses and probes for given combination of T + D
    responses = markerCSV.resp(idxs);
    probes = markerCSV.probe(idxs);
    
    %%%% count probes=change and response=Correct
    TP = sum(strcmp(responses(find(strcmp(probes, 'change'))), 'Correct'));
    %%%% count probes=change and response=InCorrect
    FP = sum(strcmp(responses(find(strcmp(probes, 'change'))), 'InCorrect'));
    %%%% count probes=change
    condP = sum(strcmp(probes, 'change'));
    
    %%%% count probes=same and response=Correct
    TN = sum(strcmp(responses(find(strcmp(probes, 'same'))), 'Correct'));
    %%%% count probes=same and response=InCorrect
    FN = sum(strcmp(responses(find(strcmp(probes, 'same'))), 'InCorrect'));
    %%%% count probes=same
    condN = sum(strcmp(probes, 'same'));
    
    num_total = length(idxs);
    num_correct = sum(strcmp(responses,'Correct'));
    num_missed  = sum(strcmp(responses,'Missed'));
    num_tgt = str2num(stimT{s}(1));
    num_dis = str2num(stimT{s}(2));
    
    %%%% caculate performance
    HR = TP / condP;  % hit rate
    FA = FN / condN;  % false alarm
    wmc = num_tgt * (HR - FA);
    precision = TP / (TP + FP);
    recall = TP / (TP + FN);
    accuracy = num_correct / num_total;

    %%%% show in console
    performance = sprintf('T=%d, D=%d: MC=%.2f TP=%d FN=%d FP=%d TN=%d P=%.2f R=%.2f Acc=%.2f Miss=%d', num_tgt, num_dis, wmc, TP, FN, FP, TN, precision, recall, accuracy, num_missed);
    disp(performance);
    
    %%%% write to file
    fprintf(fid, [performance, '\r\n']);
end

fclose(fid);