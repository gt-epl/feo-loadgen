from fabric import Connection,Config
import threading
import pandas as pd
import sys
import os
import time

policy="central"
profile_filename=sys.argv[1]
PROFILE_PATH=f'./profiles/{profile_filename}'
RESDIR=f'../feodata/clab-181357/run_load/{policy}'

UID           = f'{profile_filename[:-4]}-p2p20ms.out' # loadgen e2e latency is captured in this file
COPY_BINS     = False # copies the loadgen binary along with any function input if you want to
KILL_LOAD     = True  
KILL_FEO      = True
LOAD_PROFILE  = False
CONFIG        = False # run sync.sh. syncs feo and central_server binary along with the appropriate policy config
RUN_FEO       = True
WARMUP        = True
ACTUAL        = False
FETCH_RESULTS = False

cfg = Config()
cfg.ssh_config_path = "/Users/anirudh/.ssh/config.d/clab.sshconfig"
cfg.load_ssh_config()

hosts = ['clabsvr','clabcl0','clabcl1','clabcl2']
controller = 'clabcl3'

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
        conns[0].run(f'bash ~/feo/utils/sync.sh {policy}')
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
        
