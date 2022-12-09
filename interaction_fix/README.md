# Add Dialogue Act and Emotio annotations to scenarios

1. Checkout this branch with `git checkout interaction_fix`
2. Change directory to `interaction_fix/`.
3. Run `./setup.sh` to download Midas model.
4. Copy scenarios into `data/` or change the path for the ScenarioStorage in `annotation.py`
5. Activate the virtual environment in `cltl-leolani-app/` with
   
   `source ../venv/bin/activate`

6. Run `python annotation.py` from this directory.
   **Run the script only once, otherwise annotations will be added multiple times!**