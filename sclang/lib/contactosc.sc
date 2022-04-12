p2pscOsc {
	var <>address;
	var <>nodeinfoUpdated;
	var nodeinfoReceived;
	var <>groups;
	var <>paths;
	var <>mypaths;
	var <>name;

	*new { | ip="localhost", port=3760 |
		var o = super.new();
		o.address = NetAddr.new(ip,port);
		o.nodeinfoUpdated = Condition(false);
		o.paths = [];
		o.groups = [];
		^o;
	}

	update { | tries=inf , interval=5 |
        var task;
		if(nodeinfoReceived == nil, {
			nodeinfoReceived = Condition(false);
			OSCdef.newMatching(\nodeinfo, {|msg|
				groups = msg[4].asString.split($ );
				paths = msg[5].asString.split($ );
				name = groups[0];
				nodeinfoReceived.test = true;
				nodeinfoReceived.signal;
			}, '/N//nodeinfo', address);
		});
		task = Task {
			this.groups = [];
			this.paths = [];
			this.name = [];

			tries.do { |i|
				this.sendn("/nodeinfo");
				nodeinfoReceived.hang(interval);
				if(nodeinfoReceived.test,
					{
						nodeinfoReceived.test = false;
						nodeinfoUpdated.test = true;
						nodeinfoUpdated.signal;
						"p2psc node updated".postln;
						task.stop;

					},
					{if( (i + 1) == tries, {"Error: Failed to update".postln}, {"Retrying..".postln})}

				)
			};
		}.play;
	}

	send { | path...args | address.sendMsg(path, *args)}

	sendg { | group, path...args | this.send("/" ++ group ++ "/" ++ path, *args) }

	sendn { | path...args | this.send("/N/" ++ path, *args) }

	joingroup { | group |
		Task {
			address.sendMsg("/N//joingroup", group);
			this.update(1,1);
			nodeinfoUpdated.hang(1);
			nodeinfoUpdated.test = false;
			if (groups.find([group]) == nil,
				{("Error: Failed to join group:"+group).postln}, {"Joined group:"+this.group});
		}.play
	}

	leavegroup { | group |
		Task {
			address.sendMsg("/N//leavegroup", group);
			this.update(1,1);
			nodeinfoUpdated.hang(1);
			nodeinfoUpdated.test = false;
			if (groups.find([group]) != nil,
				{("Error: Failed to leave group:"+group).postln}, {"Left group:"+group});
		}.play
	}

	cleargroups {address.sendMsg("/N//cleargroups");this.update(1,1);}

	addpath { | path, function |
		OSCdef.newMatching(path, function, path, address);
		Task {
			address.sendMsg("/N//addpath", path);
			this.update(1,1);
			nodeinfoUpdated.hang(1);
			nodeinfoUpdated.test = false;
			if (paths.find([path]) == nil,
				{("Error: Failed to add path:"+path).postln}, {
					("Added path:"+path).postln;
			});
		}.play
	}

	delpath { | path, function |
		OSCdef(path).free;
		Task {
			address.sendMsg("/N//delpath", path);
			this.update(1,1);
			nodeinfoUpdated.hang(1);
			nodeinfoUpdated.test = false;
			if (paths.find([path]) != nil,
				{("Error: Failed to delete path:"+path).postln}, {
					("Deleted path:"+path).postln;
			});
		}.play
	}

	clearpaths {address.sendMsg("/N//clearpaths");this.update(1,1);}
}

