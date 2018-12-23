var  summary_array = [{"name":"date","Bangla":"তারিখ","English":"Date"},{"name":"ngo","Bangla":"NGO","English":"NGO"},{"name":"district","Bangla":"জেলা","English":"District"},{"name":"upazila","Bangla":"উপজেলা","English":"Upazila (sub-district)"},{"name":"union","Bangla":"ইউনিয়ন","English":"Union"},{"name":"village","Bangla":"গ্রামের নাম","English":"Name of the village"},{"name":"location_bn","Bangla":"অবস্থান (বাংলা)","English":"অবস্থান (বাংলা)"},{"name":"location","Bangla":"Location (English)","English":"Location (English)"},{"name":"area_size","Bangla":"আয়তন (বঃকিঃমিঃ)","English":"Area size (s.k.m.)"},{"name":"population","Bangla":"জনসংখ্যা","English":"Population"},{"name":"hh_number","Bangla":"মোট খানা সংখ্যা","English":"Number of total Household"},{"name":"high_sensitive_hh","Bangla":"বেশী সংবেদনশীল খানা সংখ্যা","English":"Number of high sensitive household"},{"name":"medium_sensitive_hh","Bangla":"মধ্যম সংবেদনশীল খানা সংখ্যা","English":"Number of medium sensitive household"},{"name":"low_sensitive_hh","Bangla":"কম সংবেদনশীল খানা সংখ্যা","English":"Number of low sensitive household"},{"name":"average_member_hh","Bangla":"খানা প্রতি গড় সদস্য সংখ্যা","English":"Average number of household member per household"},{"name":"average_male_earning_per_hh","Bangla":"খানা প্রতি গড়ে উপার্জনক্ষম পুরষ সদস্য সংখ্যা","English":"Average number of male earning member per household"},{"name":"average_female_earning_per_hh","Bangla":"খানা প্রতি গড়ে উপার্জনক্ষম নারী সদস্য সংখ্যা","English":"Average number of female earning member per household"},{"name":"villagers_main_occupation_bn","Bangla":"গ্রামের মানুষের প্রধান প্রধান পেশা (বাংলা)","English":"গ্রামের মানুষের প্রধান প্রধান পেশা (বাংলা)"},{"name":"villagers_main_occupation","Bangla":"Occupations of the villagers (English)","English":"Occupations of the villagers (English)"},{"name":"hh_average_income","Bangla":"খানা প্রতি মাসে গড় আয় (টাকা)","English":"Average monthly income per family (in Taka)"},{"name":"hh_average_expenditure","Bangla":"খানা প্রতি মাসে গড় ব্যয় (টাকা)","English":"Average monthly expenditure per family (in Taka)"},{"name":"hh_average_food_expenditure","Bangla":"খানা প্রতি মাসে গড়ে খাদ্য ব্যয় (টাকা)","English":"Average monthly food expenditures per family (in Taka)"},{"name":"hh_average_productive_assets","Bangla":"খানা প্রতি গড়ে উৎপাদনশীল সম্পদের - জমি ব্যতীত মূল্য (টাকা)","English":"Average value of productive assets, other than land, owned by per family (in Taka)"},{"name":"percentage_cultivable_land_family","Bangla":"% পরিবারের নিজস্ব আবাদী জমি আছে","English":"% of family own cultivable land"},{"name":"percentage_cultivable_leased_land_family","Bangla":"% পরিবারের লিজ বা বর্গা চাষের জমি আছে","English":"% of family cultivate leased in or shared land"},{"name":"percentage_hh_use_homestead","Bangla":"% পরিবার বসতবাড়ীতে সবজি চাষ করে","English":"% of households use the land space of homestead for vegetable cultivation or other productive purpose"},{"name":"village_main_crops_bn","Bangla":"গ্রামের প্রধান প্রধান ফসল কি কি (বাংলা)","English":"গ্রামের প্রধান প্রধান ফসল কি কি (বাংলা)"},{"name":"village_main_crops","Bangla":"Main crops of the village (English)","English":"Main crops of the village (English)"},{"name":"percentage_hh_faced_hunger","Bangla":"% পরিবারকে বছরের কোন না কোন সময়ে ক্ষুধার সম্মুখিন হতে হয়","English":"% of household experience hunger situation"},{"name":"hunger_duration","Bangla":"বছরে গড়ে যে কয় মাস ক্ষুধার সম্মুখিন হতে হয়","English":"Average duration hunger situation in a year (month)"},{"name":"main_natural_disaster_bn","Bangla":"প্রধান প্রধান প্রাকৃতিক দুর্যোগ (বাংলা)","English":"প্রধান প্রধান প্রাকৃতিক দুর্যোগ (বাংলা)"},{"name":"main_natural_disaster","Bangla":"Main natural disaster of the village (English)","English":"Main natural disaster of the village (English)"},{"name":"primary_school","Bangla":"প্রাথমিক বিদ্যালয়ের সংখ্যা","English":"Number of Primary School"},{"name":"secondary_school","Bangla":"মাধ্যমিক বিদ্যালয়ের সংখ্যা","English":"Number of Secondary School"},{"name":"madrasa","Bangla":"মাদ্রাসার সংখ্যা","English":"Number of Madrasha"},{"name":"market","Bangla":"বাজারের সংখ্যা","English":"Number of Market"},{"name":"hat","Bangla":"হাটের সংখ্যা","English":"Number of Hat"},{"name":"mosque","Bangla":"মসজিদের সংখ্যা","English":"Number of Mosque"},{"name":"flood_shelter","Bangla":"বন্যা আশ্রয় কেন্দ্র সংখ্যা","English":"Numbe of flood shelter"},{"name":"eidgah","Bangla":"ঈদ গা’র সংখ্যা","English":"Number of Eid-gah"},{"name":"temple","Bangla":"মন্দিরের সংখ্যা","English":"Number of temple"},{"name":"boat_ghat","Bangla":"নৌকা ঘাটের সংখ্যা","English":"Number of boat ghat"},{"name":"community_clinic","Bangla":"কমিউনিটি ক্লিনিক সংখ্যা","English":"Number of Communtiy Clinic"},{"name":"health_complex","Bangla":"হেল্থ কমপেলেক্স সংখ্যা","English":"Number of Health Complex"},{"name":"epi_center","Bangla":"ই.পি.আই সেন্টার সংখ্যা","English":"Number of EPI center"},{"name":"post_office_distance","Bangla":"গ্রাম থেকে পোষ্ট অফিসের দূরত্ব (কি.মি.)","English":"Distance to Post office from the village (KM)"},{"name":"up_distance","Bangla":"গ্রাম থেকে ইউনিয়ন পরিষদের দূরত্ব (কি.মি.)","English":"Distance to Union Parishad from the village (KM)"},{"name":"upazila_office_distance","Bangla":"গ্রাম থেকে উপজেলার অন্যান্য সরকারী অফিসের দূরত্ব (কি.মি.)","English":"Distance to Upazila Offices from the village (KM)"},{"name":"bank_distance","Bangla":"গ্রাম থেকে ব্যাংকের দুরত্ব (কি.মি.)","English":"Distance to Bank from the village (KM)"}];

