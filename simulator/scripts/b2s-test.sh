#!/bin/bash

if [ ! -f ./abides.py ]; then
    echo "Run from repo root directory"
    exit 1
fi
rm -rf log/b2s-*

SEED=$(((RANDOM) + 1))
CORES=$(nproc)
TRIALS=1
MAX_BOTS=1

if [[ $(($TRIALS % $MAX_BOTS)) != 0 ]]; then
    echo "Trials must be a multiple of max bots"
    exit 2
fi

seq $TRIALS | xargs -P $CORES -n 1 -I {} /bin/bash -c "\
    python3 ./abides.py -c bot2stock -l b2s-baseline-{}-\$(({} % ${MAX_BOTS} + 1)) -s \$((${SEED} + {})); \
    python3 ./abides.py -c bot2stock -a --bots \$(({} % ${MAX_BOTS} + 1)) -l b2s-attack-{}-\$(({} % ${MAX_BOTS} + 1)) -s \$((${SEED} + {})); \
"

echo "num_bots,profit-baseline,profit-attack,delta" > ~/b2s-eval.csv
for i in $(seq $TRIALS); do
    BOTS=$(ls log/b2s-baseline-$i-*/ExchangeAgent0.bz2 | cut -d '-' -f 4 | cut -d / -f 1)

    BASE_BEFORE=$(python3 cli/dump.py log/b2s-baseline-$i-*/BotmasterAgent*.bz2 STARTING_CASH | tail -n 1 | grep -o "[0-9]\+ \+STARTING_CASH$" | cut -d ' ' -f 1)
    BASE_AFTER=$(python3 cli/dump.py log/b2s-baseline-$i-*/BotmasterAgent*.bz2 ENDING_CASH | tail -n 1 | grep -o "[0-9]\+ \+ENDING_CASH$" | cut -d ' ' -f 1)
    ATTACK_BEFORE=$(python3 cli/dump.py log/b2s-attack-$i-*/BotmasterAgent*.bz2 STARTING_CASH | tail -n 1 | grep -o "[0-9]\+ \+STARTING_CASH$" | cut -d ' ' -f 1)
    ATTACK_AFTER=$(python3 cli/dump.py log/b2s-attack-$i-*/BotmasterAgent*.bz2 ENDING_CASH | tail -n 1 | grep -o "[0-9]\+ \+ENDING_CASH$" | cut -d ' ' -f 1)

    echo "${BOTS},$((BASE_AFTER - BASE_BEFORE)),$((ATTACK_AFTER - ATTACK_BEFORE)),$(((ATTACK_AFTER - ATTACK_BEFORE) - (BASE_AFTER - BASE_BEFORE)))" >> ~/b2s-eval.csv
done
