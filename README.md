# p2psc 


> Note: P2PSC has been tested on mac os and linux, but does not officially support windows for now

## Installation

This package uses pyhons *setuptools* to manage the installation process. After cloning this repository, simply run:

```bash
python -m pip install . 
```

You can also uninstall p2psc using this method:

```bash
python -m pip uninstall p2psc 
```

## Runnning
To start a p2psc node after the installation simply run

```bash
p2psc
```

You will not see any output by default, so you may want to use `-v` or `-vv` as an argument to see what's going on. 
To get a list of available commands use `p2psc --help`:

```
OSC p2psc Node

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Set configuration file path
  -a IP, --ip IP        Set ip address
  -p PORT, --port PORT  Set network port
  -n NAME, --name NAME  Set node name
  --version             show program's version number and exit
  -v, --verbose         set loglevel to INFO
  -vv, --very-verbose   set loglevel to DEBUG
```


## Configuration

p2psc is configured using a json based configuration file. To create one, simply run :


> Note: You can obviously pass any path here.
```
p2psc -c ~/.p2psc
```

and p2psc will generate a default configuration file. If you want to modify it, simply close p2psc and open the file (here at `~/.p2psc`)

```json
{
  "name": "RWYC81AE4U",
  "zeroconf": true,
  "ip": null,
  "port": 3760
}
```

+ `name`: Initially a random string is generated, but you may change it to any string
+ `zeroconf`: if set to `false`, the node will not discover peers in the network and will also not be discoverable by them.
+ `ip`: An IP address
+ `port`: a Port number

> Note: If `ip` is set to `null`, the application will try to find the compuiter's IP address. This can fail in more complicated network setups.

