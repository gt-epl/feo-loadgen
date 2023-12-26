# Simple Go Loadgen for FaaS testing

## how to use

1. `run_load.py` is the main experiment runner script
2. `generate_traffic.py` generates static tracefiles for load at every edge node


### Additional Info

1. `generate_traffic.py` uses to the user arrival model first expressed in OneEdge.
2. The `sfcabs` variant uses the cab routes whose routes are generated in the sfcabs notebook in feo-notebooks to produce aggregate load tracefiles at candidate edge nodes.
