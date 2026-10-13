#!/usr/bin/env bash
set -euo pipefail
# Execute on the Docker host, as root. This touches only the named project bridge
# and rules matching its dedicated subnet. Check for conflicts before provisioning.
if ! docker network inspect skg-execution >/dev/null 2>&1; then
  docker network create --internal --subnet 172.30.90.0/24 --gateway 172.30.90.1 \
    --opt com.docker.network.bridge.name=skg-exec --label skg.egress=portal-only skg-execution
fi
test "$(docker network inspect -f '{{.Internal}}' skg-execution)" = true
test "$(docker network inspect -f '{{(index .IPAM.Config 0).Subnet}}' skg-execution)" = 172.30.90.0/24
test "$(docker network inspect -f '{{index .Options "com.docker.network.bridge.name"}}' skg-execution)" = skg-exec
iptables -C INPUT -i skg-exec -j DROP 2>/dev/null || iptables -I INPUT 1 -i skg-exec -j DROP
iptables -N SKG-EGRESS 2>/dev/null || true
iptables -C SKG-EGRESS -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || iptables -A SKG-EGRESS -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -C SKG-EGRESS -s 172.30.90.0/24 -d 172.30.90.2 -p tcp --dport 8090 -j ACCEPT 2>/dev/null || iptables -A SKG-EGRESS -s 172.30.90.0/24 -d 172.30.90.2 -p tcp --dport 8090 -j ACCEPT
iptables -C SKG-EGRESS -s 172.30.90.0/24 -j DROP 2>/dev/null || iptables -A SKG-EGRESS -s 172.30.90.0/24 -j DROP
iptables -C SKG-EGRESS -j RETURN 2>/dev/null || iptables -A SKG-EGRESS -j RETURN
iptables -C DOCKER-USER -i skg-exec -j SKG-EGRESS 2>/dev/null || iptables -I DOCKER-USER 1 -i skg-exec -j SKG-EGRESS
echo 'Installed project-specific portal-only egress and host access block.'
