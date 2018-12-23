var initCount = 0;
var totalColumns = new Array();
var data = new Array();
var columnsTypes = new Array();
var selectobj = {};
var selectedColumns = new Array();
var selectedCondition = new Array();
var availableColumn = new Array();
var conditions = {"anywhere": "anywhere", "starts_with": "starts_with", "ends_with": "ends_with", "exact": "exact"};
var rowCount = 1;
var oldColumn = '';

//get unique values form an array
Array.prototype.getUnique = function(){
   var u = {}, a = [];
   for(var i = 0, l = this.length; i < l; ++i){
      if(u.hasOwnProperty(this[i])) {
         continue;
      }
      a.push(this[i]);
      u[this[i]] = 1;
   }
   return a;
}

//initialize user/form config
function initialization(dataList,columns,types){
    totalColumns = columns;
    columnsTypes = types;
    data = dataList;
    selectedColumns = [];//load from db/cookie
    selectedCondition = [];//load from db/cookie
    rowCount = selectedColumns.length + 1;
    initCount = totalColumns.length;
    selectobj = generateSelectOptions(data,columns,columnsTypes);
    availableColumn = totalColumns.filter( function( elem ) {
        return selectedColumns.indexOf( elem ) < 0;
    });
    addFilterField();
}

//get unique vaues from column for select types
function generateSelectOptions(dList,cols,cTypes){
    var selectArray = {};
    for(var i=0; i < cTypes.length; i++) {
        if(cTypes[i] == 'select'){
            var result = dList.map(function(a) {return a[i];});
            var uniqueArray = result.getUnique();
            selectArray[cols[i]] = uniqueArray;
        }
    }
    return selectArray;
}

//Capitalize first character of a string or string parts separated by underscore or hyphen
function capitalize(string) {
    var splitStr = string.split(/[_-]+/);
    var fullStr = '';
    $.each(splitStr, function (index) {
        var currentSplit = splitStr[index].charAt(0).toUpperCase() + splitStr[index].slice(1);
        fullStr += currentSplit + " "
    });
    return fullStr;
}

//remove selected values form other dropdowns
function removeSelected(obj) {
    var id = obj.id;
    var newValue = obj.value;
    var oldValue = $('.' + id).val();
    var splitId = id.split('_');
    oldColumn = oldValue;

    $('.' + id).val(newValue);
    if (newValue != oldValue) {
        hideSelectedOnchange(newValue, id);
        availableColumn.splice($.inArray(newValue, availableColumn), 1);
        if (availableColumn.indexOf(oldValue) >= 0) {
        } else {
            availableColumn.push(oldValue);
        }
        addDeselected(oldValue, id);
    }
}

//add deselected value to other dropdowns
function addDeselected(oldValue, id) {
    $('.loop-count').each(
        function () {
            var selectCountId = ($(this).attr("id"));
            if (selectCountId != id) {
                if (availableColumn.indexOf(oldValue) >= 0) {
                    $('<option>').val(oldValue).text(capitalize(oldValue)).appendTo('#' + selectCountId);
                }
            }
        });
}

//change condition column according to on change event of main
function changeConditional(obj) {

    var id = obj.id;
    var new_value = obj.value;
    var splitId = id.split('_');
    var text_inptval = $('#search_input_value_' + splitId[1]).val();

    var con_field = getConditionHtml(new_value, splitId[1]);
    var input_field = getSearchInputHtml(new_value, splitId[1]);
    $("#cust_condition_" + splitId[1]).empty().append(con_field);
    $('#rep_cls_' + splitId[1]).empty().append(input_field);

    $("#search_input_value_"+splitId[1]).val(text_inptval);
}

