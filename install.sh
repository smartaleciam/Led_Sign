#!/bin/bash

# Led Trailer Sign Install Script
SIGNBRANCH=${SIGNBRANCH:-"master"}
SIGNIMAGEVER="2023-12-18"
SIGNCFGVER="1.2"
SIGNPLATFORM="UNKNOWN"
SIGNDIR=/opt/sign
SIGNUSER=smartalec
SIGNHOME=/home/${SIGNUSER}/sign
OSVER="UNKNOWN"
IP4=$(/sbin/ip -o -4 addr list eth0 | awk '{print $4}' | cut -d/ -f1)

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
	echo "SIGN - Removing old ${SIGNHOME}"
	rm -rf ${SIGNHOME}
fi
#######################################
# Create /etc/sign directory and contents
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

# Enable SSH terminal Login
systemctl enable ssh.socket

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
echo "SIGN - Setting US keyboard layout and locale"
sed -i 's/^\(en_GB.UTF-8\)/# \1/;s/..\(en_AU.UTF-8\)/\1/' /etc/locale.gen
sed -i "s/XKBLAYOUT=".*"/XKBLAYOUT="us"/" /etc/default/keyboard
echo "LANG=en_AU.UTF-8" > /etc/default/locale
echo "LC_MESSAGES=en_AU.UTF-8" > /etc/default/locale
export LANG=en_AU.UTF-8
# end of if desktop
fi

echo "SIGN - Updating package list"
apt-get update
apt-get install --only-upgrade apt
apt-get -y upgrade
echo "SIGN - Cleanup caches"
apt-get -y clean

# remove gnome keyring module config which causes pkcs11 warnings
# when trying to do a git pull
rm -f /etc/pkcs11/modules/gnome-keyring-module

echo "SIGN - Installing System packages"
sudo apt-get install mc python3-dev python3-pip python3-flask python3-ftputil python3-gps gpsd-clients vsftpd openssl shellinabox sudo git ppp minicom ufw libopenblas-dev unzip mosquitto mosquitto-clients logrotate -y
#echo "SIGN - Installing Camera Packages"
#sudo apt-get install build-essential cmake pkg-config libjpeg-dev libgl1-mesa-dev libtiff5-dev libjasper-dev libpng-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev libfontconfig1-dev libcairo2-dev libgdk-pixbuf2.0-dev libpango1.0-dev libgtk2.0-dev libgtk-3-dev libatlas-base-dev gfortran libhdf5-dev libhdf5-serial-dev libhdf5-103 python3-pyqt5 python3-dev -y
echo "SIGN - Cleaning up after installing packages"
apt-get -y clean

echo "SIGN - Installing PIP Modules"
pip3 install wheel Flask flask-socketio flask_fontawesome paho-mqtt python-gsmmodem mysql-connector pyserial psutil matplotlib gevent-websocket numpy ftputil eventlet pyftpdlib pyudev opencv-python-headless

#######################################
#clear   # clears the screen
#######################################

# Setting firewall
sudo ufw logging on
echo "SIGN - Setting up firewall"
sudo ufw default deny incoming
sudo ufw default deny outgoing
sudo ufw allow 22/tcp
sudo ufw allow 4200/tcp
sudo ufw allow 8080/tcp
sudo systemctl start ufw
#sudo ufw enable
#clear
sudo ufw status

echo "SIGN - Configuring shellinabox to use /var/tmp"
echo "SHELLINABOX_DATADIR=/var/tmp/" >> /etc/default/shellinabox
sed -i -e "s/SHELLINABOX_ARGS.*/SHELLINABOX_ARGS=\"--no-beep -t\"/" /etc/default/shellinabox

#echo "SIGN - Disabling the VC4 OpenGL driver"
#sed -i -e "s/dtoverlay=vc4-fkms-v3d/#dtoverlay=vc4-fkms-v3d/" /boot/config.txt
#sed -i -e "s/dtoverlay=vc4-kms-v3d/#dtoverlay=vc4-kms-v3d/" /boot/config.txt
            
#echo "SIGN - Disabling Camera AutoDetect"
#sed -i -e "s/camera_auto_detect/#camera_auto_detect/" /boot/config.txt

#echo "SIGN - Disabling fancy network interface names"
#sed -e 's/rootwait/rootwait net.ifnames=0 biosdevname=0/' /boot/cmdline.txt

