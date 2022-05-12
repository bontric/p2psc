(
~node.sendg("nodeA", "/scl/interpret", "
a = {|freq, t_gate| LeakDC.ar([SinOsc.ar(freq, mul:0.5) * EnvGen.kr(Env.perc(0.001, 3), t_gate)]!2)}.play;
~node.addpath(\"/ping\", {|msg|
	Task{
		a.set(\\t_gate, 1, \\freq, msg[1]);
        0.5.wait;
		~node.sendg(\"nodeB\", \"/ping\", 300);
	}.play
})
");
)
(
~node.sendg("nodeB", "/scl/interpret", "
a = {|freq, t_gate| LeakDC.ar([SinOsc.ar(freq, mul:0.5) * EnvGen.kr(Env.perc(0.001, 3), t_gate)]!2)}.play;
~node.addpath(\"/ping\", {|msg|
	Task{
		a.set(\\t_gate, 1, \\freq, msg[1]);
		0.5.wait;
		~node.sendg(\"nodeC\", \"/ping\", 500);
	}.play
})
");

~node.sendg("nodeC", "/scl/interpret", "
a = {|freq, t_gate| LeakDC.ar([SinOsc.ar(freq, mul:0.5) * EnvGen.kr(Env.perc(0.001, 3), t_gate)]!2)}.play;
~node.addpath(\"/ping\", {|msg|
	Task{
		a.set(\\t_gate, 1, \\freq, msg[1]);
		2.wait;
		~node.sendg(\"nodeA\", \"/ping\", 200);
	}.play
})
");
)

~node = P2psc();

~node.sendg("nodeA", "/ping", 200);

~node.sendg("ALL", "/scl/interpret", "~node.clearpaths; thisProcess.recompile;");

~node.sendg("ALL", "/scl/interpret", "{SinOsc.ar()}.play;");

~node.sendg("ALL", "/scl/interpret", "\"sudo reboot\".unixCmd");

~node.sendg("ALL", "/scl/interpret", "\"sudo shutdown -h now\".unixCmd");

