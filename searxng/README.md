Anna's Archive uses DDoS-Guard protection headers (verified via curl):

```
server: ddos-guard
set-cookie: __ddg8_=ivtAlu3BwZg5gqvK; Domain=.annas-archive.li; ...
set-cookie: __ddg10_=1770437376; Domain=.annas-archive.li; ...
```

This protection system:

- Detects automated/bot traffic patterns
- Blocks requests regardless of User-Agent headers
- Requires JavaScript challenge solving (not possible in SearXNG)
- Suspends violating IPs for 24 hours

Solution i using proxies
```
outgoing:
  proxies:
    http: http://proxy-server:port
    https: https://proxy-server:port
```