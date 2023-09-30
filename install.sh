#!/bin/bash

# Led Trailer Sign Install Script
SIGNBRANCH=${SIGNBRANCH:-"master"}
SIGNIMAGEVER="2023-09"
SIGNCFGVER="1"
SIGNPLATFORM="UNKNOWN"
SIGNDIR=/opt/ledsign
SIGNUSER=SIGN
SIGNHOME=/home/${FPPUSER}
OSVER="UNKNOWN"

# Make sure the sbin directories are on the path as we will
# need the adduser/addgroup/ldconfig/a2enmod/etc... commands
PATH=$PATH:/usr/sbin:/sbin

# CPU Count
CPUS=$(grep "^processor" /proc/cpuinfo | wc -l)
if [[ ${CPUS} -gt 1 ]]; then
    MEMORY=$(grep MemTot /proc/meminfo | awk '{print $2}')
    if [[ ${MEMORY} -lt 425000 ]]; then
        # very limited memory, only use one core or we'll fail or
        # will be very slow as we constantly swap in/out
        CPUS=1
    elif [[ ${MEMORY} -lt 512000 ]]; then
        SWAPTOTAL=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
        # Limited memory, if we have some swap, we'll go ahead with -j 2
        # otherwise we'll need to stick with -j 1 or we run out of memory
        if [[ ${SWAPTOTAL} -gt 49000 ]]; then
            CPUS=2
        else
            CPUS=1
        fi
    fi
fi
        
#############################################################################
# Gather some info about our system
. /etc/os-release
OSID=${ID}
OSVER="${ID}_${VERSION_ID}"
if [ "x${PRETTY_NAME}" = "x" ]
then
	echo "ERROR: /etc/os-release does not exist, will not install"
	exit
fi

if [ "x${OSID}" = "x" ]
then
	echo "ERROR: /etc/os-release does not contain OS ID, will not install"
	exit
fi

# Parse build options as arguments
clone_sign=true
build_vlc=true
skip_apt_install=false
desktop=true
isimage=false;

MODEL=""
if [ -f /proc/device-tree/model ]; then
    MODEL=$(tr -d '\0' < /proc/device-tree/model)
fi
# Attempt to detect the platform we are installing on
if [ "x${OSID}" = "xraspbian" ]
then
	SIGNPLATFORM="Raspberry Pi"
	OSVER="debian_${VERSION_ID}"
    isimage=true
    desktop=false
elif [ -e "/sys/class/leds/beaglebone:green:usr0" ]
then
	SIGNPLATFORM="BeagleBone Black"
    isimage=true
    desktop=false
elif [ -f "/etc/armbian-release" ]
then
    SIGNPLATFORM="Armbian"
    isimage=true
    desktop=false
elif [[ $PRETTY_NAME == *"Armbian"* ]]
then
    SIGNPLATFORM="Armbian"
    isimage=true
    desktop=false
elif [ "x${OSID}" = "xdebian" ]
then
	SIGNPLATFORM="Debian"
elif [ "x${OSID}" = "xubuntu" ]
then
	SIGNPLATFORM="Ubuntu"
elif [ "x${OSID}" = "xlinuxmint" ]
then
	SIGNPLATFORM="Mint"
elif [ "x${OSID}" = "xfedora" ]
then
    SIGNPLATFORM="Fedora"
else
	SIGNPLATFORM="UNKNOWN"
fi

while [ -n "$1" ]; do
    case $1 in
        --skip-clone)
            clone_sign=false
            shift
            ;;
        --skip-vlc)
            build_vlc=false
            shift
            ;;
        --skip-apt-install)
            skip_apt_install=true
            shift
            ;;
        --img)
            desktop=false
            isimage=true
            shift
            ;;
        --no-img)
            desktop=true
            isimage=false
            shift
            ;;
        --branch)
            SIGNBRANCH=$2
            shift
            shift
            ;;
        *)
            echo "Unknown option $1" >&2
            exit 1
            ;;
    esac
done

#############################################################################
echo "============================================================"
echo "SIGN Image Version: v${SIGNIMAGEVER}"
echo "SIGN Directory    : ${SIGNDIR}"
echo "SIGN Branch       : ${SIGNBRANCH}"
echo "Operating System : ${PRETTY_NAME}"
echo "Platform         : ${SIGNPLATFORM}"
echo "OS Version       : ${OSVER}"
echo "OS ID            : ${OSID}"
echo "Image            : ${isimage}"
echo "============================================================"
#############################################################################

echo ""
echo "Notes:"
echo "- Does this system have internet access to install packages?"
echo ""
echo "WARNINGS:"
echo "- This install expects to be run on a clean freshly-installed system."
echo "  The script is not currently designed to be re-run multiple times."
if $isimage; then
    echo "- This installer will take over your system." 
