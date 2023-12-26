import argparse
import simpy
import random
import sys
import numpy as np
import os
import pandas as pd

total = 0
max_users = 0
cur_users = 0

def user(env, event_rate, mean_service_time, tracker):
    # Leave the system after a random service time
    service_time = random.expovariate(1 / mean_service_time)
    leave_time = env.now + service_time

    global cur_users
    global max_users
    cur_users += 1
    max_users = max(max_users, cur_users)

    while env.now <= leave_time:
        yield env.timeout(1/event_rate)
        tracker.append(env.now)
    cur_users -= 1


def system(env, start,duration, num_users, arrival_rate, event_rate, mean_service_time, tracker):
    #for i in range(num_users):
    while env.now < start:
        yield env.timeout(start-env.now)

    start=env.now
    print("start,end, arrival:", start,start+duration,arrival_rate)

    while env.now < start+duration:
        arrival_time = random.expovariate(arrival_rate)
        yield env.timeout(arrival_time)
        tracker.append(env.now)
        env.process(user(env, event_rate, mean_service_time, tracker))

def oneedge_sim_arrivals(duration, arrival_rate, event_rate, mean_service_time, inc=None):
    tracker = []
    env = simpy.Environment()
    num_users = int(duration*arrival_rate)
    
    env.process(system(env, 0, duration/2, num_users, arrival_rate, event_rate, mean_service_time, tracker))

    env.process(system(env, duration/2, duration/2, num_users, arrival_rate/2, event_rate, mean_service_time, tracker))

    env.run(until=duration)

    start = tracker[0]
    ia_arr = np.ediff1d(tracker)
    ia_arr = np.insert(ia_arr, 0, start)
    if inc:
        np.save(f'./traffic_dur{duration}_lam{arrival_rate}_stime{mean_service_time}_rate{event_rate}_site{inc}.npy', ia_arr)
    return iter(ia_arr)

def cab(env, route , node_array, rps):
    idx = int(route['node'].at[0])
    node = node_array[idx]

    for index, row in route[1:].iterrows():
            while True:

                node.append(env.now)

                yield env.timeout(1/rps)

                if env.now > row['ts']:
                    idx = int(row['node'])
                    node = node_array[idx]
                    break
            
        
def sfcabs_arrivals(routes, num_centroids, rps) :
    node_arr = []
    for i in range(num_centroids):
        node_arr.append([])
    
    env = simpy.Environment()
    for route in routes:
        env.process(cab(env, route, node_arr, rps))

    env.run()

    for i,node in enumerate(node_arr):
        start = node[0]
        ia_arr = np.ediff1d(node)
        ia_arr = np.insert(ia_arr, 0, start)
        np.save(f'sfcabs-load-site{i}.npy', ia_arr)


parser = argparse.ArgumentParser(description="Federared Orchestration Simulation")
parser.add_argument("--duration", type=int, nargs="?", default=200)
parser.add_argument("--lam", type=float, nargs="?", default=0.1, help="default=0.1")
parser.add_argument("--stime", type=float, nargs="?", default=10, help="default=10")
parser.add_argument("--rate", type=float, nargs="?", default=1, help="default=1")
parser.add_argument("--inc", type=int, nargs="?", default=0)
parser.add_argument("--sfcabs", type=bool, const='False', nargs="?")
args = parser.parse_args()

if args.sfcabs:
    print("generating from sfcabs dataset!")
    base = '../datasets/routes'
    files = [f'{base}/{file}' for file in os.listdir(base)]
    routes = []
    
    for file in files:
        df = pd.read_csv(file)
        routes.append(df)
    
    num_centroids = 12
    rps=10
    sfcabs_arrivals(routes, num_centroids, rps)
    exit()

if args.inc != 0:
    for i in range(1,args.inc+1):
        it = oneedge_sim_arrivals(args.duration, args.lam, args.rate, args.stime, i)
else:
    it = oneedge_sim_arrivals(args.duration, args.lam, args.rate, args.stime)

print("max users", max_users)

