function hdf5csv2mat(path_recordings, filename_hdf5, filename_csv)

markerCSV.minRT=0.2; %%%% define min RT in sec to consider correct response, 0.200 sec ? 

disp(['Processing file: ',filename_hdf5]);

dat = ghdf5read([path_recordings, filesep, filename_hdf5]);
%%%% EEG
data.series=dat.RawData.Samples'; %%%% samples x channels
header.sampleFreq=dat.RawData.AcquisitionTaskDescription.SamplingFrequency;

%%%% individual channels propreties
for i=1:length(dat.RawData.AcquisitionTaskDescription.ChannelProperties.ChannelProperties)
    chP(i)=dat.RawData.AcquisitionTaskDescription.ChannelProperties.ChannelProperties(i);
    header.labels{i}=chP(i).ChannelName;
    %header.labels{i}=['Ch',num2str(i)];
end

%%%% Digital Channels
vID=dat.AsynchronData.TypeID;
mT=dat.AsynchronData.Time;

%%%% individual channels propreties
for i=1:length(dat.AsynchronData.AsynchronSignalTypes.AsynchronSignalDescription)
    %dChP(i)=dat.AsynchronData.AsynchronSignalTypes.AsynchronSignalDescription(i);
    marker.id(i)  =dat.AsynchronData.AsynchronSignalTypes.AsynchronSignalDescription(i).ID;
    marker.desc{i}=dat.AsynchronData.AsynchronSignalTypes.AsynchronSignalDescription(i).Description;
end

emptyCells={[]  []  []  []  []  []  []  []};
cellCheck={'pushRed'  'pushGreen'  'fotoDiod'  'pp1'  'pp2'  'pp3'  'pp4'};

%%%% wheck whether marker desc missing
if size(marker.desc, 2) == 8 && sum(~cellfun(@strcmp, marker.desc, emptyCells))
    marker.desc = {'pushRed'  'pushGreen'  ''  'fotoDiod'  'pp1'  'pp2'  'pp3'  'pp4'};
    marker.id(3) = [];  %%%% remove marker ID that is not used (gTec 3rd DIO)

%%%% check whether marker desc doesnt match cellCheck
elseif sum(~cellfun(@strcmp, marker.desc, cellCheck))
    error('s.t. wrong with cells check ....')
end

%%%% remove if first is fotodiod
if vID(1)==marker.id(3)
    timeD=(mT(2)-mT(1))/header.sampleFreq;
    if timeD > 3 %%% more than 3 sec difference - remove 
        vID(1)=[]; 
        mT(1)=[]; 
    else 
        error('Something wrong with the first fotodiod') 
    end 
end 

mL=[];
for i=1:length(vID)
    switch vID(i)
        case marker.id(1) %%%% pushGreen
            mL{i}='RBsame';
        case marker.id(2) %%%% pushRed
            mL{i}='RBchange';
        case marker.id(3) %%%% fotoDiod
            switch vID(i-1)
                case marker.id(4) %%%% TA is either pp1 pp2 or pp2 pp1
                    if i > 2
                        switch vID(i-2)
                            case marker.id(5)
                                mL{i}='testArray';
                            otherwise
                                mL{i}='arrLeft';
                        end
                    else
                        mL{i}='arrLeft';
                    end
                case marker.id(5)
                    if i > 2
                        switch vID(i-2)
                            case marker.id(4)
                                mL{i}='testArray';
                            otherwise
                                mL{i}='arrRight';
                        end
                    else
                        mL{i}='arrRight';
                    end
                case marker.id(6)
                    mL{i}='same';
                case marker.id(7)
                    mL{i}='change';
            end
        otherwise
            mT(i)=0;
    end
end

%%%%%% now read csv
disp(['Processing file: ',filename_csv]);

fidE=fopen([path_recordings, filesep, filename_csv],'r');

%%%%% read csv header
tline = fgets(fidE);
strP1=textscan(tline,'%s','delimiter','|');
lenStrP1=length(strP1{1});
%%%
iTrial=find(strcmp(strP1{1},'no_block')==1);
iBlock=find(strcmp(strP1{1},'block')==1);
iNdist=find(strcmp(strP1{1},'numDistracts')==1);
iNtarget=find(strcmp(strP1{1},'numTargets')==1);
iProbe=find(strcmp(strP1{1},'Probe')==1); %%% 'change' or 'same'
iCueSide=find(strcmp(strP1{1},'CueSide')==1); %%% 'left' or 'right'