//remove row
function removeRow(obj) {
    var id = obj.id;
    var removeNum = id.split("_")[(id.split("_")).length - 1]
    var row = $('#rowCount' + removeNum);
    var sel = row.find('.loop-count :selected').val();
    var name = row.find('.loop-count :selected').text();


    var index = availableColumn.indexOf(sel);
    if (index <= -1) {
        availableColumn.splice(index, 0, sel);
    }
    row.remove();
    var hiddenRow = $('.selectCount_' + removeNum);
    hiddenRow.remove();
    var newId = 1;
    $('.loop-count').each(
        function () {
            myList = [];
            var selectCountId = ($(this).attr("id"));
            if (typeof (selectCountId) !== 'undefined') {
                if (selectCountId != '') {
                    $('#' + selectCountId).children('option').each(function () {
                        myList.push($(this).val())
                    });
                }
                if (myList.indexOf(sel) == -1) {
                    $('<option>').val(sel).text(capitalize(sel)).appendTo('#' + selectCountId);
                }

                var newSelectCountIdMarge = selectCountId.split("_");
                var oldRowId = newSelectCountIdMarge[1];

                var arrayNewId = ['selectCount_', 'rowCount', 'rowcount_', 'rep_cls_', 'rowcountPlus_', 'conditions_input_', 'search_input_value_'];

                for (var i = 0; i < arrayNewId.length; i++) {
                    var finalNewId = arrayNewId[i] + newId;

                    if (i == 0) {
                        $('#' + selectCountId).attr('name', finalNewId);
                        $('#' + selectCountId).attr('id', finalNewId);
                        $('.' + selectCountId).attr('class', finalNewId);
                    } else {
                        var selectRowId = arrayNewId[i] + oldRowId;
                        $('#' + selectRowId).attr('name', finalNewId);
                        $('#' + selectRowId).attr('id', finalNewId);
                    }
                }
                newId++;
            }
        });
    rowCount--;
    var addPlus = newId - 1;
    $('#rowcountPlus_' + addPlus).show();
}

//hide selected form other dropdowns when onchange event fires
function hideSelectedOnchange(option, id) {
    $('.loop-count').each(
        function () {
            var selectCountId = ($(this).attr("id"));
            if (selectCountId != id) {
                $('#' + selectCountId).children('option[value=' + option + ']').remove();
            }
        });
}

//generate filter main field
function getColumnHtml(rowCount, options) {
    var childDropdown = '';
    var className ='';
    childDropdown += '<select name="selectCount_' + rowCount + '" id="selectCount_' + rowCount + '"   class="back-color form-control loop-count ' + className + '" onchange="removeSelected(this);changeConditional(this)">';
    childDropdown += options;
    childDropdown += '</select>';
    return childDropdown;
}

//generate conditional field
function getConditionHtml(selectField, rowCount) {
    var conField = "";
    if (typeof(selectField) == "undefined") return conField;
    conField = '<select name="conditions_input_' + rowCount + '" id="conditions_input_' + rowCount + '" class="form-control back-color">';
    var type = columnsTypes[totalColumns.indexOf(selectField)];
    if(type == 'select' || type == 'date'){
        conField += '<option value="exact">Exact</option>';
    }else{
        $.each(conditions, function (key, value) {
                conField += '<option value="' + key + '">' + capitalize(value) + '</option>';
        });
    }
    conField += '</select>';
    return conField;
}

//generate input fields
function getSearchInputHtml(selectField, rowCount){
    var inputField = '';
    var className = '';
    var type = columnsTypes[totalColumns.indexOf(selectField)];
    if(type == 'select'){
        var options = selectobj[selectField];
        inputField = '<select name="search_input_value_' + rowCount + '" id="search_input_value_' + rowCount + '" class="form-control ' + className + ' back-color selectbox ">';
            $.each(options, function (key, value) {
                inputField += '<option value="' + value + '">' + value + '</option>';
            });
        inputField += '</select>';
    } else {
        inputField = '<input name="search_input_value_' + rowCount + '"  id="search_input_value_' + rowCount + '" class="form-control valid-cls '+className+'" type="text" />';
    }
    return inputField;
}