#    echo "  It will disable any existing 'pi' or 'debian' user and create a '${FPPUSER}' user.  If the system"
#    echo "  has an empty root password, remote root login will be disabled."
fi
echo ""

echo -n "Do you wish to proceed? [N/y] "
read ANSWER
if [ "x${ANSWER}" != "xY" -a "x${ANSWER}" != "xy" ]
then
	echo
	echo "Install cancelled."
	echo
	exit
fi

STARTTIME=$(date)

#######################################
# Log output and notify user
echo "ALL output will be copied to SIGN_Install.log"
exec > >(tee -a SIGN_Install.log)
exec 2>&1
echo "========================================================================"
echo "SIGN_Install.sh started at ${STARTTIME}"
echo "------------------------------------------------------------------------"
#######################################
# Remove old /etc/sign if it exists
if [ -e "/etc/sign" ]
then
	echo "SIGN - Removing old /etc/sign"
	rm -rf /etc/sign
fi

#######################################
# Create /etc/fpp directory and contents
echo "SIGN - Creating /etc/sign and contents"
mkdir /etc/sign
echo "${SIGNPLATFORM}" > /etc/sign/platform
echo "v${SIGNIMAGEVER}" > /etc/sign/rfs_version
echo "${SIGNCFGVER}" > /etc/sign/config_version
if $desktop; then
    echo "1" > /etc/sign/desktop
else
# Bunch of configuration we wont do if installing onto desktop
# We shouldn't set the hostname or muck with the issue files, keyboard, etc...

#######################################
# Setting hostname
echo "SIGN - Setting hostname"
echo "SIGN" > /etc/hostname
hostname SIGN

#######################################
# Add SIGN hostname entry
echo "SIGN - Adding 'SIGN' hostname entry"
# Remove any existing 127.0.1.1 entry first
sed -i -e "/^127.0.1.1[^0-9]/d" /etc/hosts
echo "127.0.1.1       SIGN" >> /etc/hosts

#######################################
# Update /etc/issue and /etc/issue.net
echo "SIGN - Updating /etc/issue*"
head -1 /etc/issue.net > /etc/issue.new
cat >> /etc/issue.new <<EOF

LED Sign Trailer OS Image v${FPPIMAGEVER}

EOF
cp /etc/issue.new /etc/issue.net
rm /etc/issue.new

head -1 /etc/issue > /etc/issue.new
cat >> /etc/issue.new <<EOF

LED Sign Trailer OS Image v${FPPIMAGEVER}
My IP address: \4

SIGN is configured from a web browser. Point your browser at:
http://\4 , http://\n.local , or http://\n 

EOF
cp /etc/issue.new /etc/issue
rm /etc/issue.new

#######################################
# Make sure /opt exists
echo "SIGN - Checking for existence of /opt"
cd /opt 2> /dev/null || mkdir /opt


#######################################

echo "SIGN - Updating package list"
apt-get update
echo "SIGN - Upgrading apt if necessary"
apt-get install --only-upgrade apt
echo "SIGN - Sleeping 5 seconds to make sure any apt upgrade is quiesced"
sleep 5
echo "SIGN - Upgrading other installed packages"
apt-get -y upgrade
echo "SIGN - Cleanup caches"
apt-get -y clean
apt-get -y --purge autoremove
apt-get -y clean

# remove gnome keyring module config which causes pkcs11 warnings
# when trying to do a git pull
rm -f /etc/pkcs11/modules/gnome-keyring-module

echo "SIGN - Installing required packages"
# Install 10 packages, then clean to lower total disk space required
  
PHPVER=""
ACTUAL_PHPVER="7.4"
if [ "${OSVER}" == "ubuntu_22.04" -o "${OSVER}" == "linuxmint_21" ]; then
    PHPVER="7.4"
    echo "FPP - Forceing PHP 7.4"
    apt install software-properties-common apt-transport-https -y
    add-apt-repository ppa:ondrej/php -y
    apt-get -y update
    apt-get -y upgrade
fi
if [ "${OSVER}" == "ubuntu_22.10" ]; then
    ACTUAL_PHPVER="8.1"
fi

$PACKAGES="mc python3-dev python3-pip python3-mysql.connector python3-flask python3-sqlalchemy shellinabox sudo"

apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install ${PACKAGE_LIST}
#apt-get install $PACKAGES -y
echo "SIGN - Cleaning up after installing packages"
apt-get -y clean

echo "SIGN - Installing PIP Modules"
sudo pip install Flask python-gsmmodem pyftpdlib

echo "SIGN - Configuring shellinabox to use /var/tmp"
echo "SHELLINABOX_DATADIR=/var/tmp/" >> /etc/default/shellinabox
sed -i -e "s/SHELLINABOX_ARGS.*/SHELLINABOX_ARGS=\"--no-beep -t\"/" /etc/default/shellinabox