function changeLanguage(obj) {
	value = obj.value;
	if(value == 'b'){
		$('.lang_en').hide();
		$('.lang_bd').show();
	} else {
		$('.lang_en').show();
		$('.lang_bd').hide();
	}
}

function generateCropTableRows(rowData){
	var tbody = '';
	for(var i = 0; i < rowData.length; i++){
		tbody += '<tr>';
		for(var j = 0; j < rowData[i].length; j++){
			if(j < 2){
				tbody += '<td>';
				if(j == 0){
					tbody += '<span class="lang_en">'+rowData[i][j]+'</span>';
				} else if(j == 1) {
					tbody += '<span class="hide_lang lang_bd">'+rowData[i][j]+'</span></td>';
				}	
			} else if (j > 1 && j < 14){
				if(rowData[i][j] == 1){
					tbody += '<td class="stripe-background"></td><td></td>';
				} else if (rowData[i][j] == 2) {
					tbody += '<td></td><td class="stripe-background"></td>';
				} else if (rowData[i][j] == 3){
					tbody += '<td class="stripe-background"></td><td class="stripe-background"></td>';
				} else if(rowData[i][j] == 4) {
					tbody += '<td></td><td></td>';
				}
			} else if (j > 13 && j < 17) {
				tbody += '<td class="text-center">'+rowData[i][j]+'</td>';
			} else if (j == 17){
				var form_id = rowData[i][j];
			} else if (j == 18) {
				var instance_id = rowData[i][j];
			}
		}
		tbody += '</tr>';
		
	}
	generateEditLink('crop_table_edit_instance',form_id,instance_id);
	return tbody;
}

