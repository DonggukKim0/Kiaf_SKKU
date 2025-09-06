# Kiaf_SKKU

RUN!!!!!!

---

## Setup

### 1) Configure the `load.sh` Script

To properly set up the environment, follow these steps:

1. Generate the environment snapshot:
   ```bash
   sh alienv printenv O2Physics/latest >> alienv_envset.sh
   ```
2. Enter the O2Physics environment:
   ```bash
   sh alienv enter O2Physics/latest
   ```
3. Retrieve your current `PATH`:
   ```bash
   sh echo $PATH
   ```
4. Append the `PATH` you just printed to the end of `alienv_evnset.sh` (replace `<PATH_FROM_ECHO>` with the actual output from step 3):
   ```bash
   sh echo 'export PATH=<PATH_FROM_ECHO>:$PATH' >> alienv_envset.sh
   ```
---

### 2) Modifying `runCondor.py`

Ensure that `runCondor.py` is properly set up and executable. Make the following modifications:

- **Keep the filename consistent** between `configuration.json` and the `sed` command used in run scripts.
  - In `configuration.json`, under the key:
    ```json
    "aod-file": "@<filename>"
    ```
  - Ensure the `sed` command uses the same `<filename>`:
    ```bash
    sed -i 's/<filename>/list$2/g' configuration.json
    ```
  - **The `<filename>` in both places must be identical.**

- **Do not redirect stdout to a log file** in each run script.
  - **Change this (remove `> stdout.log`):**
    ```bash
    o2-analysis-pid-tof -b --configuration json://configuration.json --aod-file @{mainDir}/{workDir}/macro/list$2 > stdout.log
    ```
  - **To this (no redirection so errors remain visible):**
    ```bash
    o2-analysis-pid-tof -b --configuration json://configuration.json --aod-file @{mainDir}/{workDir}/macro/list$2
    ```

> Rationale: redirecting to `stdout.log` can hide on-screen errors from Condor/DPL, making debugging harder.