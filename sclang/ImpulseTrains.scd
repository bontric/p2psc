// Helpers for node control
~node.sendg("ALL", "/scl/interpret", "\"sudo reboot\".unixCmd");
~node.sendg("ALL", "/scl/interpret", "\"sudo shutdown -h now\".unixCmd");

// reset sclang
~node.sendg("ALL", "/scl/interpret", "~node.clearpaths; thisProcess.recompile;");

(
~node.sendg("ALL", "/scl/interpret", "
~packet = 5000.do{|i| n = \"a\" ++ n};
a = {|freq, t_gate| LeakDC.ar(EnvGen.ar(Env.perc(0.001, 0.001, curve:-12), t_gate))}.play;
~node.addpath(\"/ping\", {|msg|
a.set(\\t_gate, 1); // freq does not matter here
~node.sendg([\"ALL\"].choose , \"/ping\", ~packet);
});

~node.addpath(\"/plen\", {|msg|
msg.postln;
~packet = nil;
msg[1].rand.do{|i| ~packet = \"a\" ++ ~packet};
});
");
)

~node = ContactOsc();

~node.sendg("ALL", "/scl/interpret", "OSCdef(\"/ping\").free")

~node.sendg("ALL", "/ping", 200)

~node.sendg("ALL", "/plen", 40000)
