#!/usr/bin/env python3
"""Script to collect Proxmox node data and output as JSON."""

import os
import json
import sys
from proxmoxer import ProxmoxAPI

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
            timeout=60  # Increase timeout to 60 seconds
        )
        
        # Get list of nodes (this already includes the data we need)
        nodes = proxmox.nodes.get()
        
        # Extract the fields we want from nodes.get() response
        node_data = []
        for node in nodes:
            node_info = {
                'node': node.get('node', ''),
                'host': proxmox_host,
                'disk': node.get('disk', 0),
                'maxdisk': node.get('maxdisk', 0),
                'mem': node.get('mem', 0),
                'maxmem': node.get('maxmem', 0),
                'uptime': node.get('uptime', 0),
                'cpu': node.get('cpu', 0),
                'maxcpu': node.get('maxcpu', 0),
                'status': node.get('status', 'unknown')
            }
            node_data.append(node_info)
        
        # Output as JSON to stdout
        print(json.dumps(node_data, indent=2))
            
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
