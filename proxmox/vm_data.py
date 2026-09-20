#!/usr/bin/env python3
"""Script to collect Proxmox VM data and output as JSON."""

import os
import json
import sys
from proxmoxer import ProxmoxAPI
from humanize import naturalsize

def main():
    # Get credentials from environment
    proxmox_user = os.getenv('PROXMOX_USER', 'root@pam')
    proxmox_password = os.getenv('PROXMOX_PASSWORD', '')
    proxmox_host = os.getenv('PROXMOX_HOST', 'nuc-g3p-1.local.symmatree.com')
    
    if not proxmox_password:
        print("Error: PROXMOX_PASSWORD not set", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Connect to Proxmox with increased timeout
        proxmox = ProxmoxAPI(
            proxmox_host,
            user=proxmox_user,
            password=proxmox_password,
            verify_ssl=False,
            port=8006,
            timeout=60
        )
        
        # Get list of nodes
        nodes = proxmox.nodes.get()
        
        # Collect VM data for each node
        vm_data = []
        for node in nodes:
            node_name = node.get('node', '')
            
            # Get VMs for this node with full=1 (boolean parameter)
            try:
                vms = proxmox.nodes(node_name).qemu.get(full=1)
            except Exception as e:
                print(f"Error getting VMs for node {node_name}: {e}", file=sys.stderr)
                continue
            
            for vm in vms:
                vmid = vm.get('vmid', 0)
                name = vm.get('name', '')
                
                # Extract basic fields
                cpu = vm.get('cpu', 0)
                cpus = vm.get('cpus', 0)
                mem = vm.get('mem', 0)
                maxmem = vm.get('maxmem', 0)
                uptime = vm.get('uptime', 0)
                status = vm.get('status', 'unknown')
                
                # Try to get IP address from agent
                ip_address = None
                try:
                    # Try agent/info first
                    agent_info = proxmox.nodes(node_name).qemu(vmid).agent('info').get()
                    # Check if agent is available and has network info
                    if agent_info and 'result' in agent_info:
                        # Try network-get-interfaces
                        try:
                            network_info = proxmox.nodes(node_name).qemu(vmid).agent('network-get-interfaces').get()
                            if network_info and 'result' in network_info:
                                # Parse network interfaces to find IP addresses
                                interfaces = network_info.get('result', [])
                                for interface in interfaces:
                                    if 'ip-addresses' in interface:
                                        for ip_info in interface['ip-addresses']:
                                            if ip_info.get('ip-address-type') == 'ipv4' and not ip_info.get('ip-address', '').startswith('127.'):
                                                ip_address = ip_info.get('ip-address')
                                                break
                                    if ip_address:
                                        break
                        except:
                            pass
                except:
                    # Agent not available or failed
                    pass
                
                # Format values
                mem_used_str = naturalsize(mem, binary=True) if mem else "0 B"
                mem_total_str = naturalsize(maxmem, binary=True) if maxmem else "0 B"
                mem_fraction = (mem / maxmem * 100) if maxmem > 0 else 0
                
                uptime_days = int(uptime / 86400) if uptime else 0
                uptime_hours = int((uptime % 86400) / 3600) if uptime else 0
                uptime_str = f"{uptime_days}d {uptime_hours}h" if uptime else "0d 0h"
                
                vm_info = {
                    'vmid': vmid,
                    'name': name,
                    'node': node_name,
                    'host': proxmox_host,
                    'cpu': cpu,
                    'cpus': cpus,
                    'mem': mem,
                    'maxmem': maxmem,
                    'mem_used_str': mem_used_str,
                    'mem_total_str': mem_total_str,
                    'mem_fraction': round(mem_fraction, 1),
                    'uptime': uptime,
                    'uptime_str': uptime_str,
                    'status': status,
                    'ip_address': ip_address
                }
                vm_data.append(vm_info)
        
        # Output as JSON to stdout
        print(json.dumps(vm_data, indent=2))
            
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
