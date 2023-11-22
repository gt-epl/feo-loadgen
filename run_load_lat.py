
import os

start=1
end=6
num_reqs=500
uid=0

rootdir='var_lam_loads_2rps'
files = os.listdir(rootdir)

# test files
files = ['traffic_dur1000_lam0.1_stime10_rate2.0_site1.npy',
         'traffic_dur1000_lam0.2_stime10_rate2.0_site1.npy',
         'traffic_dur1000_lam0.4_stime10_rate2.0_site1.npy']



resdir="./results/var_loads_cs_test"
os.system(f'mkdir -p {resdir}')

info = f'{resdir}/info'
fh = open(info,'w')

for file in files[::-1]:
    tracefile = f'{rootdir}/{file}'
    tokens = file.split('_')
    fh.write(f'{tracefile},{uid}\n')

    print(f'[+] Run {tokens[2]}')
    print('[+] Warmup run')
    print(f'./exp.sh {num_reqs} {tracefile}')
    os.system(f'./exp.sh {num_reqs} {tracefile}')
    for i in range(start,end):

        print(f'[+] Actual run {i}')
        out=f'{resdir}/{uid}-{i}.out'
        os.system(f'./exp.sh {num_reqs} {tracefile} {out}')

    uid += 1

fh.close()
    