//generate input row
function getRowHtml(dropdown, inputField, conField, rowCount) {
    $('#addedRows').append('<div id="rowCount' + rowCount + '" name="removeName" class="lmarg">');
    $('#rowCount'+rowCount).append('<div class="form-group">');
    $('#rowCount'+rowCount + ' div.form-group').append('<div class="col-sm-3" id="cust-selectpicker">');
    $('#rowCount'+rowCount + ' div.form-group div.col-sm-3').append(dropdown);

    $('#rowCount'+rowCount + ' div.form-group').append('<div class="col-sm-2 cust_pdd" id="cust_condition_' + rowCount + '">');
    $('#rowCount'+rowCount + ' div.form-group div.col-sm-2').append(conField);

    $('#rowCount'+rowCount + ' div.form-group').append('<div id ="rep_cls_' + rowCount + '" class="col-sm-4 cust_pdd">');
    $('#rowCount'+rowCount + ' div.form-group div.col-sm-4').append(inputField);

    $('#rowCount'+rowCount + ' div.form-group').append('<div class="col-sm-1 width-col">');
    $('#rowCount'+rowCount + ' div.form-group div.col-sm-1').append('<ul id="rowcount_' + rowCount + '" class ="update-row-count" onclick="removeRow(this)"><li class="btn custom_btn tooltip_s" type="button" name="add_new_row" id="add_new_row"><i class="fa fa-2x fa-remove cust_remove"></i></li></ul>');

    $('#rowCount'+rowCount + ' div.form-group').append('<div id="addmore" class="col-sm-1 width-col-add">');
    if(initCount > rowCount){
        $('#rowCount'+rowCount + ' div.form-group div#addmore').append('<ul id="rowcountPlus_' + rowCount + '" class ="update-row-count add-plus-icon" onclick="addFilterField();"><li class="btn custom_btn tooltip_s" type="button" name="add_new_row" id="add_new_row"><i class="fa fa-2x fa-plus cust_plus"></i></li></ul>');
    }else{
        $('#rowCount'+rowCount + ' div.form-group div#addmore').append('<ul id="rowcountPlus_' + rowCount + '" style="display:none;" class ="update-row-count add-plus-icon" onclick="addFilterField();"><li class="btn custom_btn tooltip_s" type="button" name="add_new_row" id="add_new_row"><i class="fa fa-2x fa-plus cust_plus"></i></li></ul>');
    }
}

//add new row
function addFilterField(){
    var totalRowCount = $('#addedRows').children('div').length;
    $('.add-plus-icon').hide();
    if (totalRowCount < initCount) {
        var dropdown = '';
        var options = '';
        var inputField = '';
        var conField = '';

        for (var i = 0; i < availableColumn.length; i++) {
            options += '<option value = "' + availableColumn[i] + '">' + capitalize(availableColumn[i]) + '</option>';
        }

        dropdown = getColumnHtml(rowCount, options);
        inputField = getSearchInputHtml(availableColumn[0], rowCount);
        conField = getConditionHtml(availableColumn[0], rowCount);
        getRowHtml(dropdown, inputField, conField, rowCount);

        if(rowCount == 1){
            $(".width-col .fa-remove").hide();
        }

        var selectedValue = $("#selectCount_" + rowCount).find("option:selected").val();
        var index = availableColumn.indexOf(selectedValue);
        dropdown = '<input class="form-control selectCount_' + rowCount + '" type="hidden"  value="' + selectedValue + '" />';
        $('#addedRows').append(dropdown);

        var option = $('.loop-count option:selected:last').val();
        var id = "selectCount_" + rowCount;
        hideSelectedOnchange(option, id);
        rowCount++;
    }
    var j = 0;
    $('.loop-count').each(
        function () {
            j++;
            var selectedValue = $(this).find("option:selected").val();
            var index = availableColumn.indexOf(selectedValue);

            if (index > -1) {
                availableColumn.splice(index, 1);
            }
        });
}