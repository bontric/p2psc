P2PSC {
	var addr;
	var <paths;
	var <groups;
	var <name;
	var synclock;

	*new { | ip="localhost", port=3760 |
		var o = super.newCopyArgs(NetAddr.new(ip,port), Dictionary(), [], nil, Semaphore(1));

		o.resetPaths(); // set default paths

		CmdPeriod.doOnce({o.disconnect});

		// return object
		^o;
	}

	sendMsg { | path...args | addr.sendMsg(path, *args)}

	update {
		fork {
			var remoteGroups=nil, remotePaths=nil, c = Condition(), ofunc;

			synclock.wait;

			// Send node info
			this.sendMsg("/p2psc/peerinfo", 1, groups.join(" "), paths.keys.asList().join(" "));

			// validates our groups/paths exist
			ofunc = OSCFunc({|msg|
				var updateFailed = false;
				remoteGroups = msg[2].asString.split($ );
				remotePaths = msg[3].asString.split($ );

				groups.do{|g| if(remoteGroups.indexOfEqual(g) == nil, {updateFailed = true})};
				paths.keys.asList().do{|p| if(remotePaths.indexOfEqual(p) == nil, {updateFailed = true})};

				if (updateFailed, {"ERROR: (P2PSC) peerinfo not synchronized!".postln});

				if (name != nil && name != remoteGroups[0],
					{"P2PSC Info: Name Changed to:"+ remoteGroups[0]});

				name = remoteGroups[0];
				c.unhang;
			}, "/p2psc/peerinfo", addr);

			name = nil; // reset name to check whether request worked

			this.sendMsg("/p2psc/peerinfo");
			fork {0.1.wait;c.unhang};
			c.hang;

			if (name == nil,{"ERROR: (P2PSC) Node is not responding!".postln});
			ofunc.free;

			synclock.signal;
		}
	}

	getPeers {
		var c = Condition(false), rPeers = nil, ofunc;

		synclock.wait;
		ofunc = OSCFunc({|msg|
			rPeers = msg[1].asString.split($ );
			c.unhang;
		},"/p2psc/peernames", addr);

		this.sendMsg("/p2psc/peernames");
		fork {0.1.wait;c.unhang};
		c.hang;

		if (rPeers == nil, {"ERROR: (P2PSC) Node is not responding!".postln});

		ofunc.free; // cleanup
		synclock.signal;

		if (rPeers != nil,
			{^(rPeers.sort)}, // return peers
			{^rPeers}
		)
	}

	getPaths { |peer=nil|
		var c = Condition(false), rPaths = nil, ofunc;

		synclock.wait;
		ofunc = OSCFunc({|msg|
			rPaths = msg[2].asString.split($ );
			c.test = true;
			c.signal;
		},"/p2psc/paths", addr);

		if (peer == nil,
			{this.sendMsg("/p2psc/paths")},
			{this.sendMsg("/p2psc/paths", peer)}
		);

		fork {0.1.wait;c.unhang};
		c.hang;

		if (rPaths == nil, {"ERROR: (P2PSC) Peer is not responding!".postln});

		ofunc.free; // cleanup
		synclock.signal;

		if (rPaths != nil,
			{^(rPaths.sort)}, // return paths
			{^rPaths}
		)
	}

	addPath { |function, path, matching=false|
		if (paths.at(path) != nil,
			{paths.at(path).free}	// free old OSC def if path exists
		);

		if (matching,
		{paths.put(path,
				OSCFunc.newMatching(function, path, addr))},
		{paths.put(path,
				OSCFunc(function, path, addr))}
		);

		// Synchronize peer info with node
		this.update();
	}

	removePath {|path|
		if ( paths.at(path) != nil, {
			paths.at(path).free;
			paths.removeAt(path);
			this.update();
		},{
			"P2PSC Info: Trying to remove nonexistent path!".postln;
		})
	}

	resetPaths {
		fork {
			synclock.wait;
			// free old osc functions
			paths.values.do{|ofunc| ofunc.free};
			paths = Dictionary();


			// Add default paths
			// say: Prints the meassage
			paths.put("/say", OSCFunc({|msg| msg.postln}, "/say", addr));

			// hush: Frees all OSCdefs
			paths.put("/hush", OSCFunc({|msg| this.resetPaths()}, "/hush", addr));

			// load: Loads a file from given path
			paths.put("/load", OSCFunc({|msg| PathName.new(msg[1].asString).asAbsolutePath.load}, "/load", addr));

			// reset: Recompile class interpreter
			paths.put("/reset", OSCFunc({thisProcess.recompile()}, "/reset", addr));

			synclock.signal;
			this.update();
		}
	}

	getGroups { |peer=nil|
		var c = Condition(false), rGroups = nil, ofunc;
		synclock.wait;

		ofunc = OSCFunc({|msg|
			rGroups = msg[1].asString.split($ );
			c.test = true;
			c.signal;
		},"/p2psc/groups", addr);

		if (peer == nil,
			{this.sendMsg("/p2psc/groups")},
			{this.sendMsg("/p2psc/groups", peer)}
		);

		fork {0.1.wait;c.unhang};
		c.hang;

		if (rGroups == nil, {"P2PSC Warning: Node is not responding!".postln});

		ofunc.free; //cleanup
		synclock.signal;

		if (rGroups != nil,
			{^(rGroups.sort)}, // return groups
			{^rGroups}
		)
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

	setName { |name|
		name = name;
		this.sendMsg("/p2psc/name", name);
		this.update();
	}

	resetName {
		name = nil;
		this.sendMsg("/p2psc/name", "");
		this.update();
	}

	disconnect {
		this.resetPaths();
		this.resetGroups();
		this.sendMsg("/p2psc/disconnect"); // Disconnect from node
	}
}