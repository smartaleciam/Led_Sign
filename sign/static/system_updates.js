        var socket0 = io.connect('http://' + document.domain + ':' + location.port);
        socket0.on('connect', function() {     var statusElement = document.getElementById('led_status');    statusElement.className = 'green led';   });

        socket0.on('update_time', function(data) {   
          var utcTime = new Date(data + ' UTC');  // Parse UTC time
          var localTime = utcTime.toLocaleTimeString();  // Convert to local time
          document.getElementById('s_time').textContent = data;
        });
        socket0.on('cpu_temp', function(data) {   document.getElementById('cpu_temp').textContent = data;   });
        socket0.on('cpu_usage', function(data) {   document.getElementById('cpu_usage').textContent = data;   });
        socket0.on('disk_free', function(data) {   document.getElementById('disk_free').textContent = data;   });
        socket0.on('batt_volt', function(data) {   document.getElementById('batt_volt').textContent = data;   });
        socket0.on('batt_percent', function(data) {   document.getElementById('batt_percent').textContent = data;   });
        socket0.on('speed', function(data) {
            document.getElementById('speed_up').textContent = formatBytes(data.speed_up) + '/s';   
            document.getElementById('speed_down').textContent = formatBytes(data.speed_down) + '/s';
        });

        socket0.on('disconnect', function(reason) {
          console.log('Connection has been disconnected.', reason);
          if (reason === 'ping timeout') {     var statusElement = document.getElementById('led_status');    statusElement.className = 'orange led';   }
          if (reason === 'transport close') {      var statusElement = document.getElementById('led_status');    statusElement.className = 'red led';    }
        });
 
        socket0.on('reconnect', function() {    var statusElement = document.getElementById('led_status');    statusElement.className = 'green led';    });

        
        var socket1 = io.connect('http://' + document.domain + ':8046');
        socket1.on('connect', function() {     var statusElement = document.getElementById('led_status1');    statusElement.className = 'green led';   });
//        socket1.on('cpu_temp', function(data) {   document.getElementById('cpu_temp').textContent = data;   });

        socket1.on('gps_location', function(data) {   document.getElementById('gps_location').textContent = data;   });

        socket1.on('disconnect', function(reason) {
          console.log('Connection has been disconnected.', reason);
          if (reason === 'ping timeout') {     var statusElement = document.getElementById('led_status1');    statusElement.className = 'orange led';   }
          if (reason === 'transport close') {      var statusElement = document.getElementById('led_status1');    statusElement.className = 'red led';    }
        });
 
        socket1.on('reconnect', function() {    var statusElement = document.getElementById('led_status1');     statusElement.className = 'green led';    });
 
function formatBytes(bytes, decimals = 2) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const dm = decimals < 0 ? 0 : decimals;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

            const i = Math.floor(Math.log(bytes) / Math.log(k));

            return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
        }        
        
function NotificationMessages() {
//    return [
//        {
//			icon: "error",
//			title: "Oh No",
//			subtitle: "Something really bad happened.",
//			actions: ["Close"]
//		},
//		{
//			icon: "error",
//			title: "Error",
//			subtitle: "The operation completed successfully.",
//			actions: ["OK"]
//		},
//		{
//			icon: "error",
//			title: "Critical Error",
//			subtitle: "An error has occurred while trying to display an error notification.",
//			actions: ["OK"]
//		},
//		{
//			icon: "warning",
//			title: "Failed to Save Changes",
//			actions: ["Retry","Cancel"]
//		},
//		{
//			icon: "warning",
//			title: "Download Failed",
//			actions: ["Retry","Cancel"]
//		},
//		{
//			icon: "warning",
//			title: "Notifications",
//			subtitle: "Notifications may include alerts, sounds, and icon badges.",
//			actions: ["Don’t Allow","Allow"]
//		},
//		{
//			icon: "success",
//			title: "Changes Saved",
//			actions: ["OK"]
//		},
//		{
//			icon: "success",
//			title: "Download Complete",
//			actions: ["OK"]
//		},
//		{
//			icon: "message",
//			title: "Mail Password Required",
//			subtitle: "Enter your password for user@domain.com.",
//			actions: ["Close","Continue"]
//		},
//		{
//			icon: "clock",
//			title: "Coffee Break",
//			subtitle: "In 5 minutes",
//			actions: ["Close","Snooze"]
//		},
//		{
//			icon: "up",
//			title: "Upgrade Now",
//			subtitle: "The current version will soon be obsolete. What are you waiting for?",
//			actions: ["Install","Details"]
//		}
//	];
}
