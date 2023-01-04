(
{
	var paths,groups,oname;
	"P2Psc mini test..".postln;

	p = P2PSC();
	0.1.sleep();

	10.do {

		"Testing add Group..".postln;
		p.addGroup("test");
		0.1.sleep();

		groups = p.getGroups();
		if (groups[1] != "test", {"ERROR: AddGroup failed!".postln; groups.postln});

		"Testing remove Group..".postln;
		p.removeGroup("test");
		0.1.sleep();
		groups = p.getGroups();
		if (groups.size != 1, {"ERROR: RemoveGroup failed!".postln; groups.postln});

		"Testing add Path..".postln;
		p.addPath({}, "/test");
		0.1.sleep();

		paths = p.getPaths();
		if (paths != ["/hush", "/load", "/reset", "/say", "/test"], {"ERROR: addPath failed!".postln; paths.postln});

		"Testing remove Path..".postln;
		p.removePath("/test");
		0.1.sleep();
		paths = p.getPaths();
		if (paths != ["/hush", "/load", "/reset", "/say"], {"ERROR: RemovePaths failed!".postln; paths.postln });


		"Setting Name..".postln;
		if(p.name == nil,{ "ERROR: Name not initialized".postln});

		oname = p.name;
		p.setName("blabla");
		0.1.sleep();
		if(p.name != "blabla",{ "ERROR: Name not updated".postln; p.name});
		p.resetName();
		0.1.sleep();
		if(p.name != oname,{ "ERROR: Name not reset".postln; p.name});

		"Getting Peers..".postln;
		p.getPeers().postln;
	};



	p.resetGroups();
	p.resetPaths();
	p.resetName();

	p.disconnect();
	"Done!".postln;

}.fork;
)


// One Node
p=nil
(
fork {
	p = P2PSC();
	p.sync;
	p.setName("Alice"); // set your name accordingly
	p.sync;
	p.addPath({ |msg|
		var sleeptime = 1;
		var freq = 200; // Change this for every node
		msg.postln; //print message for debugging

		{SinOsc.ar(freq:freq)*0.5*EnvGen.kr(Env.perc(releaseTime:sleeptime-0.01), doneAction:2)}.play;
		fork {
			var nextpeer;
			var source_peer = msg[1].asString;
			var peers = p.getPeers();

			sleeptime.wait; // wait for one second

			// send to the next peer in our list
			nextpeer = peers.wrapAt(1+peers.indexOfEqual(source_peer));

			p.sendMsg("/"++nextpeer++"/ping", p.name)
		};
	},"/ping");
}
)

q.paths


// Another Node
(
q = P2PSC(port:3760);
q.setName("Bob"); // set your name accordingly

q.addPath({ |msg|
    var sleeptime = 1;
    var freq = 300; // Change this for every node
    msg.postln; //print message for debugging

    {SinOsc.ar(freq:freq)*0.5*EnvGen.kr(Env.perc(releaseTime:sleeptime-0.01), doneAction:2)}.play;
    fork {
        var nextpeer;
        var source_peer = msg[1].asString;
        var peers = q.getPeers();

        sleeptime.wait; // wait for one second

        // send to the next peer in our list
        nextpeer = peers.wrapAt(1+peers.indexOfEqual(source_peer));

        q.sendMsg("/"++nextpeer++"/ping", q.name)
    };
},"/ping");
)



// Use this to start sending OSC messages
(
// We include the sender's name to form a circle by sending it to the next peer
// in our (alphabetically sorted) peer list.
fork {
    var peer, peers;
    peers = p.getPeers();
    if (peers.size > 0,
        {
            peer = peers[0];
            ("Sending initial ping to:"+peer).postln;
            ("/"++peer++"/ping").postln;
            p.sendMsg("/"++peer++"/ping" , p.name)
        },
        {"Error: No other peers in the network"}
    )
}
)