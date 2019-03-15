clc
% to be called from the directry containing filename.hdf5 and filename.csv

%fn = '011 CDT preTRAIN1 C01-LKE-D2 14-03-2019 13-16-18'; %%% ZLY
%fn = '011 CDT preTRAIN1 C01-LKE-D1 12-03-2019 13-07-13';
%fn = '012 CDT preTRAIN1 C01-LKE-D1 13-03-2019 11-58-18';
%fn = '013 CDT preTRAIN1 C01-LKE-D1 13-03-2019 12-59-33';
fn = '013 CDT preTRAIN1 C01-LKE-D2 14-03-2019 12-36-00';

%%%% run conversion and create matlab file 
hdf5csv2mat(fn)

%%%% convert matlab file to edf 
mat2edf(fn)

%%%% compute performance amd writes results of to a csv file
compPerformance(fn)