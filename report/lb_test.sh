#!/bin/bash

url="localhost:5002/heavy"
success_count=0
total_count=0

start_time=$(date +%s)

# Send 10 requests in parallel using xargs
seq 1 100 | xargs -n1 -P100 -I{} sh -c 'curl -s "$0" >/dev/null 2>&1 && echo "success"' $url | wc -l > /dev/null
success_count=$?

end_time=$(date +%s)
duration=$((end_time - start_time))

echo "Sent 10 requests in parallel."
echo "It took $duration seconds to send and complete all requests."
echo "Out of $total_count requests, $success_count were successful."
