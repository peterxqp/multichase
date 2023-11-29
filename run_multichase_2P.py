#!/usr/bin/python3
#
#Please make sure python3,pip,gcc,make are installed 
########################################################################
#                                                                      #
#                                                                      #
# PURPOSE: A script for 2 Sockets 8 NUMA nodes Multichase test         #
#                                                                      #
# VERSION: 1.0.0                                                       #
#                                                                      #
# Author: Peter Xu  Lenovo SPV team                                    #
#                                                                      #
########################################################################

import subprocess
import sys
import importlib

# Check and install required module
def install(package):
    #subprocess.check_call([sys.executable, "-m", "ensurepip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade","pip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_python_module():
    packages = ['numpy','matplotlib','urllib','shutil','os','datetime']
    for package in packages:
        try:
            package = importlib.import_module(package)
        except ModuleNotFoundError as e:
            install(package)

check_python_module()

#refresh sys.path
import site
from importlib import reload
reload(site)


import shutil
import os
from urllib import request
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm


def is_numactl_installed(a_print_result=True):
    try:
        numa_node_count = int(subprocess.check_output("numactl --hardware | grep 'available:' | awk '{print $2}'", shell=True))
        if a_print_result:
            print('numactl is installed.')
        return True
    except:
        if a_print_result:
            print('numactl is NOT installed.')
        return False

def get_numa_node_count():
    if is_numactl_installed(False):
        return int(subprocess.check_output("numactl --hardware | grep 'available:' | awk '{print $2}'", shell=True))
    else:
        print('numactl must be installed for get_numa_node_count.')
        sys.exit(1)

def get_socket_count():
    return int(subprocess.check_output("lscpu | grep 'Socket(s):' | awk '{print $2}'", shell=True))

def check_nps():
    if int(get_numa_node_count()/get_socket_count())!= 4:
        print("Please set NPS=4 in the UEFI")
        return False
    else:
        return True


def check_multichase_file():
     if not os.path.isfile('multichase'):
        print("Can't find multichase in the current direcotry")
        return False
     else:
        return True 

def check_root_privileges():
    if os.geteuid()!=0:
        return False
    else:
        return True

def install_multichase():
    print("Downloading multichase from github")
    Current_Time=datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
    if os.path.isdir("multichase"):
        target = str(os.getcwd()) + '/' + 'multichase' + '_' + str(Current_Time)
        os.rename("multichase",target)
    try:
        response = subprocess.check_output("git clone https://github.com/google/multichase.git", shell=True)
        print(response)
        print("File download")
        if os.path.isdir("multichase"):
               os.chdir("multichase")
               subprocess.check_output("make", shell=True)
               print("multichase installation is done") 
               return True
    except:
        print("Something wrong, please check network and install multichase manually")
        return False

def check_for_requirements():
    if not is_numactl_installed():
        sys.exit("numactl is required but not found! Exiting.\n")
    if not check_nps():
       sys.exit("NPS=4 is required, please change the setting in the UEFI")
    if not check_root_privileges():
        sys.exit("Root privileages is required, please switch to root user")
    if not check_multichase_file():
        print("Try to install multichase")
        install_multichase()   

#check_for_requirements()

#print out the output immediately 
def run_shell(shell):
    cmd = subprocess.Popen(shell, stdin=subprocess.PIPE, stderr=sys.stderr, close_fds=True,
                           stdout=sys.stdout, universal_newlines=True, shell=True, bufsize=1)

    cmd.communicate()
    return cmd.returncode

def generate_run_multichase_sh():
    result = '''#!/bin/bash

LOGFILE=multichase_test.log


echo 16384 > /proc/sys/vm/nr_hugepages

echo never > /sys/kernel/mm/transparent_hugepage/enabled
cat /sys/kernel/mm/transparent_hugepage/enabled




printf "%4s %7s %7s %7s %7s %7s %7s %7s %7s\n" \
"CPU" "NODE0" "NODE1" "NODE2" "NODE3" "NODE4" "NODE5" "NODE6" "NODE7" >> $LOGFILE

printf "%4s %7s %7s %7s %7s %7s %7s %7s %7s\n" \
"CPU" "NODE0" "NODE1" "NODE2" "NODE3" "NODE4" "NODE5" "NODE6" "NODE7" 

for cpu in $(seq 0 24 168)
do 
   printf "%4s " ${cpu} 
   printf "%4s " ${cpu} 2>&1 >> $LOGFILE
   for numa in $(seq 0 7) 
   do
	result=$(numactl -C ${cpu} -m ${numa} ./multichase -s 512 -H -m 1g -n 60)
	printf "%7.1f " ${result} 
	printf "%7.1f " ${result} 2>&1 >> $LOGFILE
   done
   printf "\n" 
   printf "\n" 2>&1 >> $LOGFILE
done

#printf "Re-enabling Transparent Hugepages" 2>&1 $LOGFILE
echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
    '''
    return result

def run_multichase():
    Current_Time=datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
    if check_multichase_file():
        if not os.path.exists('run_multichase.sh'):
            #subprocess.check_output("wget http://10.240.52.11/pub/test_scripts/multichase/run_multichase.sh", shell=True)
            file = open('run_multichase.sh','w')
            run_multichase_txt = generate_run_multichase_sh()
            file.write( run_multichase_txt )
            file.close()
        if os.path.exists("multichase_test.log"):
            target = str(os.getcwd()) + '/' + 'multichase_test' + '_' + str(Current_Time) + '.log'
            os.rename("multichase_test.log",target)
        subprocess.check_output("chmod u+x run_multichase.sh", shell=True)
        print(run_shell("./run_multichase.sh"))
        print("multichase test is done, checking the result now")


