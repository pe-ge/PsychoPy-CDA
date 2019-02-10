function eog_analyse(path_recordings, train_secs, sac_min_prob)

    disp('Doing EOG analysis');

    %%%% get matlab filename
    filename_mat = strsplit(path_recordings, filesep);
    filename_mat = filename_mat(end);
    filename_mat = filename_mat{1};
    filename_mat = [path_recordings, filesep, filename_mat, '.mat'];

    %%%% load matlab file
    load(filename_mat,'data','markerCSV','annotation','header');

    %%%% extract horizontal/vertical eog + sampling rate
    heog = data.series(:, 2);
    veog = data.series(:, 4);
    fs = header.sampleFreq;
    
    %%%% detect saccades and blinks
    [SAC_START, SAC_DUR, SAC_PROB, BLI_START, BLI_DUR, BLI_PROB] = eogert_offline(heog, veog, fs, train_secs)
    
    %%%% plot horizontal/vertical eog
    clf;
    hold on;

    plot(heog);
    plot(veog);
    
    %%%% plot saccades
    min_y = min([min(heog), min(veog)]);
    max_y = max([max(heog), max(veog)]);
    
    for idx = 1:size(SAC_START, 2)
        if SAC_PROB(idx) > sac_min_prob
            line([SAC_START(idx) * fs SAC_START(idx) * fs], [min_y max_y]);
        end
    end
end

