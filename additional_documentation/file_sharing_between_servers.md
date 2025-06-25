File sharing can be established with the servers to use the same mount folder(s) in each computer.

In case of default configuration, NFS likes to use the port 2049, which clashes with the default docker reservation ports.

In order to fix this problem, we can change NFS to use port 2049 (and 20491 for mountd).

## Configure nfs-kernel-server

First, open the file:

```
sudo nano /etc/default/nfs-kernel-server
```

Then, add these configurations to the file:

```
RPCNFSDARGS="-p 20490"
# Custom NFS server port
RPCMOUNTDOPTS="-p 20491"
# Custom mountd port
STATDARGS="--port 20492 --outgoing-port 20493"
# Custom statd ports
RPCMOUNTDOPTS="--manage-gids"
```

## Services

Open file for editing:

```
sudo nano /etc/services
```

Find nfs and change ports from 2049 to 20490:

Default setting:
```
nfs             2049/tcp                       # Network File System
nfs             2049/udp                       # Network File System
```

Change to use port 20490:

```
nfs             2049/tcp                       # Network File System
nfs             2049/udp                       # Network File System
```

## nfs.conf

Open file for editing:

```
sudo nano /etc/nfs.conf
```

Add these configurations to correct sections:

```
[mountd]
port=20491
manage-gids=y

[nfsd]  
port=20490

[statd]
port=20492
outgoing-port=20493
```

## Restart Services

After everything is ready, restart all services:
```
sudo systemctl restart rpcbind
sudo systemctl restart nfs-kernel-server
sudo systemctl restart nfs-idmapd
```