start=1
end=10

num_reqs=100
tracefile="loads/traffic_dur1000_lam1.0_stime10.0_rate4.0_site2.npy"
resdir="./results/r13"
policy="roundrobin"
mkdir -p $resdir

#stored info: policy tracefile number_of_requests metainfo
echo $policy $tracefile $num_reqs 20ms-p2p,1024m,roundrobin > $resdir/info

for(( i=start; i<=end; i++ )); do 
  out="$resdir/${policy}$i.out"
  echo "[+] warmup run $i"
  ./exp.sh $num_reqs $tracefile $out
  echo "[+] actual run $i"
  ./exp.sh $num_reqs $tracefile $out
done
