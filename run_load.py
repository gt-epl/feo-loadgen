from fabric import Connection,Config
import threading
import pandas as pd
import sys
import os

policy="roundrobin"
RESDIR=f'../feodata/clab-178922/run_load/{policy}'

UID             ='5.out'
COPY_BINS       =False
KILL_LOAD       =False
LOAD_PROFILE    =False
WARMUP          =False
ACTUAL          =False
FETCH_RESULTS   =False

cfg = Config()
cfg.ssh_config_path = "/Users/anirudh/.ssh/config.d/clab.sshconfig"
cfg.load_ssh_config()

hosts = ['clabsvr','clabcl0','clabcl1','clabcl2']
ips = [f'192.168.10.{last_octet}:9696' for last_octet in range(10,14)]
profiles = pd.read_csv(sys.argv[1])
profiles = profiles.set_index('host')
conns = [Connection(host, config=cfg) for host in hosts]

if COPY_BINS:
    print('[+] Copy loadgen binary')
    for c in conns:
        try:
            c.put('loadgen','/tmp/')
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