function generateImapctTableRows(rowData){
	var tbody = '';
	for(var i = 0; i < rowData.length; i++){
		tbody += '<tr>';
		for(var j = 0; j < rowData[i].length; j++){
			if(j < 4){
				if(j == 0){
					tbody += '<td><span class="lang_en">'+rowData[i][j]+'</span>';
				} else if(j == 1) {
					tbody += '<span class="hide_lang lang_bd">'+rowData[i][j]+'</span></td>';
				} else if(j == 2) {
					tbody += '<td><span class="lang_en">'+rowData[i][j]+'</span>';
				} else if(j == 3) {
					tbody += '<span class="hide_lang lang_bd">'+rowData[i][j]+'</span></td>';
				}
			} else if (j > 3 && j < 16){
				if(rowData[i][j] == 1){
					tbody += '<td class="stripe-background"></td><td></td>';
				} else if (rowData[i][j] == 2) {
					tbody += '<td></td><td class="stripe-background"></td>';
				} else if (rowData[i][j] == 3){
					tbody += '<td class="stripe-background"></td><td class="stripe-background"></td>';
				} else if(rowData[i][j] == 4) {
					tbody += '<td></td><td></td>';
				}
			} else if(j == 16){
				var form_id = rowData[i][j];
			} else if(j == 17){
				var instance_id = rowData[i][j];
			}
		}
		tbody += '</tr>';
	}
	generateEditLink('climate_table_edit_instance',form_id,instance_id);
	return tbody;
}

function setCookie(cookieName, cookieValue) {
	$.cookie(cookieName, cookieValue, { expires: 365 });
}

$(".accordion-heading a").click(function (event) {
	if ($(this).find($(".fa")).hasClass('fa-caret-right'))  {
		$(this).find($(".fa")).removeClass('fa-caret-right');
        $(this).find($(".fa")).addClass('fa-caret-down');
	} else {
		$(this).find($(".fa")).removeClass('fa-caret-down');
        $(this).find($(".fa")).addClass('fa-caret-right');
	} 
});

function generateStepArr(start,end,step){
	var arr = [];
	for(var i = start; i < end; i=i+step){
		arr.push(i);
	}
	return arr;
}

function checkNullValue(value){
	if(value == null){
		value = '';
	}
	return value;
}

function generateSeasonTableRows(rowData){
	var exp_arr = generateStepArr(2,38,3);
	var exp_bn_arr = generateStepArr(3,38,3);
	var micon_arr = generateStepArr(4,38,3);
	var icon_array = ['+++','++','+','0','---','--','-']; 

	var tbody = '';
	for(var i = 0; i < rowData.length; i++){
		tbody += '<tr>';
		for(var j = 0; j < rowData[i].length; j++){
			if(j < 2){
				if(j == 0){
					tbody += '<td><span class="lang_en">'+rowData[i][j]+'</span>';
				} else if(j == 1) {
					tbody += '<span class="hide_lang lang_bd">'+rowData[i][j]+'</span></td>';
				}	
			} else if (j > 1 && j < 38) {
				
				if (exp_arr.indexOf(j) != -1){
					tbody += '<td><span class="lang_en">'+checkNullValue(rowData[i][j])+'</span>';
				} else if (exp_bn_arr.indexOf(j) != -1){
					tbody += '<span class="hide_lang lang_bd">'+checkNullValue(rowData[i][j])+'</span>';
				} else if (micon_arr.indexOf(j) != -1 ) {
					tbody += '<span style="display:block;" class="season-icon">'+icon_array[rowData[i][j]-1]+'</span></td>';
				}
				
			} else if (j == 38) {
				var form_id = rowData[i][j];
			} else if (j == 39) {
				var instance_id = rowData[i][j];
			}
		}
		tbody += '</tr>';
	}
	generateEditLink('season_table_edit_instance',form_id,instance_id);
	return tbody;
}

