#!/bin/sh
#
# OpenPolarServer Public Build Wrapper

sudo -i <<EOF

notify-send "Preparing to build the OpenPolarServer"

mkdir /opt/ops && cd /opt/ops
git clone https://github.com/cresis/OPS.git .

printf "If you want to place custom datapacks (from the OPS) in the /opt/ops/data/postgresql/ directory do so now.\n\n"

read -p "Press enter to continue ... "

sh conf/provisions.sh

EOF
