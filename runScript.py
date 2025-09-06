#!/usr/bin/env python3
import shutil
from datetime import datetime
import subprocess
import pathlib
import os 
os.umask(0)

MAINGENERATOR = "O2Data" # name of optns file, must be placed in the same folder of this script
USER_MAIL = "dongguk.kim@cern.ch"
USER_SCRIPT = ""
POST_SCRIPT = ""

## Default values
inputDataListFile = "inputdata_LHC22o_pass7.txt" # Data
inputFiles=f"configuration.json"
numberOfFilesPerJob = 10
totalEvents = int(subprocess.check_output(['wc', '-l', inputDataListFile]).split()[0]) // numberOfFilesPerJob
print(f"Total events: {totalEvents}")

request_RAM = "8GB" # test result was 1.7GB (1637~1647)

# Below should not be modified ##########################################
now=datetime.now().strftime("%Y%m%d_%H%M%S")
workDir=f"{now}_{MAINGENERATOR}"
mainDir=os.path.dirname(os.path.realpath(__file__))
inputFileArray = inputFiles.split(",")
# inputFileArrayIncludingRunMacro = inputFileArray+[runMacro] # Don't need for the moment.

## Preparing the run
# Make paths
pathlib.Path(f"{mainDir}/{workDir}/macro").mkdir(parents=True, exist_ok=True)
pathlib.Path(f"{mainDir}/{workDir}/out").mkdir(parents=True, exist_ok=True)
pathlib.Path(f"{mainDir}/{workDir}/logs").mkdir(parents=True, exist_ok=True)

for number in range(totalEvents):
    pathlib.Path(f"{mainDir}/{workDir}/out/{number}").mkdir(parents=True, exist_ok=True)

# Copy input files
# for inputfiles in inputFileArrayIncludingRunMacro: # Don't need for the moment.
for inputfiles in inputFileArray:
    shutil.copy(inputfiles, f"{mainDir}/{workDir}/macro/")

# Split input data file into smaller files
def split_file(input_file, lines_per_file, output_dir):
    with open(input_file, 'r') as file:
        lines = file.readlines()

    os.makedirs(output_dir, exist_ok=True)

    for i in range(0, len(lines), lines_per_file):
        chunk = lines[i:i + lines_per_file]
        suffix = str(i // lines_per_file)
        output_file = os.path.join(output_dir, f'list{suffix}')
        
        with open(output_file, 'w') as out_file:
            out_file.writelines(chunk)

# Example usage
split_file(inputDataListFile, numberOfFilesPerJob, f"{mainDir}/{workDir}/macro")


# Make run.sh file (main macro)
fRunScript = open(f"{mainDir}/{workDir}/macro/run.sh", "a")
fRunScript.write(f"""#!/bin/bash

echo "INIT! $1 $2 $3 $4 $5"
export PATH=$PATH:/usr/bin

cp /alice/home/dongguk/.tmp/* /tmp/

#Modify the input list
sed -i 's/input_data.txt/list$2/g' configuration.json

source alienv_envset.sh


echo "Environment:"
env

start_time=$(date +%s)

o2-analysis-timestamp --configuration json://configuration.json  -b | \
o2-analysis-event-selection --configuration json://configuration.json  -b | \
o2-analysis-track-propagation --configuration json://configuration.json -b | \
o2-analysis-tracks-extra-v002-converter --configuration json://configuration.json -b | \
o2-analysis-trackselection --configuration json://configuration.json  -b | \
o2-analysis-multiplicity-table --configuration json://configuration.json  -b | \
o2-analysis-je-jet-deriveddata-producer --configuration json://configuration.json  -b | \
o2-analysis-je-jet-finder-data-charged --configuration json://configuration.json  -b | \
o2-analysis-je-dijet-finder-charged-qa --configuration json://configuration.json -b --aod-file @{mainDir}/{workDir}/macro/list$2 

end_time=$(date +%s)
elapsed_time=$((end_time - start_time))
echo "Running time: $elapsed_time sec"

#alienv unload O2Physics

ls -althr # Check the output files before finish
echo "DONE!"
""")
fRunScript.close()

# Make some condor input files
# Executable              = {workDir}/macro/{runMacro}
# transfer_input_files    = {runMacro},{inputFiles}
fCondorSub = open(f"{mainDir}/{workDir}/macro/condor.sub", "a")
fCondorSub.write(f"""Universe                = vanilla
Executable              = {workDir}/macro/run.sh
Accounting_Group        = group_alice
JobBatchName		    = {workDir}_$(process)
Log                     = {workDir}/logs/$(process).log
Output                  = {workDir}/$(process).out
Error                   = {workDir}/$(process).error

request_cpus            = 1
request_memory          = {request_RAM}
request_disk            = 100MB
transfer_input_files    = run.sh,{inputFiles},load.sh
transfer_output_files   = AnalysisResults.root, dpl-config.json
arguments               = "$(Opt) $(process)"
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
periodic_remove = (CurrentTime - EnteredCurrentStatus) > 86400
output_destination      = file://{mainDir}/{workDir}/out/$(process)/
Notification            = Always
Notify_user             = {USER_MAIL}
Queue {totalEvents} Opt in ({MAINGENERATOR})
""")
fCondorSub.close()

# with open(os.open(f"{mainDir}/{workDir}/macro/merge.sh", os.O_CREAT | os.O_WRONLY, 0o777), 'a') as fPostScript:
#     fPostScript.write(f"""#!/bin/bash
#     cd {mainDir}/{workDir}
#     ls -alth
#     echo "No merge needed at the moment!"
#     """)

fCondorDag = open(f"{mainDir}/{workDir}/macro/condor.dag", "a")
fCondorDag.write(f"""JOB A {workDir}/macro/condor.sub
""")
fCondorDag.close()

process = subprocess.Popen([f'condor_submit_dag -batch-name {MAINGENERATOR}_{totalEvents} -force -notification Always -append "Accounting_Group=group_alice" -append "notify_user={USER_MAIL}" {workDir}/macro/condor.dag'], shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = process.communicate()
print(stdout.decode("utf-8"))