echo "SIGN - Disabling Swap to save SD card"
systemctl disable dphys-swapfile          

dpkg-reconfigure --frontend=noninteractive locales

echo "SIGN - Setting up Mosquitto"
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
           
#######################################
# Make sure /opt exists
echo "SIGN - Checking for existence of /opt"
cd /opt 2> /dev/null || mkdir /opt
sudo chmod -R 777 /opt
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
    echo "SIGN - Cloning git repository"
    git clone https://github.com/smartaleciam/Led_Sign.git sign
    cd sign
    git config pull.rebase true
fi
git config --global pull.rebase true
git config --global --add safe.directory /opt/sign

#######################################
echo "SIGN - Populating ${SIGNHOME}"
if [ cd /${SIGNHOME}/.ssh 2> /dev/null]
then
    sudo mkdir ${SIGNHOME}/.ssh
    sudo chown ${SIGNUSER}.${SIGNUSER} ${SIGNHOME}/.ssh
    sudo chmod 700 ${SIGNHOME}/.ssh
fi
if [ cd /${SIGNHOME}/logs 2> /dev/null]
then
    sudo mkdir ${SIGNHOME}/logs
    #chown ${SIGNUSER}.${SIGNUSER} ${SIGNHOME}/logs
    sudo chmod -R 777 ${SIGNHOME}/logs
fi
#if [ cd /${SIGNHOME}/.bashrc 2> /dev/null]
#then
#    echo >> ${SIGNHOME}/.bashrc
#    echo ". /opt/sign/scripts/common" >> ${SIGNHOME}/.bashrc
#fi
#######################################
# Configure log rotation
echo "SIGN - Configuring log rotation"
sudo cp -r /opt/sign/etc/logrotate.d/* /etc/logrotate.d/
sed -i -e "s/#compress/compress/" /etc/logrotate.conf
sed -i -e "s/rotate .*/rotate 2/" /etc/logrotate.conf
#######################################
# Move all files to correct locations
echo "SIGN - Moving Files to Correct locations"
sudo cp -r /opt/sign/etc/systemd/system/* /etc/systemd/system/

cd /etc/ppp/gprs 2> /dev/null || mkdir /etc/ppp/gprs
sudo cp -r /opt/sign/etc/ppp/gprs/* /etc/ppp/gprs/

#cp /opt/sign/etc/chatscripts/* /etc/chatscripts/
sudo cp -r /opt/sign/etc/update-motd.d/* /etc/update-motd.d/
sudo cp -r /opt/sign/etc/* /etc/

cd ${SIGNHOME} 2> /dev/null || mkdir ${SIGNHOME}
sudo cp -r /opt/sign/sign/* ${SIGNHOME}/

cd /${SIGNHOME}/../sim7600g-h 2> /dev/null || sudo mkdir ${SIGNHOME}/../sim7600g-h
sudo cp -r /opt/sign/sim7600g-h/* ${SIGNHOME}/../sim7600g-h/

#######################################
echo "SIGN - Enabling System Services"
sudo systemctl enable sign.service
sudo systemctl enable status_update.service
sudo systemctl start sign.service
sudo systemctl start status_update.service
#######################################
#echo "SIGN - Giving ${SIGNUSER} user sudo"
#echo "${SIGNUSER} ALL=(ALL:ALL) NOPASSWD: ALL" >> /etc/sudoers

#######################################
ENDTIME=$(date)

echo "========================================================="
echo "SIGN Install Complete."
echo "Started : ${STARTTIME}"
echo "Finished: ${ENDTIME}"
echo "========================================================="
echo "Welcome ${SIGNUSER}, Please Reboot"
echo "by running the reboot command."
echo "Ip Address: ${IP4}"
#echo "su - ${SIGNUSER}"
#echo "sudo shutdown -r now"
#echo ""
#echo "NOTE: If you are prepping this as an image for release,"
#echo "remove the SSH keys before shutting down so they will be"
#echo "rebuilt during the next boot."
#echo ""
#echo "su - ${SIGNUSER}"
#echo "sudo rm -rf /etc/ssh/ssh_host*key*"
echo "sudo reboot"
echo "========================================================="
echo ""

#cp /root/SIGN_Install.* ${SIGNHOME}/
#chown sign.sign ${SIGNHOME}/SIGN_Install.*

#sudo apt install ufw