%%%% read trials data
ct=1;
tline = fgets(fidE);
while ischar(tline)
    strP=textscan(tline,'%s','delimiter','|');
    if length(strP{1})==lenStrP1
        switch char(strP{1}(iProbe))
            case {'same','change'} %%%%% selects memory array only
                markerCSV.block(ct)=str2double(strP{1}(iBlock));
                markerCSV.trial(ct)=str2double(strP{1}(iTrial));
                markerCSV.probe{ct}=char(strP{1}(iProbe));
                markerCSV.nDist{ct}=char(strP{1}(iNdist));
                markerCSV.nTgt{ct}=char(strP{1}(iNtarget));
                markerCSV.cueSide{ct}=char(strP{1}(iCueSide));
                ct=ct+1;
        end
    end
    tline = fgets(fidE);
end
fclose(fidE);

%%%% check MA type
iC=find(strcmp(mL,'change')==1);
iS=find(strcmp(mL,'same')==1);
iM=sort([iC, iS]);
if length(mL(iM)) < length(markerCSV.probe)
    [mL,mT,markerCSV]=checkmL(mL,mT,markerCSV);
elseif length(mL(iM)) > length(markerCSV.probe)
    [mL,mT,markerCSV]=checkmL(mL,mT,markerCSV);
    % error('Missing MA in csv ?')
elseif sum(~cellfun(@strcmp, mL(iM),markerCSV.probe))
    error('Memory Array types do not match')
end


%%% clear markers from parallel port
ii=find(mT==0);
mT(ii)=[];
mL(ii)=[];
%%%%% check resposnses and remove discrepancies
remI=[];
for i=1:(length(mL)-1)
    switch mL{i}
        case {'RBsame','RBchange'}
            if ~strcmp(mL{i-1},'testArray')
                disp('Response outside of the correct interval  ... removed')
                remI=[remI,i]; %mL(i)=[];mT(i)=[];
            else
                if ~(strcmp(mL{i+1},'arrRight') | strcmp(mL{i+1},'arrLeft'))
                    remI=[remI,i,i+1];
                    disp('More than one response ... removing all ....but code later .... ')
                end
            end
    end
end
%%%% remove wrong
if ~isempty(remI)
    mL(remI)=[];mT(remI)=[];
end

%%%% extract responses
ctI=1;
%%%% transfer mT to sec 
mT=double(mT);
for i=1:length(mL)
    switch mL{i}
        case 'same'
            if length(mL)>=i+2
                if strcmp(mL{i+2},'RBsame')
                    markerCSV.rt(ctI)=(mT(i+2)-mT(i+1))/header.sampleFreq;
                    if markerCSV.rt(ctI) < markerCSV.minRT
                        markerCSV.resp{ctI}='InCorrect';
                    else
                        markerCSV.resp{ctI}='Correct';
                    end
                elseif strcmp(mL{i+2},'RBchange')
                    markerCSV.resp{ctI}='InCorrect';
                    markerCSV.rt(ctI)=(mT(i+2)-mT(i+1))/header.sampleFreq;
                else
                    markerCSV.resp{ctI}='Missed';
                    markerCSV.rt(ctI)=0;
                end
            else %%%% missing last 
                markerCSV.resp{ctI}='Missed';
                markerCSV.rt(ctI)=0;
            end
            ctI=ctI+1;
        case 'change'
            if length(mL)>=i+2
                if strcmp(mL{i+2},'RBchange')
                    markerCSV.rt(ctI)=(mT(i+2)-mT(i+1))/header.sampleFreq;
                    if markerCSV.rt(ctI) < markerCSV.minRT
                        markerCSV.resp{ctI}='InCorrect';
                    else
                        markerCSV.resp{ctI}='Correct';
                    end
                elseif strcmp(mL{i+2},'RBsame')
                    markerCSV.resp{ctI}='InCorrect';
                    markerCSV.rt(ctI)=(mT(i+2)-mT(i+1))/header.sampleFreq;
                else
                    markerCSV.resp{ctI}='Missed';
                    markerCSV.rt(ctI)=0;
                end
            else %%%% missing last 
                markerCSV.resp{ctI}='Missed';
                markerCSV.rt(ctI)=0;
            end
            ctI=ctI+1;
    end
end
% markerCSV.rt=(double(markerCSV.rt)/header.sampleFreq)*1000; %%% in ms

