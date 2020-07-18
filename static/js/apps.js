function run_app(app_name) {
    alert('Hello! ' + app_name);
}

let el = document.getElementById("run");
el.addEventListener("click", function(){run_app("Worktime is not run yet")}, false);


function create_table(data) {
	let table;
	let headers = Object.keys(data);
	table = '<table border="1">';
	table += '<tr>';
	headers.forEach(
		header => table = table + '<th>' + header + '</th>'
	);
	table = table + '</tr>';

	for (let i=0; i < data[headers[0]].length; i++) {
		table += '<tr>';
		headers.forEach(
			header => {
				table += '<td>';
				if (data[header].select){
					table += '<select>';
					// table += '<option>100</option>';
					data[header].select.forEach(
						slct => table += '<option value="slct">' + slct + '</option>'
					);
					table += '</select>';
				} else {
					table += data[header][i]
				}
				table += '</td>';
			}
		);
		table += '</tr>';
	};

	table = table + '</table>';
	return table
}