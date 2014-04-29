#!/bin/sh
#
# OpenPolarServer Public Build Wrapper

# clone the OPS repo
sudo -i;
mkdir /vagrant && cd /vagrant;
git clone https://github.com/cresis/OPS.git .;

# let the user download any data packs
printf "If you want to place custom datapacks (from the OPS) in the /vagrant/data/postgresql/ directory do so now.";
read -p "Press enter to continue ... ";

# run the ops build tool
sh conf/provisions.sh;