from fabric import Connection,Config
import threading
import pandas as pd
import sys
import os
import time


### START CONFIGURATION AREA ###
# On each run, adjust the configurations below:

policy="central" # Available candidates are in 'feo/offload.go'
RESDIR=f'../feodata/clab-181357/run_load/{policy}'
SSH_CONFIG_PATH = "/Users/anirudh/.ssh/config.d/clab.sshconfig"
OPENWHISK_IP = "http://localhost:3233" # Ip of the openwhisk server running in each node
app_name = 'copy' # The directory name of the application under 'feo/apps'
SETUP_OPENWHISK_SUDO = True # Run the RUN_OPENWHISK command in sudoer 
CONFIG_EXEC_LOCAL = True # Set to True if executing 'feo/utils/sync.ch' locally. Set to False if executing from the host defined in 'controller'.

# The names below should match the following: 
#  1) The alias defined in sshconfig (e.g. `ssh clabcl0`)
#  2) The first column in profiles under 'loadgen/profile'
hosts = ['clabsvr','clabcl0','clabcl1','clabcl2']
controller = 'clabcl3' # The server which will run the controller for 'central' policy.

COPY_LOAD_BIN   = False # Builds and copies the Loadgen binary.
KILL_LOAD       = True  
KILL_FEO        = True
LOAD_PROFILE    = False # Will copy profile, i.e. var_lam_loads
CONFIG          = False # run sync.sh
RUN_OPENWHISK   = False # Runs the standalone openwhisk image on each host in 'hosts'.
CREATE_ACTION   = True  # Runs the `create_action.sh` script for the application defined in `app_name`
SET_LATENCY     = False # Runs the `set_latency.sh` script to set the inter-node latency.
RUN_FEO         = True  # Runs the feo binary on each host in 'hosts'. Also runs central_server in 'central' policy.
WARMUP          = True  # Generates dummy requests to avoid coldstart latency
ACTUAL          = False # Generate load using the loadgen binary
FETCH_RESULTS   = False # Fetch results from 'hosts' into RESDIR


### END CONFIGURATION AREA ###

profile_filename=sys.argv[1] # Filename under 'loadgen/policies' (e.g., 'profile.csv')
PROFILE_PATH=f'./profiles/{profile_filename}'
UID           = f'{profile_filename[:-4]}-p2p20ms.out' # loadgen e2e latency is captured in this file. #:-4 removes the '.csv' extension at end of profile name

cfg = Config()
cfg.ssh_config_path = SSH_CONFIG_PATH
cfg.load_ssh_config()


ips = [f'192.168.10.{last_octet}:9696' for last_octet in range(10,14)]
profiles = pd.read_csv(PROFILE_PATH)
profiles = profiles.set_index('host')
conns = [Connection(host, config=cfg) for host in hosts]
controller_conn =  Connection(controller, config=cfg)


if COPY_BINS:
    print('[+] Copy loadgen binary')
    for c in conns:
        try:
            c.put('loadgen','/tmp/')
            c.put('coldstart.jpeg', '/tmp/')
        except Exception as e:
            print(e)
            pass

if KILL_LOAD:
    print('[+] killall loadgen')
    for c in conns:
        try:
            c.run('killall loadgen')
        except Exception as e:
            print(e)
            pass

if KILL_FEO:
    print('[+] killall feo')
    for c in conns:
        try:
            c.run('killall feo')
        except Exception as e:
            print(e)
            pass

    if policy in ["central"]:
        try:
            controller_conn.run('killall central_server')
        except Exception as e:
            print(e)

if CONFIG:
    print(f'[+] Sync Config: {policy}')
    try:
        if CONFIG_EXEC_LOCAL:
            os.system(f'bash ../feo/utils/sync.sh {policy}')
        else:
            controller_conn.run(f'bash ~/feo/utils/sync.sh {policy}')
    except Exception as e:
        print(e)
        pass

if RUN_OPENWHISK: 
    print('[+] Run standalone openwhisk server')
    for c in conns:
        try:
            sudo_str = ''
            if SETUP_OPENWHISK_SUDO:
                sudo_str = 'sudo'
            c.run(f'{sudo_str} bash ~/utils/openwhisk_server.sh {OPENWHISK_IP}')
        except Exception as e:
            print(e)
            pass

if CREATE_ACTION:
    print(f'[+] Create the action for the app {app_name}')
    for c in conns:
        try:
            c.run(f'bash ~/apps/{app_name}/create_action.sh {OPENWHISK_IP}')
        except Exception as e:
            print(e)
            pass

if SET_LATENCY:
    print(f'[+] Set the inter-node latency')
    for c in conns:
        try:
            c.run(f'bash ~/utils/set_latency.sh')
        except Exception as e:
            print(e)
            pass


if RUN_FEO:
    if policy == "central":
        print(f'[+] run controller on {controller}')
        controller_conn.run("bash -c 'nohup ./central_server > central_server.log 2>&1 &'")

    time.sleep(1)

        
    print(f'[+] Run FEO: {policy}') 
    for i,c in enumerate(conns):
        print(f'Running feo @ {hosts[i]}')
        with c.cd('/tmp/'):
            try:
                c.run("bash -c 'nohup ./feo > feo.log 2>&1 &'", pty=False)
            except Exception as e:
                print(e)
                exit()

if LOAD_PROFILE:
    print("[+] Transfer load files")
    for i,c in enumerate(conns):
        host = hosts[i]
        profile = profiles.loc[host].iloc[0]


        print(f"[+] {host}: Transfering load file: {profile}")
        c.put(profile, f"/tmp")


def run_load(host :str, ip :str, conn : Connection, profile_fp :str, uid : str):
    duration = 60

    profile = profile_fp.split('/')[-1]
    uidstr = uid
    if not uidstr:
        uidstr="warmup"
    print(f"Running {profile} for {host}: {uidstr}")
    with conn.cd('/tmp/'):
        if not uid:
            conn.run(f"./loadgen -duration {duration} -trace {profile} -host {ip}> /dev/null")
        else:
            conn.run(f"./loadgen -duration {duration} -trace {profile} -host {ip} > {uid}")

def run_tasks(uid=None):
    tasks = [ 
            threading.Thread( target=run_load,
                            args=(host, 
                                  ips[i],
                                  conns[i],
                                  profiles.loc[host].iloc[0],
                                  uid))
            for i,host in enumerate(hosts)]

    for t in tasks:
        t.start()

    for t in tasks:
        t.join()

if WARMUP: 
    print("[+] Run warmup tasks")
    run_tasks()

if ACTUAL:
    run_tasks(UID)

if FETCH_RESULTS:
    print('[+] Fetch results')
    for host in hosts:
        print(f"[+] {host}: Transfering result file:")
        dst = f'{RESDIR}/{host}'
        os.system(f'mkdir -p {dst}')
        os.system(f'rsync -avz {host}:/tmp/{UID} {dst}/')
        