function generateProblemRankTableRows(rowData) {
	var tbody = '';
	for(var i = 0; i < rowData.length; i++){
		tbody += '<tr>';
		for(var j = 0; j < rowData[i].length; j++){
			if(j < 1){
				tbody += '<td>'+rowData[i][j]+'</td>';
			} else if(j > 0 && j < 5) {
				if(j == 1) {
					tbody += '<td><span class="lang_en">'+rowData[i][j]+'</span>';
				} else if(j == 2){
					tbody += '<span class="hide_lang lang_bd">'+rowData[i][j]+'</span></td>';
				} else if(j == 3){
					var form_id = rowData[i][j];
				} else if (j == 4){
					var instance_id = rowData[i][j];
				}
			}
		}
	}
	generateEditLink('priority_table_edit_instance',form_id,instance_id);
	return tbody;
}

function generateProblemMatrixTableRows(rowData){
	var en_text_arr = generateStepArr(0,10,2);
	var bn_text_arr = generateStepArr(1,10,2);
	var tbody = '';
	for(var i = 0; i < rowData.length; i++){
		tbody += '<tr>';
		for(var j = 0; j < rowData[i].length; j++){
			if (en_text_arr.indexOf(j) != -1){
					tbody += '<td><span class="lang_en">'+checkNullValue(rowData[i][j])+'</span>';
				} else if (bn_text_arr.indexOf(j) != -1){
					tbody += '<span class="hide_lang lang_bd">'+checkNullValue(rowData[i][j])+'</span></td>';
				} else if (j == 10){
					var form_id = rowData[i][j];
				} else if (j == 11){
					var instance_id = rowData[i][j];
				}
		}
		tbody += '</tr>';
	}
	generateEditLink('solution_table_edit_instance',form_id,instance_id);
	return tbody;
}

function generateLivlihoodTableData(rowData){
console.log(rowData)
	var bn_income_type_text = ['','মধ্যম', 'কম','বেশি'];
	var en_income_type_text = ['', 'Medium', 'Low', 'High'];
	var tbody = '';
	for(var i = 0; i < rowData.length; i++){
		tbody += '<tr>';
			for(var j = 0; j < rowData[i].length; j++){
				if(j == 0 || j == 4 || j == 12 || j == 14) {
					tbody += '<td><span class="lang_en">'+checkNullValue(rowData[i][j])+'</span>';
				} else if(j == 1 || j==5 || j == 13 || j == 15) {
					tbody += '<span class="hide_lang lang_bd">'+checkNullValue(rowData[i][j])+'</span></td>';
				}
				if (j > 5 && j < 12) {
console.log(rowData[i][j])
					if (j == 6){
						tbody += '<td><span class="lang_en">'+en_income_type_text[rowData[i][j]]+'</span><span class="hide_lang lang_bd">'+bn_income_type_text[rowData[i][j]]+'</span>';
					} else if (j > 6 && j < 11) {
						tbody += ', <span class="lang_en">'+en_income_type_text[rowData[i][j]]+'</span><span class="hide_lang lang_bd">'+bn_income_type_text[rowData[i][j]]+'</span>';
					} else if (j == 11) {
console.log(rowData[i][j]);
						tbody += ', <span class="lang_en"></td>'+en_income_type_text[rowData[i][j]]+'</span><span class="hide_lang lang_bd">'+bn_income_type_text[rowData[i][j]]+'</span></td>';
					}
				}
				if(j == 2 || j == 3) {
					tbody += '<td>'+rowData[i][j]+'</td>';
				}
				if (j == 16){
					var form_id = rowData[i][j];
				}
				if(j == 17){
					var instance_id = rowData[i][j];
				}
			}
		tbody += '</tr>';
	}
	generateEditLink('livelihood_table_edit_instance',form_id,instance_id);
	return tbody;
}

