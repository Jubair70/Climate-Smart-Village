var map; //define map object
//store each icon name in an object
var itemsNamesObj = {"1":"Village borders","2":"Mosque","3":"Eid-gah","4":"Temples","5":"Others Temple","6":"Market","7":"Hat","8":"Primary school","9":"Secondary school","10":"Collage","11":"Madrasha","12":"Boat ghat","13":"Communtiy Clinic","14":"Health complex","15":"EPI center","16":"other health centre","17":"post office","18":"union complex","19":"Govt office","20":"office","21":"Bank","22":"Irrigation pumps","23":"Other irrigation points (river","24":"CSV project's Self-help Group","25":"CSV project's Farmer Field School","26":"CSV project's PLA Group","27":"Road","28":"Main kachcha roads","29":"Small link roads","30":"Bridges","31":"Graveyard","32":"sosanghat","33":"Ponds","34":"Flood protection embankments","35":"Populated areas","36":"One-crop land areas","37":"Two-crops land areas","38":"three crop land","39":"unuse land","40":"River","41":"Bill area","42":"Forest","43":"Low lands","44":"High land","45":"Draught prone lands","46":"Water-logged prone lands","47":"Early rain affected lands","48":"late flood area","49":"flood prone area","50":"River erosion affected area","51":"late flood land","52":"Early flood affected lands","53":"High tempreture affected lands","54":"Foggy or winter affected lands","55":"govt land","56":" Canel","57":"Others"};
var center_lat = legends_data[0][7].split(' ')[0]; //map center lattitude
var center_lng = legends_data[0][7].split(' ')[1]; //map center longitude

var legendShapeProp = [{name:'1_Village borders', fill_color:'#FFFFFF', border_color:'#000000', fill_opacity:0, stroke_weight:4},{name:'35_Populated areas', fill_color:'#ffff00', border_color:'#ffff00', fill_opacity:0.5, stroke_weight:1},{name:'36_One-crop land areas', fill_color:'#7fbf7f', border_color:'#7fbf7f', fill_opacity:0.5, stroke_weight:1},{name:'37_Two-crops land areas', fill_color:'#329932', border_color:'#329932', fill_opacity:0.5, stroke_weight:1},{name:'38_three crop land', fill_color:'#008000', border_color:'#008000', fill_opacity:0.5, stroke_weight:1},{name:'39_Fellow land areas', fill_color:'#7f7f7f', border_color:'#7f7f7f', fill_opacity:0.5, stroke_weight:1},{name:'40_River', fill_color:'#0000cc', border_color:'#0000cc', fill_opacity:0.5, stroke_weight:1},{name:'41_Bil areas', fill_color:'#7f7fff', border_color:'#7f7fff', fill_opacity:0.5, stroke_weight:1},{name:'42_Forest', fill_color:'#009900', border_color:'#009900', fill_opacity:0.5, stroke_weight:1},{name:'43_Low lands', fill_color:'#db9356', border_color:'#db9356', fill_opacity:0.5, stroke_weight:1},{name:'44_High lands', fill_color:'#f4a460', border_color:'#f4a460', fill_opacity:0.5, stroke_weight:1},{name:'45_Draught prone lands', fill_color:'#49311c', border_color:'#49311c', fill_opacity:0.5, stroke_weight:1},{name:'46_Water-logged prone lands', fill_color:'#ff00ff', border_color:'#ff00ff', fill_opacity:0.5, stroke_weight:1},{name:'47_Early rain affected lands', fill_color:'#ff0080', border_color:'#ff0080', fill_opacity:0.5, stroke_weight:1},{name:'48_late flood area', fill_color:'#800080', border_color:'#800080', fill_opacity:0.5, stroke_weight:1},{name:'49_Flood affected lands', fill_color:'#bf7fbf', border_color:'#bf7fbf', fill_opacity:0.5, stroke_weight:1},{name:'50_River erosion affected area', fill_color:'#444444', border_color:'#444444', fill_opacity:0.5, stroke_weight:1},{name:'51_late flood land', fill_color:'#f9d1af', border_color:'#f9d1af', fill_opacity:0.5, stroke_weight:1},{name:'52_Early flood affected lands', fill_color:'#a52a2a', border_color:'#a52a2a', fill_opacity:0.5, stroke_weight:1},{name:'53_High tempreture affected lands', fill_color:'#660066', border_color:'#660066', fill_opacity:0.5, stroke_weight:1},{name:'54_Foggy or winter affected lands', fill_color:'#FFFFF1', border_color:'#FFFFF1', fill_opacity:0.5, stroke_weight:1},{name:'55_Govt  Khash land', fill_color:'#418688', border_color:'#418688', fill_opacity:0.5, stroke_weight:1},{name:'56_ Canel', fill_color:'#3232ff', border_color:'#3232ff', fill_opacity:0.5, stroke_weight:1},{name:'57_Others', fill_color:'#eeeeee', border_color:'#FFFFFF', fill_opacity:0.5, stroke_weight:1}];

