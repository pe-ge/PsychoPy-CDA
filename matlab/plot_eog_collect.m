function plot_eog_collect(eog_fn)

if ~exist(eog_fn, 'file')
    disp('eog.hdf5 for given subject missing.');
    return
end

disp('Please create threshold.txt for given subject before closing the figure.');

fig = figure('Name', 'EOG signal');
hold on;

% read data
hdf5_data = ghdf5read(eog_fn);

%%%% get sampling frequency
fs = hdf5_data.RawData.AcquisitionTaskDescription.SamplingFrequency;

%%%% get markers
marker_types = hdf5_data.AsynchronData.TypeID;
marker_times = hdf5_data.AsynchronData.Time;

%%%% keep only most frequent marker
most_freq_marker_type = mode(marker_types);
idxs_keep = marker_types == most_freq_marker_type;

marker_types = marker_types(idxs_keep);
marker_times = marker_times(idxs_keep);

%%%% define start and end of signal
time_first_marker = marker_times(1) - fs/2; % minus half a second
time_last_marker = marker_times(end) + fs/2; % plus half a second

% filter marker times
marker_times = marker_times - time_first_marker;

%%%% get indexes of horizontal and vertical eog
channel_properties = hdf5_data.RawData.AcquisitionTaskDescription.ChannelProperties.ChannelProperties;
num_channels = length(channel_properties);
for i = 1:num_channels
    switch channel_properties(i).ChannelName
        case 'HEOG'
            heog_idx = i;
        case 'VEOG'
            veog_idx = i;
    end
end

%%%% select signal
heog = hdf5_data.RawData.Samples(heog_idx, time_first_marker:time_last_marker);
veog = hdf5_data.RawData.Samples(veog_idx, time_first_marker:time_last_marker);

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

% compute 1D signal and plot
one_dim_signal = sqrt((diff_heog_filtered .^ 2) + (diff_veog_filtered .^ 2));
plot(one_dim_signal);

% set x limits
xlim([0, length(one_dim_signal)]);

% set y limits
y_min = 0;
y_max = 15;
ylim([y_min, y_max]);

% plot push button markers
for marker_time = marker_times
    line([marker_time, marker_time], [y_min, y_max], 'Color', 'yellow');
end

% plot helper lines
for i = 1:5
    plot([0, length(one_dim_signal)], [i, i], '--', 'Color', 'red');
end

% wait until figure is closed
waitfor(fig);