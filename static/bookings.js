$(function() {

  // test to ensure jQuery is working
  // console.log("whee!")

  // disable refresh button
  // $("#refresh-btn").prop("disabled", true)

  var addrLookup = {
    "Alexandra Road":"460 Alexandra Road",
    "Boon Lay":"Jurong Point Shopping Centre",
    "Buangkok":"Buangkok MRT",
    "Bukit Panjang":"Bukit Panjang Plaza",
    "Changi Business Park":"UE Biz Hub East",
    "Clementi":"Blk 451 Clementi Avenue 3",
    "Esplanade":"Esplanade MRT Station",
    "Harbourfront":"1 Harbourfront Place",
    "Kovan":"Heartland Mall",
    "Marina Bay":"Marina Bay Link Mall",
    "Orchard":"333 Orchard Road",
    "Pasir Ris":"Blk 625 Elias Road",
    "Paya Lebar":"Singapore Post Centre",
    "Punggol":"Block 681 Punggol Dr",
    "Raffles Place (ORQ)":"1 Raffles Quay, North Tower",
    "Raffles Place (ACB)":"11 Collyer Quay (#19-01)",
    "Raffles Place (PAC)":"11 Collyer Quay (#18-01)",
    "Serangoon":"Blk 263 Serangoon Central Dr",
    "Shenton Way":"50 Robinson Road",
    "Tanjong Pagar":"10 Anson Road",
    "Toa Payoh":"Blk 126 Lorong 1",
    "Woodlands":"Woodlands MRT",
    "Sentosa (RWS)":"26 Sentosa Gateway (#B2-01)",
    "Yishun Ring":"Blk 598 Wisteria Mall (#B1-09)",
    "SCDF HQ Med Center":"91 Ubi Ave 4 S(408827)",
    "CDA Med Center":"101 Jalan Bahar S(649734)",
    "HTA Med Center":"501 Old Choa Chu Kang Rd S(698928)"}
  
  var ladyDoc = {
    "Alexandra Road": "No",
    "Boon Lay": "Yes",
    "Buangkok": "Yes",
    "Bukit Panjang":"No",
    "Changi Business Park":"No",
    "Clementi": "No",
    "Esplanade":"Yes",
    "Harbourfront": "Yes",
    "Kovan": "No",
    "Marina Bay":"Yes",
    "Orchard":"Yes",
    "Pasir Ris":"Yes",
    "Paya Lebar": "Yes",
    "Punggol": "No",
    "Raffles (ORQ)": "No",
    "Raffles (ACB)": "Yes",
    "Raffles (PAC)": "Yes",
    "Serangoon": "No",
    "Shenton Way": "No",
    "Tanjong Pagar": "Yes",
    "Toa Payoh":"No",
    "Woodlands": "No",
    "Sentosa (RWS)":"No",
    "Yishun Ring":"No"
  }
  function getAddress(k){
    return addrLookup[k];
  }
  function hasLadyDoc(k){
    return ladyDoc[k]=="Yes"
  }

  //$("#location_select").change(function() {
  $( document ).on("change", "#location_select", function() {

    // grab value
    var location_id = $("#location_select").val();
		var dataString = $("#htmbForm").serialize();

    // send value via POST to URL /<department_id>
    var get_request = $.ajax({
      type: 'GET',
			data: dataString,
      url: '/slotsfor/' + location_id + '/'
    });

    // handle response
    get_request.done(function(data){

    // data
    // console.log(data)

    // add values to list 
    var option_list = [["", "Choose Date & Time"]].concat(data);
    $("#slot_select").empty();
      for (var i = 0; i < option_list.length; i++) {
        $("#slot_select").append(
          $("<option></option>").attr("value", option_list[i][0]).text(option_list[i][1]));
      }
      // show model list
      $("#slot_select").show();
    });
    //show address
    $('.addressText').text(getAddress(location_id));
    if (hasLadyDoc(location_id)) {
      document.getElementById("female").style.display=""
    } else {
      document.getElementById("female").style.display="None"
    }

  });
})
