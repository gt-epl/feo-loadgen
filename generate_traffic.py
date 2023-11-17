import argparse
import simpy
import random
import sys
import numpy as np

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


def system(env, num_users, arrival_rate, event_rate, mean_service_time, tracker):
    for i in range(num_users):
        arrival_time = random.expovariate(arrival_rate)
        yield env.timeout(arrival_time)
        tracker.append(env.now)
        env.process(user(env, event_rate, mean_service_time, tracker))

def oneedge_sim_arrivals(duration, arrival_rate, event_rate, mean_service_time, inc=None):
    tracker = []
    env = simpy.Environment()
    num_users = int(duration*arrival_rate)
    env.process(system(env, num_users, arrival_rate, event_rate, mean_service_time, tracker))
    env.run(until=duration)

    start = tracker[0]
    ia_arr = np.ediff1d(tracker)
    ia_arr = np.insert(ia_arr, 0, start)
    if inc:
        np.save(f'./traffic_dur{duration}_lam{arrival_rate}_stime{mean_service_time}_rate{event_rate}_site{inc}.npy', ia_arr)
    return iter(ia_arr)



parser = argparse.ArgumentParser(description="Federared Orchestration Simulation")
parser.add_argument("--duration", type=int, nargs="?", default=200)
parser.add_argument("--lam", type=float, nargs="?", default=0.1, help="default=0.1")
parser.add_argument("--stime", type=float, nargs="?", default=10, help="default=10")
parser.add_argument("--rate", type=float, nargs="?", default=1, help="default=1")
parser.add_argument("--inc", type=int, nargs="?", default=0)
args = parser.parse_args()

if args.inc != 0:
    for i in range(1,args.inc+1):
        it = oneedge_sim_arrivals(args.duration, args.lam, args.rate, args.stime, i)
else:
    it = oneedge_sim_arrivals(args.duration, args.lam, args.rate, args.stime)

print("max users", max_users)

