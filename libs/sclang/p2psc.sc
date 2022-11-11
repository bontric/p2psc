P2psc {
	var <>addr;
	var <>peers;
	var <>peersRoutine;
	var <>paths;
	var <>groups;
	var <>defaultPaths;
	var <name;

	*new { | ip="localhost", port=3760, peersInterval=5 |
		var o = super.new();
		o.addr = NetAddr.new(ip,port);
		o.groups = [];
		o.paths = [];

		// Map incoming peernames to peers variable
		OSCdef.newMatching(\p2psc\peernames, {|msg| o.peers = msg[1].asString.split($ )}, "/p2psc/peernames", o.addr).fix;

		// Request peernames periodically
		// Note: "asString" required here because the OSC message argument is technically a "Symbol" not a string
		// The .split($ ) is another speciality, where "$ " references a "space"
		o.peersRoutine = {loop{o.addr.sendMsg("/p2psc/peernames"); peersInterval.sleep}}.fork;

		// initialize default paths
		o.defaultPaths = "/say /hush /load /reset";
		// say: prints a message
		OSCdef.newMatching(\p2psc\say, {|msg| msg.postln;}, "/say", o.addr).fix;
		// hush: free a Oscdef
		OSCdef.newMatching(\p2psc\hush, {|msg| OSCdef(msg[1]).free;}, "/hush", o.addr).fix;
		// load a file from given path
		OSCdef.newMatching(\p2psc\load, {|msg| PathName.new(msg[1].asString).asAbsolutePath.load;}, "/load", o.addr).fix;
		// reset/reboot supercollider
		OSCdef.newMatching(\p2psc\reset, {thisProcess.recompile()}, "/reset", o.addr).fix;

		// TODO use local send or update function!
		o.addr.sendMsg("/p2psc/peerinfo", 1, "", o.defaultPaths);

		fork{o.getName()};

		// return object
		^o;
	}

	send { | path...args | addr.sendMsg(path, *args)}

	sendg { | group, path...args | this.send("/" ++ group ++ "/" ++ path, *args) }

	update {
		var remoteGroups=nil, remotePaths=nil, c = Condition();

		// Send node info
		this.send("/p2psc/peerinfo", 1, groups.join(" "), defaultPaths + paths.join(" "));

		// validate our groups/paths exist
		OSCdef.newMatching(\p2psc\pi, {|msg|
			var updateFailed = false;
			remoteGroups = msg[2].asString.split($ );
			remotePaths = msg[3].asString.split($ );

			groups.do{|g| if(remoteGroups.indexOfEqual(g) == nil, {updateFailed = true})};
			paths.do{|p| if(remotePaths.indexOfEqual(p) == nil, {updateFailed = true})};

			if (updateFailed, {"P2PSC ERR: peerinfo not synchronized!".postln});
			c.test=true;
			c.signal
		}, "/p2psc/peerinfo", addr);

		this.send("/p2psc/peerinfo");
		fork {
			c.halt(0.1);
			if (c.test == false,{"P2PSC ERR: Node is not responding!".postln});
			OSCdef(\p2psc\pi).free;
		}
	}

	getPaths { |node=nil|
		var c = Condition(false);
		var rPaths = nil;

		OSCdef.newMatching(\p2psc\paths, {|msg|
			rPaths = msg[2].asString.split($ );
			c.test = true;
			c.signal;
		},"/p2psc/paths", addr);

		if (node == nil,
			{this.send("/p2psc/paths")},
			{this.send("/p2psc/paths", node)}
		);

		c.hang(0.1);

		if (rPaths == nil, {"P2PSC ERR: Node is not responding!"}.postln);

		OSCdef(\p2psc\paths).free; // cleanup
		^rPaths; // return paths
	}

	addPath { |path, function|
		if (paths.indexOfEqual(path) != nil,
			{OSCdef(path).free},	// remove old OSC def if path exists
			{paths.add(path)}
		);

		// fix OSC defs to avoid confusion when using cmd+.
		OSCdef.newMatching(path, function, path, addr).fix;

		// Synchronize peer info with node
		this.update();
	}

	removePath {|path|
		var index;
		index = paths.indexOfEqual("/test");

		if ( index != nil, {
			OSCdef(path).free;
			paths.removeAt(index);
			this.update();
		},{
			"P2PSC Info: Trying to remove nonexistent path!".postln;
		})
	}

	resetPaths {
		paths = [];
		this.update();
	}

	getGroups { |node=nil|
		var c = Condition(false);
		var rGroups = nil;

		OSCdef.newMatching(\p2psc\groups, {|msg|
			rGroups = msg[1].asString.split($ );
			c.test = true;
			c.signal;
		},"/p2psc/groups", addr);

		if (node == nil,
			{this.send("/p2psc/groups")},
			{this.send("/p2psc/groups", node)}
		);

		c.hang(0.1);

		if (rGroups == nil, {"P2PSC Warning: Node is not responding!".postln});

		OSCdef(\p2psc\groups).free; //cleanup
		^groups; // return groups
	}

	addGroup { |group|
		// Note: if already in group -- do nothing
		if ( groups.indexOfEqual(group) == nil,
			{groups.add(group); this.update()}
		);
	}

	removeGroup {|group|
		var index;
		index = groups.indexOfEqual(group);

		if ( index != nil,
			{groups.removeAt(index); this.update()},
			{"P2PSC Info: Trying to remove nonexistent group!".postln})
	}

	resetGroups {
		groups = [];
		this.update();
	}

	getName {
		var c = Condition(false);

		OSCdef.newMatching(\p2psc\name, {|msg|
			name = msg[1];
			c.test = true;
			c.signal;
		},"/p2psc/name", addr);

		this.send("/p2psc/name");
		c.hang(0.1);

		if (name == nil, {"P2PSC Warning: Node is not responding!".postln});

		OSCdef(\p2psc\name).free; //cleanup
		^name; // return groups
	}

	disconnect {
		this.send("/p2psc/disconnect"); // Disconnect from node

		OSCdef(\p2psc\say).free;
		OSCdef(\p2psc\hush).free;
		OSCdef(\p2psc\load).free;
		OSCdef(\p2psc\reset).free;
		OSCdef(\p2psc\peernames).free;

		peersRoutine.stop;
	}
}