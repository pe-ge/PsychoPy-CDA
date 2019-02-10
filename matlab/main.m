clc

%%%% path to directory with all recordings
dir_data = ['.', filesep, 'Data'];
%%%% filename of recording to process
filename_recording = 'KS02_CDT42019.02.06_12.09.27';
%%%% full path to directory with recording
path_recordings = [dir_data, filesep, filename_recording];

%%%% obtain filenames of hdf5 and csv files
filename_hdf5 = '';
filename_csv = '';
all_files = dir(path_recordings);
for file_idx = 1:length(all_files)
    filename = all_files(file_idx).name;
    filename_splitted = strsplit(filename, '.');
    extension = filename_splitted(end);
    switch extension{1}
        case 'hdf5'
            filename_hdf5 = filename;
        case 'csv'
            if ~strcmp(filename, 'performance.csv')
                filename_csv = filename;
            end
    end
end

%%%% run conversion and create matlab file 
%%%% the matlab filename is created from dir_recording
hdf5csv2mat(path_recordings, filename_hdf5, filename_csv)

%%%% convert matlab file to edf 
mat2edf(path_recordings)

%%%% compute performance amd writes results of to a csv file
compPerformance(path_recordings)

%%%% eog analysis
eog_analyse(path_recordings, 30, 0.95)