function createDonutChart(container, txtitle, pie_json) {
    Highcharts.chart(container, {
        chart: {
            plotBackgroundColor: null,
            plotBorderWidth: 1,
            plotShadow: false,
            width:250
        },
        title: {
            text: txtitle,
            align: 'center',
            verticalAlign: 'top',
            y: 120
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.y}%</b>'
        },
        plotOptions: {
            pie: {
                dataLabels: {
                    enabled: true,
                    connectorWidth: 0,
                    connectorPadding: -50
                },
                formatter: function () {
			return Highcharts.numberFormat(this.percentage,0) + '%';
		}
            }
        },
        credits: {
            enabled: false
        },
        series: [{
            type: 'pie',
            name: txtitle,
            innerSize: '50%',
            data: pie_json
        }]
    });
}


function createBarChart(container,txtitle,dataset,charttype,categories) {
    if(typeof dataset == 'string'){
        dataset = JSON.parse(dataset);
    }
    Highcharts.chart(container, {
        chart: {
            type: charttype,
            plotBorderWidth: 1
        },
        legend: {
            layout: 'horizontal',
            align: 'left',
            verticalAlign: 'top',
            floating: true,
            backgroundColor: '#FFFFFF',
            y:30,
            x:70,
	    itemStyle: {
		color: '#000',
		fontSize:'10px'
	    }
            

        },
        title: {
            text: txtitle,
            style: {
                    fontSize:'12px'
                }
        },
        xAxis: {
            categories: categories,
            crosshair: false
        },
        yAxis: {
            min: 0,
            title: {
                text: ''
            }
        },
        tooltip: {
            headerFormat: '<span style="font-size:8px">{point.key}</span><table>',
            pointFormat: '<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
                '<td style="padding:0"><b>{point.y:.0f}%</b></td></tr>',
            footerFormat: '</table>',
            shared: true,
            useHTML: true
        },
        credits: {
            enabled: false
        },
        plotOptions: {
            column: {
                dataLabels: {
                    enabled: true,
                    style:{
                        fontSize:'10px'
                    },
		    formatter: function () {
			return Highcharts.numberFormat(this.y,0) + '%';
		    }
                },
                pointPadding: 0.2,
                borderWidth: 0
            }
        },
        series: dataset
    });
}

function createBarChartwithoupercent(container,txtitle,dataset,charttype,categories) {
    if(typeof dataset == 'string'){
        dataset = JSON.parse(dataset);
    }
    Highcharts.chart(container, {
        chart: {
            type: charttype,
            plotBorderWidth: 1
        },
        legend: {
            layout: 'horizontal',
            align: 'left',
            verticalAlign: 'top',
            floating: true,
            backgroundColor: '#FFFFFF',
            y:30,
            x:70,
	    itemStyle: {
		color: '#000',
		fontSize:'10px'
	    }
            

        },
        title: {
            text: txtitle,
            style: {
                    fontSize:'12px'
                }
        },
        xAxis: {
            categories: categories,
            crosshair: false
        },
        yAxis: {
            min: 0,
            title: {
                text: ''
            }
        },
        tooltip: {
            headerFormat: '<span style="font-size:8px">{point.key}</span><table>',
            pointFormat: '<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
                '<td style="padding:0"><b>{point.y:.0f}</b></td></tr>',
            footerFormat: '</table>',
            shared: true,
            useHTML: true
        },
        credits: {
            enabled: false
        },
        plotOptions: {
            column: {
                dataLabels: {
                    enabled: true,
                    style:{
                        fontSize:'10px'
                    },
		    formatter: function () {
			return Highcharts.numberFormat(this.y,0) + '';
		    }
                },
                pointPadding: 0.2,
                borderWidth: 0
            }
        },
        series: dataset
    });
}

function filterByProperty(array, prop, value) {
    var filtered = [];
        value.forEach(function(element) {
           for (var i = 0; i < array.length; i++) {
            var obj = array[i];
            if (obj[prop] == element) {
                filtered.push(obj);
            }
        }
    });
    return filtered;
}
