function detect_saccades_blinks(fn, sacc_threshold, bli_threshold, min_gap_sec)

PLOT = 1;

disp('Detecting saccades and blinks');

%%%% read matlab file
load([fn, '.mat'], 'data', 'markerCSV', 'annotation', 'header');

%%%% get sampling frequency
fs = header.sampleFreq;

%%%% get indexes of horizontal and vertical eog
channel_labels = header.labels;
for i = 1:length(channel_labels)
    switch channel_labels{i}
        case 'HEOG'
            heog_idx = i;
        case 'VEOG'
            veog_idx = i;
    end
end

%%%% select signal
heog = data.series(:, heog_idx);
veog = data.series(:, veog_idx);

% define filter
bandpass_freq = [0.1 5];
FIRlen = 50;
b = fir1(FIRlen, bandpass_freq / (fs/2));

% apply filters
heog_filtered = filter(b, 1, heog);
veog_filtered = filter(b, 1, veog);

% compute diff
diff_heog_filtered = diff(heog_filtered);
diff_veog_filtered = diff(veog_filtered);

% compute 1D signal
one_dim_signal = sqrt((diff_heog_filtered .^ 2) + (diff_veog_filtered .^ 2));

% detect saccades/blinks
min_gap = min_gap_sec * fs; % minimal gap in samples

saccades = [];
blinks = [];

found_saccade = 0;
found_blink = 0;

for i = 1:length(one_dim_signal)
    % compute sample number of last saccade, blink
    % if missing, keep min_gap
    last_blink = -min_gap;
    last_saccade = -min_gap;
    if ~isempty(blinks)
        last_blink = blinks(end);
    end
    if ~isempty(saccades)
        last_saccade = saccades(end);
    end
    last_event = max(last_blink, last_saccade);  % either saccade or blink

    % check for blink
    if one_dim_signal(i) > bli_threshold && ~found_blink && i - last_blink > min_gap
        blinks = [blinks, i];
        found_blink = 1;
        saccades = saccades(1:end-1);  % remove last saccade
    end
    
    % check for saccade
    if one_dim_signal(i) > sacc_threshold && ~found_saccade && i - last_event > min_gap
        saccades = [saccades, i];
        found_saccade = 1;
    end
    
    if one_dim_signal(i) < sacc_threshold
        found_saccade = 0;
    end
    
    if one_dim_signal(i) < bli_threshold
        found_blink = 0;
    end
end

%%%% append saccades + blinks
annotation = append_eog_events(annotation, saccades, 'EOG_saccade', fs);
annotation = append_eog_events(annotation, blinks, 'EOG_blink', fs);

% save everything to file
save([fn, '.mat'], 'data', 'markerCSV', 'annotation', 'header');

if PLOT
    figure('Name', 'EOG signal');
    hold on;
    
    plot(one_dim_signal);
    
    % dummy points for proper legend colors
    line([-1, -1], [-1, -1], 'Color', 'green');
    line([-1, -1], [-1, -1], 'Color', 'red');
    line([-1, -1], [-1, -1], 'Color', 'yellow');
    line([-1, -1], [-1, -1], 'Color', 'black');
    
    % set x limits
    xlim([0, length(one_dim_signal)]);

    % set y limits
    y_min = 0;
    y_max = 15;
    ylim([y_min, y_max]);
    % plot saccades
    for sacc_x = saccades
        line([sacc_x, sacc_x], [y_min, y_max], 'Color', 'green');
    end

    % plot blinks
    for blink_x = blinks
        line([blink_x, blink_x], [y_min, y_max], 'Color', 'red');
    end
    
    % plot markers
    for i = 1:length(annotation.event)
        event_type = annotation.event(i);
        event_type = event_type{1};
        event_time = annotation.sampleN(i);
        
        if strfind(event_type, 'arr')
            line([event_time, event_time], [y_min, y_max], 'Color', 'yellow');
        elseif strfind(event_type, 'RB')
            line([event_time, event_time], [y_min, y_max], 'Color', 'black');
        end
    end
    
    legend('signal', 'saccade', 'blink', 'trial start', 'trial response')
end

function annotation = append_eog_events(annotation, eog_events, event_type, fs)
annotation_event_idx = 1;
annotation_event_time = annotation.sampleN(annotation_event_idx);
for eog_event_time = eog_events
    inserted = 0;
    while ~inserted
        if eog_event_time < annotation_event_time
            annotation.event = [annotation.event(1:annotation_event_idx-1), event_type, annotation.event(annotation_event_idx:end)];
            annotation.sampleN = [annotation.sampleN(1:annotation_event_idx-1), eog_event_time, annotation.sampleN(annotation_event_idx:end)];
            annotation.starttime = [annotation.starttime(1:annotation_event_idx-1), eog_event_time/fs, annotation.starttime(annotation_event_idx:end)];
            annotation.duration = [annotation.duration(1:annotation_event_idx-1), 0.0039, annotation.duration(annotation_event_idx:end)];
            inserted = 1;
        end
        annotation_event_idx = annotation_event_idx + 1;
        if annotation_event_idx <= length(annotation.sampleN)
            annotation_event_time = annotation.sampleN(annotation_event_idx);
        else
            annotation_event_time = inf; % at the end of annotation array, append rest of eog events
        end
    end
end
