from fabric import Connection,Config
import threading
import pandas as pd
import sys
import os
import time


### START CONFIGURATION AREA ###
# On each run, adjust the configurations below:

policy=sys.argv[3] # Available candidates are in 'feo/offload.go'
# RESDIR=f'../feodata/' + sys.argv[2] +'/run_load/{policy}'
RESDIR=f'../feodata/' + sys.argv[2] +'/run_load/' + policy

# TODO: hosts configuration could be automatically generated. 
SSH_CONFIG_PATH = "/home/jithin/.ssh/config"
OPENWHISK_IP = "http://localhost:3233" # Ip of the openwhisk server running in each node

# TODO: since we have many apps, app configuration could be separate file. Loadgen could read the configs from the said files
app_name = 'fibtest' # The directory name of the application under 'feo/apps'

app_name_2 = 'fibtest2' # Only used if RUN_MULTI_LOADGEN is True.

# TODO: force experiment trigger from local w/e that may be i.e., do away with this op.
CONFIG_EXEC_LOCAL = True # Refer to 'feo/README.md' for more detail. Set to True if executing 'feo/utils/sync.ch' from the same node as run_load.py. Set to False if executing from the host defined in 'controller'.

# The names below should match the following: 
#  1) The alias defined in sshconfig (e.g. `ssh clabcl0`)
#  2) The first column in profiles under 'loadgen/profile'
#  3) The order of peer addresses under 'feo/config.yml' 
# TODO: need a cleaner way to specify ssh aliases, public ips, private ips once in for all. 
# i.e., this script should work off a hosts.csv file
# it should possibly create the ssh config file.

# hosts = ['clabcl0','clabcl1','clabcl2', 'clabcl3', 'clabcl4', 'clabcl5', 'clabcl6', 'clabcl7', 'clabcl8', 'clabcl9']
hosts = ['clabcl0','clabcl1','clabcl2', 'clabcl3', 'clabcl4', 'clabcl5', 'clabcl6', 'clabcl7', 'clabcl8', 'clabcl9']
controller = 'clabsvr' # The server which will run the controller for 'central' policy.
ips = [f'192.168.10.{last_octet}:9696' for last_octet in range(10,20)]

# hosts = [f'az{i}' for i in range(4)]
# controller = 'az4'
# # ip input for loadgen. 
# ips = [f'192.168.10.{last_octet}:9696' for last_octet in [7,8,4,5]]

COPY_LOAD_BIN   = True # Builds and copies the Loadgen binary.
KILL_LOAD       = True  
KILL_FEO        = True
LOAD_PROFILE    = True # Will copy profile, i.e. var_lam_loads
CONFIG          = True # run sync.sh
RUN_OPENWHISK   = False # Runs the standalone openwhisk image on each host in 'hosts'.
DEPLOY_FIBTEST  = False
CREATE_ACTION   = False  # Runs the `create_action.sh` script for the application defined in `app_name`
SET_LATENCY     = False # Runs the `set_latency.sh` script to set the inter-node latency.
RUN_FEO         = True  # Runs the feo binary on each host in 'hosts'. Also runs central_server in 'central' policy.
WARMUP          = False  # Generates dummy requests to avoid coldstart latency
ACTUAL          = True # Generate load using the loadgen binary
FETCH_RESULTS   = True # Fetch results from 'hosts' into RESDIR

RUN_MULTI_LOADGEN = True # Currently runs each loadgen instance twice simultaneously on each node.

### END CONFIGURATION AREA ###

profile_filename=sys.argv[1] # Filename under 'loadgen/profiles' (e.g., 'profile.csv')
PROFILE_PATH=f'./profiles/{profile_filename}'
UID           = f'{profile_filename[:-4]}-p2p20ms.out' # loadgen e2e latency is captured in this file. #:-4 removes the '.csv' extension at end of profile name

cfg = Config()
cfg.ssh_config_path = SSH_CONFIG_PATH
cfg.load_ssh_config()


profiles = pd.read_csv(PROFILE_PATH)
profiles = profiles.set_index('host')
conns = [Connection(host, config=cfg) for host in hosts]
controller_conn =  Connection(controller, config=cfg)


