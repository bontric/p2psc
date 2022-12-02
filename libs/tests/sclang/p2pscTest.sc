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


