#
# This file will run the setup for fast state comparisons
# and execute the necessary tests.
# It is intended to be run in a shell environment.

#!/bin/bash

python stage1_database_loader.py
python stage2_normalization.py
python stage2_verification_updated.py
python enhanced_radar_v2_with_fast_state.py
python county_secure_dashboard.py