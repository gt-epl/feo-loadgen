# Simple Go Loadgen for FaaS testing

## how to use

### Single Run
- `exp.sh` can be used to run the loadprofile on an edge node. Modify loadgen to change IP
- `./exp.sh <num_requests> <tracefile> <output>`
- e.g., `./exp.sh 100 traffic_dur1000_lam1.0_stime10.0_rate4.0_site2.npy tmp`


### Multi Run
- `./run.sh`
- modify `run.sh` as appropriate.

