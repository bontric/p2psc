# p2psc 

p2psc -- short for "Peer 2 Peer Sound Control" -- is an OSC path registry and message routing tool. After running `p2psc`, you can send it OSC messages to receive information about other "peers" (people also running the p2psc application) in you *local* network. Additionally, you can send OSC messages which are forwarded to a peer, or a group of peers, by using their name or group, in the OSC path. While `p2psc` is a standalone application, it can be fully configured using OSC messages. This allows any OSC-capable application to communicate with `p2psc` and participants in the network. 

The main goal of p2psc is, to simplify the setup of networked music performances or installations. In most situations, you don't have to worry about the network configuration of participants, or even if some of the participants are available for a performance. Using `p2psc` you can program compositions which are dynamic in regards to participants and even their capabilities, as you are able to querry information about the participants in the network.

Here is an example scenario for using p2psc:

Suppose 3 people are joining together: Alice, Bob and Carol. They are in the same network and have `p2psc` installed and running. Immediately, `p2psc` will find all paricipants in the network and Alice can send an OSC message to her local p2psc node:

`</Bob/hello, 123>` 

Her local node will route this message only to Bob, if he subscribes the OSC path `/hello`.

To `subscribe` a path, Bob needs to inform his local node, which he can also do via OSC. This information is shortly after passed to Alice and Carol, so that everyone always knows which paths are available and who is connected. (See the Wiki for more details on the specific OSC messages)

But, as mentioned earlier *groups* are also supported. By default, every participant is in the `ALL` group. So Carol can send a message

`</ALL/hello, 123>`

Which is then forwarded to all participants who subscribe the `/hello` path. Participants can join or leave groups any time using OSC messages, which can be useful when changing groups is required for different compositions. Additionally, any participant can be in multiple groups at the same time.

To simplify the interactions with `p2psc` we provide libraries which simplify the communication with your local node. For example in Supercollider you can call simple functions to subscribe paths or join groups:

```sc
p = P2PSC(); // Creates a P2PSC object which connects to the locally running p2psc node

p.addGroup("/DRUMS"); // Join the "DRUMS" group to receive all messages, where the OSC path starts with /DRUMS
// Note: You still need to subscribe a path to actually receive a message

// Add the path "/test" which simply prints the incoming message
p.addPath({arg msg; msg.postln}, "/test");

// Send a message to everyone who is subscribing "/hello"
p.sendMsg("/ALL/hello", "Hello World!")
```

See this project's wiki for more information on the supported languages (supercollider for now, max/pd maybe in the future).


## Installation

> Note: P2PSC has been tested on mac os and linux, but does not officially support windows for now (It might work, but I didn't try it yet).
> 
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

