function mat2edf(fn)

disp(['Converting to EDF: ', fn, '.mat']);

reRefA2 = false; %%% change A2 to A2/2 for possible  re-reference 
linDetrend = false;  
% cutBlock=true; %%% needs to correctly check 

load([fn, '.mat'],'data','annotation','header')

nCh = length(header.labels);
%%%%% re-reference to linked mastoids
if reRefA2
    iA2 = find(strcmp(header.labels,'A2')==1);
    if isempty(iA2)
        error('Error: Prt som nasiel - ziadna A2')
    else
        refCh = data.series(:,iA2)/2;
        for ch = 1:nCh
            data.series(:,ch) = data.series(:,ch) - refCh;
        end
    end
    %%%% remove reference channel
    header.labels(iA2) = [];
    data.series(:,iA2) = [];
end

%%%%%%%%% detrend
if linDetrend
    treshDiff = header.sampleFreq*10; %%%% define tresholdiff to separate blocks
    diffB = diff(annotation.sampleN);
    poz = [find(diffB > treshDiff) length(annotation.sampleN)];

    for i = 1:length(poz)-1
        if i==1
            bg=annotation.sampleN(1);
        else
            bg=annotation.sampleN(poz(i-1)+1);
        end
        en = annotation.sampleN(poz(i));
        %%%%% detrend
        data.series(bg:en,:) = detrend(data.series(bg:en,:),'linear');
    end
end

%%%%%%%%%%% filtering data %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
fCut = 0.016; %%% Hz
dM = fdesign.highpass('Fst,Fp,Ast,Ap',fCut/2,fCut,3,1,header.sampleFreq);
fM = design(dM,'butter');
%save filterHighPass dM fM
for ch = 1:size(data.series,2)
    data.series(:,ch) = filtfilthd(fM,data.series(:,ch));
end

headerEDF.samplerate            = header.sampleFreq;
headerEDF.labels                = header.labels;
headerEDF.annotation.event      = annotation.event;
headerEDF.annotation.duration   = annotation.duration;
headerEDF.annotation.starttime  = annotation.starttime;

%%%% append addition info to filename
if linDetrend
    fn = [fn,'-dt-reRef'];
else
    fn = [fn,'-reRef'];
end

SaveEDF([fn,'.edf'], data.series, headerEDF);