%%%% create strings for MA
for i=1:length(markerCSV.block)
    switch markerCSV.cueSide{i}
        case 'left'
            maL{i}=['S',markerCSV.nTgt{i},markerCSV.nDist{i},'_',markerCSV.resp{i},'_Left'];
        case 'right'
            maL{i}=['S',markerCSV.nTgt{i},markerCSV.nDist{i},'_',markerCSV.resp{i},'_Right'];
    end
end

%%%%% structure for EDF annotations
ind1=1;
durM=1/header.sampleFreq; %%%% each marker one sample

for i=1:length(mT)
    annotation.sampleN(i)=double(mT(i));
    %  annotation.starttime(i)=double(mT(i)/header.sampleFreq);
    %  annotation.duration(i)=durM;
    switch mL{i}
        case {'same','change'}
            annotation.event{i}=maL{ind1};
            ind1=ind1+1;
        otherwise
            annotation.event{i}=mL{i};
    end
end
annotation.starttime=annotation.sampleN/header.sampleFreq;
annotation.duration=ones(1,length(annotation.starttime))*durM;

%%%% extract filename of directory with recordings
%%%% will be used for output filename
filename = strsplit(path_recordings, filesep);
filename = filename(end);
filename = filename{1};

save([path_recordings, filesep, filename, '.mat'],'data','markerCSV','annotation','header')

%%%%% function check mL 
function [mL,mT,markerCSV]=checkmL(mL,mT,markerCSV) 

newmL=mL;
delmP=[];
delmL=[]; 
ind=1;indP=1;

%%%%% find missing MA foto diod 
while ind <= length(mL)
    if isempty(mL{ind}) & isempty(mL{ind+1}) & isempty(mL{ind+2}) & isempty(mL{ind+3}) & isempty(mL{ind+4})
        error('ML error: More than 4 empty cells in a row')
    elseif isempty(mL{ind}) & isempty(mL{ind+1}) & isempty(mL{ind+2}) & isempty(mL{ind+3})
        delmL=[delmL,ind];
        mL{ind+1}='missingFD';
        ind=ind+4;
    elseif isempty(mL{ind}) & isempty(mL{ind+1}) & isempty(mL{ind+2})
        delmL=[delmL,ind];
        mL{ind+1}='missingFD';
        ind=ind+3;
    else
        ind=ind+1;
    end
end

%%%% find position of these trials in CSV 
iC=find(strcmp(mL,'change')==1);
iS=find(strcmp(mL,'same')==1);
iM=find(strcmp(mL,'missingFD')==1);
iAll=sort([iC, iS, iM]);

iR=find(strcmp(mL(iAll),'missingFD')==1);

%%%%% remove these CSV trials 
markerCSV.block(iR)=[];
markerCSV.probe(iR)=[];
markerCSV.nDist(iR)=[];
markerCSV.nTgt(iR)=[];
markerCSV.cueSide(iR)=[];

%%%%%% remove trials in Markers 
indR=[]; 
for i=1:length(delmL)
    iP=delmL(i);
    if ~(strfind(mL{iP-1},'arr') & isempty(mL{iP-2}))
        error('can not remove backward')
    end
    sF=true;
    jj=1;
     while sF
         if strfind(mL{iP+jj},'testArray')
            sF1=true;
            while sF1
                if isempty(mL{iP+jj})
                    sF1=false;sF=false;
                else
                    jj=jj+1;
                end
            end
         else
             jj=jj+1;
         end
     end
     indR=[indR,iP-2:iP+5];
end
mL(indR)=[]; 
mT(indR)=[]; 

%%%%% check again if correct
iC=find(strcmp(mL,'change')==1);
iS=find(strcmp(mL,'same')==1);
iM=sort([iC, iS]);

iM
length(markerCSV.probe)
if length(iM) > length(markerCSV.probe)
    disp('Warnninig missing CSV records !!! : need to cut '); 
    %%%%% cut the missing %%%%% 
    iM=iM(1:length(markerCSV.probe));
    findNextArr=true;indS=iM(end);  
    while findNextArr
        if strfind(mL{indS},'arr')
            findNextArr=false; 
        else 
            indS=indS+1; 
        end 
    end 
    if ~cellfun(@isempty,mL(indS-1))
        error('inds-1 is not emppy - that mean pp arroew') 
    else 
        mL=mL(1:indS-2); 
        mT=mT(1:indS-2); 
    end    
end
 mL(iM)
 markerCSV.probe
if sum(~cellfun(@strcmp, mL(iM),markerCSV.probe))
    error('Memory Array types still do not match')
end