function populateVillageLabels(rowData){
	$('#district_en').html(rowData[0][0]);
	$('#district_bn').html(rowData[0][1]);
	$('#upazilla_en').html(rowData[0][2]);
	$('#upazilla_bn').html(rowData[0][3]);
	$('#union_en').html(rowData[0][4]);
	$('#union_bn').html(rowData[0][5]);
	$('#village_en').html(rowData[0][6]);
	$('#village_bn').html(rowData[0][7]);
	$('#ngo_en').html(rowData[0][8]);
	$('#ngo_bn').html(rowData[0][9]);
}


function generateVillagesListTable(rowData){
	var tbody = '';
	for(var i = 0; i < rowData.length; i++){
		tbody += '<tr>';
		for(var j = 0; j < rowData[i].length; j++){
			if(j < 10) {
				if((j % 2) == 0) {
					tbody += '<td><span class="lang_en">'+rowData[i][j]+'</span>';
				} else {
					tbody += '<span class="hide_lang lang_bd">'+rowData[i][j]+'</span></td>';
				}
			} else if (j > 9 && j < 12){
				tbody += '<td>'+rowData[i][j]+'</td>';
			} else {
				tbody += '<td class="text-center"><button class="marg-btn btn red" onclick="viewSingleVillage('+rowData[i][j]+')">View</button></td>';
			}
		}
		tbody += '</tr>';
	}
	return tbody;
}

function viewSingleVillage(village_id){
	window.location.href = '/csvp/village/'+village_id;
}


function generateVillageSummaryTable(rowData){
	var tbody = '';
	for(var idx in rowData[0]){
		if(idx != 'instance_id' && idx != 'xform_id_string'){
			if(idx == 'location' || idx == 'village_main_crops' || idx == 'main_natural_disaster' || idx == 'villagers_main_occupation'){
				tbody += '<tr class="lang_en"><td><span class="lang_en">'+getLabel(idx,'English')+'</span><span class="lang_bd hide_lang">'+getLabel(idx,'Bangla')+'</span></td><td>'+getValueLabel(idx,rowData[0][idx])+'</td></tr>';
			} else if(idx == 'location_bn' || idx == 'village_main_crops_bn' || idx == 'main_natural_disaster_bn' || idx == 'villagers_main_occupation_bn'){
				tbody += '<tr class="lang_bd hide_lang"><td><span class="lang_en">'+getLabel(idx,'English')+'</span><span class="lang_bd hide_lang">'+getLabel(idx,'Bangla')+'</span></td><td>'+getValueLabel(idx,rowData[0][idx])+'</td></tr>';
			} else {
				tbody += '<tr><td><span class="lang_en">'+getLabel(idx,'English')+'</span><span class="lang_bd hide_lang">'+getLabel(idx,'Bangla')+'</span></td><td>'+getValueLabel(idx,rowData[0][idx])+'</td></tr>';
			}
		} else {
			if(idx == 'instance_id'){
				var instance_id = rowData[0][idx];
			} else if (idx == 'xform_id_string') {
				var form_id = rowData[0][idx];
			}
		}
	}
	generateEditLink('summary_table_edit_instance',form_id,instance_id);
	return tbody;
}

function getLabel(key,lang) {
	var label = '';
	summary_array.forEach(function(elem){
		if(elem['name'] == key){
			label = elem[lang]; 
		}
	});
	return label;
}

