# nouns, topic identification

First thought is to do things by path, like 
`network-devices / unifi / basement-switch.md` or `software / loki / general-tips.md` but I think that
conflates things.

* Main article for a noun can live anywhere, free folder structure for personal logical discovery (which
  could be flat or deeply nested or whatever). Obsidian does a good job of updating links if you do this.
* Other pages provide indexing and categories (devices-by-ip.md, or software-in-tiles.md). This should
  generally be denormalized into the referenced page as well (the IP address is specified in the entity page
  as well as in the devices-by-ip.md list)

## Data sources

A big question is when and how to cross into a free-text space. "In an MCP server" seems to be the basic
answer, but we can call it eagerly or on demand, context-stuffed or agentic. Let's work some examples and
see what seems useful.

### Unifi

Network is a good source of discovery and various identities (IP addresses, hostnames). Terraform provider