if COPY_LOAD_BIN:
    print('[+] Build and copy loadgen binary')
    for c in conns:
        try:
            os.system(f'GOOS=linux GOARCH=amd64 go build')
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

    if policy in ["central", "epoch", "hybrid"]:
        try:
            controller_conn.run('killall central_server')
        except Exception as e:
            print(e)

if CONFIG:
    print(f'[+] Sync Config: {policy}')
    try:
        # Refer to 'feo/README.md' for more details.
        if CONFIG_EXEC_LOCAL:
            os.system(f'bash ../feo/utils/sync.sh {policy} True True')
        else:
            controller_conn.run(f'bash ~/feo/utils/sync.sh {policy} True False')
    except Exception as e:
        print(e)
        pass

if RUN_OPENWHISK: 
    print('[+] Run standalone openwhisk server')
    for c in conns:
        try:
            c.run(f'bash ~/utils/openwhisk_server.sh {OPENWHISK_IP}')
        except Exception as e:
            print(e)
            pass

if DEPLOY_FIBTEST: 
    print('[+] Run standalone fibtest containers')
    for c in conns:
        try:
            c.run(f'docker kill $(docker ps -q)')
        except Exception as e:
            print(e)
            pass
    
    for c in conns:
        try:
            c.run(f'docker pull jithinsojan/fibtest-local')
        except Exception as e:
            print(e)
            pass

    for c in conns:
        try:
            for i in range(9000,9020):
                c.run(f'docker run -p {i}:9000 -d jithinsojan/fibtest-local')
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
    
    if RUN_MULTI_LOADGEN:
        for c in conns:
            try:
                c.run(f'bash ~/apps/{app_name_2}/create_action.sh {OPENWHISK_IP}')
            except Exception as e:
                print(e)
                pass

if SET_LATENCY:
    print(f'[+] Set the inter-node latency')
    intf="enp6s0f1" #for azure, eth1 for clab
    for c in conns:
        try:
            c.run(f'bash ~/utils/unset_latency.sh {intf} > /dev/null')
        except Exception as e:
            print(e)

        try:
            c.run(f'bash ~/utils/set_latency.sh {intf} 5 > /dev/null')
        except Exception as e:
            print(e)
            pass


if RUN_FEO:
    if policy in ["central", "epoch", "hybrid"]:
        print(f'[+] run controller on {controller}')
        controller_conn.run("bash -c 'nohup ./central_server > central_server.log 2>&1 &'")

    time.sleep(1)

        
    print(f'[+] Run FEO: {policy}') 
    for i,c in enumerate(conns):
        print(f'Running feo @ {hosts[i]}')
        with c.cd('/tmp/'):
            try:
                c.run("bash -c 'nohup ./feo -port1 9000 -count1 10 -port2 9010 -count2 10 > feo.log 2>&1 &'", pty=False)
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


def run_load(host :str, ip :str, conn : Connection, profile_fp :str, uid : str, app :str):
    duration = 60

    profile = profile_fp.split('/')[-1]
    uidstr = uid
    if not uidstr:
        uidstr="warmup"
    print(f"Running {profile} for {host}: {uidstr}")
    with conn.cd('/tmp/'):
        if not uid:
            conn.run(f"./loadgen -duration {duration} -trace {profile} -host {ip} -app {app} > /dev/null")
        else:
            outstr = app + "-" + uid
            conn.run(f"./loadgen -duration {duration} -trace {profile} -host {ip} -app {app} > {outstr}")

def run_tasks(uid=None):
    tasks = [ 
            threading.Thread( target=run_load,
                            args=(host, 
                                  ips[i],
                                  conns[i],
                                  profiles.loc[host].iloc[0],
                                  uid,
                                  app_name))
            for i,host in enumerate(hosts)]
    
    if RUN_MULTI_LOADGEN:
        tasks2 = [ 
                threading.Thread( target=run_load,
                                args=(host, 
                                    ips[i],
                                    conns[i],
                                    profiles.loc[host].iloc[0],
                                    uid,
                                    app_name_2))
                for i,host in enumerate(hosts)]
        tasks = tasks + tasks2

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
        outstr = app_name + "-" + UID
        os.system(f'rsync -avz {host}:/tmp/{outstr} {dst}/')
        if RUN_MULTI_LOADGEN:
            outstr2 = app_name_2 + "-" + UID
            os.system(f'rsync -avz {host}:/tmp/{outstr2} {dst}/')
        