echo "SIGN - Disabling the VC4 OpenGL driver"
sed -i -e "s/dtoverlay=vc4-fkms-v3d/#dtoverlay=vc4-fkms-v3d/" /boot/config.txt
sed -i -e "s/dtoverlay=vc4-kms-v3d/#dtoverlay=vc4-kms-v3d/" /boot/config.txt
            
echo "SIGN - Disabling Camera AutoDetect"
sed -i -e "s/camera_auto_detect/#camera_auto_detect/" /boot/config.txt

echo "SIGN - Disabling fancy network interface names"
sed -e 's/rootwait/rootwait net.ifnames=0 biosdevname=0/' /boot/cmdline.txt

echo "SIGN - Disabling Swap to save SD card"
systemctl disable dphys-swapfile          

echo "SIGN - Setting locale"
sed -i 's/^\(en_GB.UTF-8\)/# \1/;s/..\(en_AU.UTF-8\)/\1/' /etc/locale.gen
locale-gen en_AU.UTF-8
dpkg-reconfigure --frontend=noninteractive locales
export LANG=en_AU.UTF-8
            
#######################################
# Clone git repository
cd /opt
if $clone_sign; then

    #######################################
    # Remove old /opt/fpp if it exists
    if [ -e "/opt/sign" ]
    then
        echo "SIGN - Removing old /opt/sign"
        rm -rf /opt/sign
    fi

    echo "SIGN - Cloning git repository into /opt/sign"
    git clone https://github.com/smartalecim/Led_Sign sign
    cd sign
    git config pull.rebase true
fi
git config --global pull.rebase true
git config --global --add safe.directory /opt/fpp

#######################################
#######################################
echo "SIGN - Populating ${SIGNHOME}"
mkdir ${SIGNHOME}/.ssh
chown ${SIGNUSER}.${SIGNUSER} ${SIGNHOME}/.ssh
chmod 700 ${SIGNHOME}/.ssh

mkdir ${SIGNHOME}/logs
chown 755 ${SIGNHOME}/logs
#######################################
echo "SIGN - Creating System Service"

cat <<-EOF >> /etc/systemd/system/sign.service 

[Unit]
Description=Sign Control System
After=network.target

[Service]
Type=simple
Restart=always
WorkingDirectory=/home/smartalec/sign/
User=smartalec
ExecStart=/usr/bin/python3 /home/smartalec/sign/app.py

[Install]
WantedBy=multi-user.target
  
EOF
    
systemctl enable sign.service
systemctl start sign.service
#######################################
#echo "SIGN - Giving ${SIGNUSER} user sudo"
#echo "${SIGNUSER} ALL=(ALL:ALL) NOPASSWD: ALL" >> /etc/sudoers

#######################################
# Print notice during login regarding console access

cat <<-EOF >> /etc/motd
[0;31m
                  [0mLED Sign Controller[0;31m
[1m
This SIGN console is for advanced users, debugging, and developers.  If
you aren't one of those, you're probably looking for the web-based GUI.

You can access the UI by typing "http://sign.local/" into a web browser.[0m
EOF

#######################################
ENDTIME=$(date)

echo "========================================================="
echo "SIGN Install Complete."
echo "Started : ${STARTTIME}"
echo "Finished: ${ENDTIME}"
echo "========================================================="
echo "You can reboot the system by changing to the '${SIGNUSER} user"
echo "and running the shutdown command."
echo ""
echo "su - ${SIGNUSER}"
echo "sudo shutdown -r now"
echo ""
echo "NOTE: If you are prepping this as an image for release,"
echo "remove the SSH keys before shutting down so they will be"
echo "rebuilt during the next boot."
echo ""
echo "su - ${SIGNUSER}"
echo "sudo rm -rf /etc/ssh/ssh_host*key*"
echo "sudo shutdown -r now"
echo "========================================================="
echo ""

cp /root/SIGN_Install.* ${SIGNHOME}/
chown sign.sign ${SIGNHOME}/SIGN_Install.*

#######################################
cat <<-EOF >> /etc/ppp/peers/gprs/ppp.txt
/dev/ttyUSB2
115200
connect "/usr/sbin/chat -v -f /etc/chatscripts/gprs"
noipdefault
usepeerdns
defaultroute
replacedefaultroute
hide-password
EOF
#######################################
cat <<-EOF >> /etc/chatscripts/gprs.txt
 
ABORT "BUSY"
ABORT "NO CARRIER"
ABORT "VOICE"
ABORT "NO DIALTONE"
ABORT "NO DIAL TONE"
ABORT "NO ANSWER"
ABORT "DELAYED"
TIMEOUT 30
"" "AT"
OK "ATE0"
OK "AT+CGDCONT=1,\"IP\",\"your_apn_here\""
OK "ATD*99#"
CONNECT ""
EOF
#######################################

#sudo apt install ufw
