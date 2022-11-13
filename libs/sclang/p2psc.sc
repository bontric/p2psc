P2psc {
	var <>addr;
	var <>peers;
	var <>peersRoutine;
	var <>paths;
	var <>groups;
	var <>defaultPaths;
	var <>name;
	var >osc_peernames, >osc_say, >osc_hush, >osc_load, >osc_reset;

	*new { | ip="localhost", port=3760, peersInterval=5 |
		var o = super.new();
		o.addr = NetAddr.new(ip,port);
		o.groups = [];
		o.paths = Dictionary();

		// Map incoming peernames to peers variable
		// Note: "asString" required here because the OSC message argument is technically a "Symbol"
		// not a string. The .split($ ) is another speciality, where "$ " references a "space"
		o.osc_peernames = OSCFunc(
			{|msg| o.peers = msg[1].asString.split($ )},"/p2psc/peernames", o.addr).fix;

		// Request peernames periodically
		o.peersRoutine = {loop{o.addr.sendMsg("/p2psc/peernames"); peersInterval.sleep}}.fork;

		// initialize default paths
		o.defaultPaths = "/say /hush /load /reset";
		// say: prints a message
		o.osc_say = OSCFunc({|msg| msg.postln;}, "/say", o.addr).fix;
		// hush: free a Oscdef
		o.osc_hush = OSCFunc({|msg| o.resetPaths()}, "/hush", o.addr).fix;
		// load a file from given path
		o.osc_load = OSCFunc(
			{|msg| PathName.new(msg[1].asString).asAbsolutePath.load},"/load", o.addr).fix;
		// reset/reboot supercollider
		o.osc_reset = OSCFunc({thisProcess.recompile()}, "/reset", o.addr).fix;

		fork{o.update()};

		// return object
		^o;
	}

	send { | path...args | addr.sendMsg(path, *args)}

	update {
		var remoteGroups=nil, remotePaths=nil, c = Condition(), ofunc;

		// Send node info
		this.send("/p2psc/peerinfo", 1, groups.join(" "), defaultPaths + paths.keys.asList().join(" "));

		// validates our groups/paths exist
		ofunc = OSCFunc({|msg|
			var updateFailed = false;
			remoteGroups = msg[2].asString.split($ );
			remotePaths = msg[3].asString.split($ );

			groups.do{|g| if(remoteGroups.indexOfEqual(g) == nil, {updateFailed = true})};
			paths.keys.asList().do{|p| if(remotePaths.indexOfEqual(p) == nil, {updateFailed = true})};

			if (updateFailed, {"P2PSC ERR: peerinfo not synchronized!".postln});

			this.name = remoteGroups[0];
			c.test=true;
			c.signal
		}, "/p2psc/peerinfo", addr);

		this.send("/p2psc/peerinfo");

		fork {
			c.hang(0.1);
			if (c.test == false,{"P2PSC ERR: Node is not responding!".postln});
			ofunc.free;
		}
	}

	getPaths { |node=nil|
		var c = Condition(false);
		var rPaths = nil;

		var ofunc = OSCFunc.newMatching(\p2psc_paths, {|msg|
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

		ofunc.free; // cleanup
		^rPaths; // return paths
	}

	addPath { |path, function, matching=false|
		if (paths.at(path) != nil,
			{paths.at(path).free}	// free old OSC def if path exists
		);

		// Note: fix OSC defs to avoid confusion when using cmd+.
		if(matching,
		{paths.put(path,
				OSCdef.newMatching(path, function, path, addr).fix)},
		{paths.put(path,
				OSCdef(path, function, path, addr).fix)}
		);

		// Synchronize peer info with node
		this.update();
	}

	removePath {|path|
		if ( paths.get(path) != nil, {
			paths.at(path).free;
			paths.removeAt(path);
			this.update();
		},{
			"P2PSC Info: Trying to remove nonexistent path!".postln;
		})
	}

	resetPaths {
		// free old osc functions
		paths.values.do{|ofunc| ofunc.free};
		paths = Dictionary();
		this.update();
	}

	getGroups { |node=nil|
		var c = Condition(false), rGroups = nil, ofunc;

		ofunc = OSCFunc({|msg|
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

		ofunc.free; //cleanup
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

	disconnect {
		this.resetPaths();
		this.resetGroups();
		this.send("/p2psc/disconnect"); // Disconnect from node

		this.osc_peernames.free;
		this.osc_say.free;
		this.osc_hush.free;
		this.osc_load.free;
		this.osc_reset.free;

		peersRoutine.stop;
	}
}