#!/bin/sh
# Requirement: a 1-D array of 150,000 elements. The upstream solution saving
# the distribution as a (150000, 1) column.
cd /app
sh "$(dirname "$0")/reference.sh"
sed -i 's/np\.save(SAVE_PATH, P)/np.save(SAVE_PATH, P.reshape(-1, 1))/' /app/search_distributions.py
rm -f /app/dist.npy
python /app/search_distributions.py
