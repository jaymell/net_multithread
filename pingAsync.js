/* 
async pinging 
. needs better way to iterate through range
	of IPs
*/

var ip = require("ip-address");
var cp = require("child_process");
var q = require("q");

function pingIt(address) {
	var deferred = q.defer();
	var ping = cp.exec("ping -c 5 " + address);
	ping.on('exit', function(code) {
		// console.log('Address: '+address, ' Code: '+code)
		if (code == 0) deferred.resolve(address);
		else deferred.reject(address);
	});
	ping.on('error', function(err) {
		deferred.resolve(address);
	});
	return deferred.promise;
}

var a = new ip.Address4("192.168.1.1");
var results = [];

for(var i = 1; i<15; ++i) {
	a = new ip.Address4( "192.168.1." + i );
	//console.log('address: ' + a.address)
	pingIt(a.address).then(
		function(answer) { 
			results.push(answer);
		}, 
		function(err) {
			console.log('Unreachable: ' + err);
		}
	);
}