function getValueLabel(key,value){
	var modified_value = value;
	if(key == 'village'){
		modified_value = '<span class="lang_en">'+village_info_data[0].village_english+'</span><span class="lang_bd hide_lang">'+village_info_data[0].village_bangla+'</span>'
	} else if (key == 'union') {
		modified_value = '<span class="lang_en">'+village_info_data[0].union_english+'</span><span class="lang_bd hide_lang">'+village_info_data[0].union_bangla+'</span>'
	} else if (key == 'ngo'){
		modified_value = '<span class="lang_en">'+village_info_data[0].org_english+'</span><span class="lang_bd hide_lang">'+village_info_data[0].org_bangla+'</span>'
	} else if (key == 'district'){
		modified_value = '<span class="lang_en">'+village_info_data[0].district_english+'</span><span class="lang_bd hide_lang">'+village_info_data[0].district_bangla+'</span>'
	} else if (key == 'upazila') {
		modified_value = '<span class="lang_en">'+village_info_data[0].upazila_english+'</span><span class="lang_bd hide_lang">'+village_info_data[0].upazila_bangla+'</span>'
	}
    
    if(modified_value == null){
		modified_value = '';
	}
	return modified_value;
}


function generateActionPlanData(rowData) {
    var tbody = '';
    for (var i = 0; i < rowData.length; i++) {
        if (i == 0) {
            tbody += '<tr>';
            tbody += '<td rowspan="' + rowData.length + '"><span class="lang_en">' + rowData[i].work_details + '</span><span class="lang_bd hide_lang">' + rowData[i].work_details_bn + '</span></td>';
            tbody += '<td rowspan="' + rowData.length + '"><span class="lang_en">' + rowData[i].work_time + '</span><span class="lang_bd hide_lang">' + rowData[i].work_time_bn + '</span></td>';
            tbody += '<td rowspan="' + rowData.length + '"><span class="lang_en">' + rowData[i].work_reposible_person_organization + '</span><span class="lang_bd hide_lang">' + rowData[i].work_reposible_person_organization_bn + '</span></td>';
            tbody += '<td><span class="lang_en">' + rowData[i].work_process + '</span><span class="lang_bd hide_lang">' + rowData[i].work_process_bn + '</span></td>';
            tbody += '<td><span class="lang_en">' + rowData[i].action_work_volume + '</span><span class="lang_bd hide_lang">' + rowData[i].action_work_volume_bn + '</span></td>';
            tbody += '<td><span class="lang_en">' + rowData[i].resposible_person + '</span><span class="lang_bd hide_lang">' + rowData[i].resposible_person_bn + '</span></td>';
            tbody += '</tr>';

            var form_id = rowData[i].xform_id_string;
            var instance_id = rowData[i].instance_id;
        } else {
            tbody += '<tr>';
            tbody += '<td><span class="lang_en">' + rowData[i].work_process + '</span><span class="lang_bd hide_lang">' + rowData[i].work_process_bn + '</span></td>';
            tbody += '<td><span class="lang_en">' + rowData[i].action_work_volume + '</span><span class="lang_bd hide_lang">' + rowData[i].action_work_volume_bn + '</span></td>';
            tbody += '<td><span class="lang_en">' + rowData[i].resposible_person + '</span><span class="lang_bd hide_lang">' + rowData[i].resposible_person_bn + '</span></td>';
            tbody += '</tr>';

            var form_id = rowData[i].xform_id_string;
            var instance_id = rowData[i].instance_id;
        }
    }
    generateEditLink('action_table_edit_instance', form_id, instance_id);
    return tbody;
}

function generateEditLink(linkId,formId,instanceId){
	var edit_link = '/pcsv/forms/'+formId+'/instance/edit-data/'+instanceId;
	$('#'+linkId).attr("href", edit_link);
}

function filterMap(obj){
	chkbox = [];
	$("input:checkbox[class=filter-icon]:checked").each(function(){
    	chkbox.push($(this).attr("id"));
	});
	
}