#data treatment
def data_treatment():
    lat = []
    count = 0
    with open("multichase_test.log","r") as f:
        for line in f.readlines():
            #locate latency data
            if line.strip().startswith("0"):
                break
            count +=1


    with open("multichase_test.log","r") as x:
        lines = x.readlines()
        for i in range(count,count+8):
            lat_line=lines[i].strip().split()[1:]
            lat_line=list(map(float,lat_line))
            lat.append(lat_line)
        #print(lat)
    
    #calculate local node
    local_node = np.diagonal(lat)
    #print(local_node)
    local_high =  max(local_node)
    local_low = min(local_node)
    local_mean = round(sum(local_node)/len(local_node),1)
    local_node_latency="Local Node Memory Latency (Low-Avg-High) is " + str(local_low) + "-" + str(local_mean) + "-" + str(local_high)+" ns"
    print(local_node_latency)

    #calculate near local node
    matrix = np.array(lat)

    near_local_node_1 = matrix[0:4,0:4]
    #print(near_local_node_1)
    near_local_node_2 = matrix[4:8,4:8]
    #print(near_local_node_2)

    #remove local node from list
    m = near_local_node_1.shape[0]
    idx = (np.arange(1,m+1) + (m+1)*np.arange(m-1)[:,None]).reshape(m,-1)
    out1 = near_local_node_1.ravel()[idx]
    #print(out1)

    m = near_local_node_2.shape[0]
    idx = (np.arange(1,m+1) + (m+1)*np.arange(m-1)[:,None]).reshape(m,-1)
    out2 = near_local_node_2.ravel()[idx]
    #print(out2)

    near_local_node = np.vstack((out1,out2))
    #print(near_local_node)
    near_local_high = np.max(near_local_node)
    near_local_low = np.min(near_local_node)
    near_local_mean = round(np.mean(near_local_node),1)
    near_local_node_latency="Near Local Node Memory Latency (Low-Avg-High) is " + str(near_local_low) + "-" + str(near_local_mean) + "-" + str(near_local_high)+" ns"
    print(near_local_node_latency)


    #calculate remote node
    remote_node_1 = matrix[4:8,0:4]
    #print(remote_node_1)
    remote_node_2 = matrix[0:4,4:8]
    #print(remote_node_2)
    remote_node = np.vstack((remote_node_1,remote_node_2))
    #print(remote_node)
    remote_high = np.max(remote_node)
    remote_low = np.min(remote_node)
    remote_mean = round(np.mean(remote_node),1)
    remote_node_latency="Remote Node Memory Latency (Low-Avg-High) is " + str(remote_low) + "-" + str(remote_mean) + "-" + str(remote_high)+" ns"
    print(remote_node_latency)

    if os.path.exists("multichase_spv_data.log"):
        Current_Time=datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
        target = str(os.getcwd()) + '/' + 'multichase_spv_data' + '_' + str(Current_Time) + '.log'
        os.rename("multichase_spv_data.log",target) 
    
    #redirect 'print' output to a file
    sys.stdout=open("multichase_spv_data.log","w")
    print(local_node_latency)
    print(near_local_node_latency)
    print(remote_node_latency)
    sys.stdout.close()

    #print(matrix)
    '''
    #Latency 2d array visualization
    #set up grid
    nx, ny = 8, 8
    x = range(nx)
    y = range(ny)

    hf = plt.figure()
    ha = hf.add_subplot(111, projection='3d')

    X,Y = np.meshgrid(x, y)
    ha.plot_surface(X, Y, matrix)
    ha.set(xlim=[8,0],ylim=[0,8],title='Numa Node Latency(ns)',ylabel='Node',xlabel='Node')
    #hf.suptitle("Numa Node Latency")
    plt.show()
    '''
    #Generate chart 

    x1 = list(range(8))
    x2 = list(range(24))
    x3 = list(range(32))
    y = list(range(0,400,20))
    near_local_node_1 = list(np.array(near_local_node).flatten())
    remote_node_1 = list(np.array(remote_node).flatten())
    plt.plot(x1,local_node,marker='*',color='green',label=u'local node')
    plt.plot(x2,near_local_node_1,marker='o',color='blue',label=u'near local node')
    plt.plot(x3,remote_node_1,marker='s',color='red',label=u'remote node')
    plt.ylabel(u'Latency(ns)')
    plt.xlim(0,32)
    plt.ylim(0,400)
    plt.title('multichase latencies(in ns)')
    plt.legend()
    plt.show(block=False)
    plt.pause(3)
    if os.path.exists("mutichase.jpg"):
        Current_Time=datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
        target = str(os.getcwd()) + '/' + 'mlc' + '_' + str(Current_Time) + '.jpg'
        os.rename("multichase.jpg",target)
    plt.savefig('multichase.jpg')
    plt.close()

# main program ###
def main():
    check_python_module()
    check_for_requirements()
    run_multichase()
    data_treatment()
    

                    
if __name__ == "__main__":
    
    main()    

 
