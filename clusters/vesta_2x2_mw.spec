[clusters]
vesta_c1 =
    10.2.1.65:8091
    10.2.1.66:8091
vesta_c2 =
    10.2.1.67:8091
    10.2.1.68:8091

[workers]
apollo_w1 =
    10.2.1.60
apollo_w2 =
    10.2.1.60

[storage]
data = /data2
index = /data

[credentials]
rest = Administrator:password
ssh = root:couchbase

[parameters]
Platform = Physical
OS = CentOS 5.8 64-bit
CPU = Intel Core2 Quad Q8300
Memory = 32 GB
Disk = 2 x SSD