function initMap() {
	//intialize map object
	map = new google.maps.Map(document.getElementById('social_map_container'), {
		zoom: 16,
		center: new google.maps.LatLng(parseFloat(center_lat), parseFloat(center_lng)),
		mapTypeId: 'hybrid',
		disableDefaultUI: true,
		zoomControl: true,
		mapTypeControl: true
	});

	var features = []; // array to store features
	var icons_arr = []; // array to store icons

	//function to add click listener event to each item
	var addListenersOnPolygon = function(item) {
		google.maps.event.addListener(item, 'click', function (event) {
			var objectType;
			if(typeof item.icon != 'undefined'){
	  	  	objectType = itemsNamesObj[item.icon.split('_')[1].split('/')[1]];//if item is geopoint
	  	  } else {
	  	  	objectType = item.id;//if item is geoshape/geotrace
	  	  }

	  	  var iconDesc = '<div><img src="/attachment/small?media_file=pcsv/attachments/'+item.picture+'" width="150"/></br>'+objectType+'</div>';
	  	  var infowindow = new google.maps.InfoWindow({
	  	  	content: iconDesc
	  	  });
	  	  infowindow.open(map);
	  	  infowindow.setPosition(event.latLng);
	  	});  
	}
	var polyShapesContainer = {}; // object to store polygons
	var areaContainer = {}; // object to store polygon area size
	for(var idx in legends_data) {
		var legendPicture = legends_data[idx][11];
		var legend = legends_data[idx][10].replace(". ", "_");
		if(legends_data[idx][8] == 'geopoint'){
			var lattitude = legends_data[idx][6].split(' ')[0];
			var longitude = legends_data[idx][6].split(' ')[1];
			var feature_single = { picture: legendPicture,'position': new google.maps.LatLng(lattitude, longitude), 'type': legends_data[idx][10].replace(". ", "_") };
			features.push(feature_single);
		} else {
			if(legends_data[idx][6] != null){
				var coordinates = legends_data[idx][6].split(";");
				
				var trace = [];
				coordinates.forEach(function(el){
					if(el != ''){
						var lt = el.trim().split(' ')[0];
						var ln = el.trim().split(' ')[1];
						var single_trace_point = {'lat':parseFloat(lt),'lng':parseFloat(ln)};
						trace.push(single_trace_point);
					}
				});
				
				if(legends_data[idx][8] == 'geotrace' || legend == '1_Village borders') {
					if (legend == '1_Village borders'){
						tracestrokeColor = '#000000';
						tracestrokeWeight = 4;
					} else {
						tracestrokeColor = '#FF0000';
						tracestrokeWeight = 2;
					}

					var tracePath = new google.maps.Polyline({
						path: trace,
						geodesic: true,
						strokeColor: tracestrokeColor,
						strokeOpacity: 1.0,
						strokeWeight: tracestrokeWeight,
						id: legend.split('_')[1],
						picture: legendPicture
					});

					tracePath.setMap(map);
					addListenersOnPolygon(tracePath)

				} else if (legends_data[idx][8] == 'geoshape' && legend != '1_Village borders'){

					village_border_color = findWithAttr(legendShapeProp, 'name', legend, 'border_color');
					village_fill_color = findWithAttr(legendShapeProp, 'name', legend, 'fill_color');
					village_fill_opacity = findWithAttr(legendShapeProp, 'name', legend, 'fill_opacity');
					village_stroke_weight =  findWithAttr(legendShapeProp, 'name', legend, 'stroke_weight');

					var ployshapes = new google.maps.Polygon({
						path: trace,
						geodesic: true,
						strokeColor: village_border_color,
						strokeOpacity: 0.5,
						strokeWeight: village_stroke_weight,
						fillColor: village_fill_color,
						fillOpacity : village_fill_opacity,
						id: legend.split('_')[1],
						picture: legendPicture
					});
					pgPos = polygonCenter(ployshapes);
					ployshapes['position'] = pgPos;
					var areaCount = google.maps.geometry.spherical.computeArea(ployshapes.getPath());
					polyShapesContainer[ployshapes.id] = ployshapes;
					areaContainer[ployshapes.id] =  areaCount;
				}
			}
		}

		var type = legends_data[idx][10].replace(". ", "_");
		
		if($.inArray(type, icons_arr) == -1){ 
			icons_arr.push(type);
		}
	}

	//sort polygon area count
	var sortedPolygonArea = [];
	for (var oox in areaContainer)
		sortedPolygonArea.push([oox, areaContainer[oox]])

	sortedPolygonArea.sort(function(a, b) {
		return a[1] - b[1]
	}).reverse();

	//place polygons according to area size
	for(var ttx in sortedPolygonArea){
		var sPolygon = polyShapesContainer[sortedPolygonArea[ttx][0]];
		sPolygon.setMap(map);
		addListenersOnPolygon(sPolygon);
	}
	
	//create icons with corresponding uri
	var iconBase = '/static/assets/img/CSVP_Legends/';
	var icons = {};
	
	icons_arr.forEach(function(elem){
		var icon_single = { 'icon': iconBase+elem+'.png' }
		icons[elem] = icon_single;
	});

	//function for adding marker to map
	function addMarker(feature) {
		var marker = new google.maps.Marker({
			picture: feature.picture,
			position: feature.position,
			icon: icons[feature.type].icon,
			map: map
		});
		addListenersOnPolygon(marker);
	}

	//placing marker for each feature
	for (var i = 0, feature; feature = features[i]; i++) {
		addMarker(feature);
	}
}

//find out center of a polygon
function polygonCenter(poly) {
	var lowx,
	highx,
	lowy,
	highy,
	lats = [],
	lngs = [],
	vertices = poly.getPath();

	for(var i=0; i<vertices.length; i++) {
		lngs.push(vertices.getAt(i).lng());
		lats.push(vertices.getAt(i).lat());
	}

	lats.sort();
	lngs.sort();
	lowx = lats[0];
	highx = lats[vertices.length - 1];
	lowy = lngs[0];
	highy = lngs[vertices.length - 1];
	center_x = lowx + ((highx-lowx) / 2);
	center_y = lowy + ((highy - lowy) / 2);
	return (new google.maps.LatLng(center_x, center_y));
}

//find one attribute with another
function findWithAttr(array, attr, value, retAttr) {
	for(var i = 0; i < array.length; i += 1) {
		if(array[i][attr] === value) {
			return array[i][retAttr];
		}
	}
	return -1;
}
