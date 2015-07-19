function get_secret_key() {
  return ElGamal.SecretKey.fromJSONObject($.secureEvalJSON($('#sk_textarea').val()));
}


function calculate_shares() {
  $('#first_step_div').hide();
  $('#waiting_div').show();

  var secret_key_sig = get_secret_key();

  //var n = {{scheme.n}};
  //var k = {{scheme.k}};
  //var ground_1 = BigInteger.fromJSONObject({{ground_1}});
  //var ground_2 = JSON.stringify({{ground_2}});
  ELGAMAL_PARAMS = ElGamal.Params.fromJSONObject({{eg_params_json|safe}});
  var p = ELGAMAL_PARAMS.p;
  var g = ELGAMAL_PARAMS.g;
  var q = ELGAMAL_PARAMS.q;
  SCHEME_PARAMS = thresholdalgs.ThresholdScheme.fromJSONObject({{scheme_params_json|safe}});
  var n = SCHEME_PARAMS.n;
    var k = SCHEME_PARAMS.k;
  var ground_1 = SCHEME_PARAMS.ground_1;
  var ground_2 = SCHEME_PARAMS.ground_2;

  console.log('ground_1: '+ground_1);

    //var g = BigInteger.fromInt({{g}});
  //var p = BigInteger.fromInt({{p}});
  //var q = BigInteger.fromInt({{q}});

   //EEN OBJECT KAN HIER NIET MEEGEGEVEN WORDEN ENKEL VARIABELEN. PK ZELF AANMAKEN
  //var pk_signer_encrypt = {{pk_list}};
  var id_array=[];
  var name_array = [];
  var email_array = [];
  var pok_encrypt_array = [];
  var pok_signing_array = [];
  var pk_encrypt_array = [];
  var pk_signing_array = [];
  var pk_encrypt_hash_array = []
  var pk_signing_hash_array = [];

  var dict, pk, proof;
  var id_dict = {{id_dict|safe}};
  var trustee_ids_dict = {{trustee_ids_dict|safe}}
  var name_dict = JSON.parse(JSON.stringify({{name_dict|safe}}));
  var email_dict = JSON.parse(JSON.stringify({{email_dict|safe}}));
  //var pok_encrypt_dict = JSON.parse(JSON.stringify({{pok_encrypt_dict|safe}}));
  //var pok_signing_dict = JSON.parse(JSON.stringify({{pok_signing_dict|safe}}));
  var pk_encrypt_dict = JSON.parse(JSON.stringify({{pk_encrypt_dict|safe}}));
  var pk_signing_dict = JSON.parse(JSON.stringify({{pk_signing_dict|safe}}));
  var pk_encrypt_hash_dict = JSON.parse(JSON.stringify({{pk_encrypt_hash_dict|safe}}));
  var pk_signing_hash_dict = JSON.parse(JSON.stringify({{pk_signing_hash_dict|safe}}));
  var i = 0;

  var trustee_ids_array = [];

  while (String(i) in id_dict) {
  	dict = id_dict[String(i)];
  	var id_value = parseInt(dict);
  	if (id_value == parseInt({{signer_id}})) {
  		var signer_index = i;
  	}
  	id_array.push(id_value);

  	dict = trustee_ids_dict[String(i)];
  	var trustee_id_value = parseInt(dict);
  	trustee_ids_array.push(trustee_id_value);

  	dict = name_dict[String(i)];
  	name_array.push(String(dict));

  	dict = email_dict[String(i)];
  	email_array.push(String(dict));

  	//dict = pok_encrypt_dict[String(i)];
  	//proof = ElGamal.Proof.fromJSONObject(dict);
  	//pok_encrypt_array.push(proof);

  	//dict = pok_signing_dict[String(i)];
  	//proof = ElGamal.Proof.fromJSONObject(dict);
  	//pok_signing_array.push(proof);

  	dict = pk_encrypt_dict[String(i)];
  	pk = ElGamal.PublicKey.fromJSONObject(jQuery.secureEvalJSON(dict));
  	pk_encrypt_array.push(pk);

  	dict = pk_signing_dict[String(i)];
  	pk = ElGamal.PublicKey.fromJSONObject(jQuery.secureEvalJSON(dict));
  	pk_signing_array.push(pk);

  	dict = pk_encrypt_hash_dict[String(i)];
  	pk_encrypt_hash_array.push(String(dict));

  	dict = pk_signing_hash_dict[String(i)];
  	pk_signing_hash_array.push(String(dict));

  	i++;

  }

  var correct_shares = true;
  if ((g.modPow(secret_key_sig.x,p).toString())==(pk_signing_array[signer_index].y.toString())) {
  	var signer = name_array[signer_index];
  	var pk_signer = pk_signing_array[signer_index];
  	var scheme = new thresholdalgs.ThresholdScheme({{election_id}},n,k,ground_1,ground_2);
  	var s = Random.getRandomInteger(q);
  	var t = Random.getRandomInteger(q);
  	//Also give the id's from the trustees (trustee.id)
  	var shares = scheme.share_verifiably(s,t,ELGAMAL_PARAMS, trustee_ids_array);
  	if(id_array.length == shares.length){
  		var encry_shares = [];
  		for(var i =0; i< n; i++) {
  			var receiver_id = id_array[i];
  			var trustee_receiver_id = trustee_ids_array[i];
  			var receiver = name_array[i];
  			var pk_encrypt_receiver = pk_encrypt_array[i];

  			var share = shares[i];
  			var share_string = JSON.stringify(share.toJSONObject(), separators=(', ', ': '));
  			if(share.point_s.x_value != trustee_receiver_id) {
  				correct_shares = false;
  			}

  			var encry_share = share.encrypt(pk_encrypt_array[i]);
  			var sig  = share.sign(secret_key_sig,p,q,g);
  			var signed_encry_share = new thresholdalgs.SignedEncryptedShare(sig, encry_share);
  			//var signed_encry_share_dict = signed_encry_share.toJSONObject();
  			if(sig.verify(share_string,pk_signer,p,q,g)){


  				console.log('signatute: '+'r: ' +sig.r+ ' s: '+sig.s);
  				console.log(signer+ ' created correct share '+String(i));
  				encry_shares.push(signed_encry_share);

  			}
  			else {
  				console.log(signer + ' created incorrect share '+String(i));
  			}
  		}

  	}
  if(encry_shares.length == n){
  	var encry_shares_text = '';
  	var item;
  	var dict = {};
  	for(var i = 0; i<n; i++){
  		item = encry_shares[i];
  		dict[String(i)] = item.toJSONObject();
  	}
  	encry_shares_text = JSON.stringify(dict);
	$('#waiting_div').hide();
  	$('#encry_shares_div').show();
  	$('#encry_shares_textarea').val(encry_shares_text);
  }
  }
  else {
  	$('#error_div').show();
  }
}

function submit_result() {
  $('#encry_shares_div').hide();
  $('#waiting_submit_div').show();

  var result = $('#encry_shares_textarea').val();

  // do the post
  $.ajax({
      type: 'POST',
      url: "./upload",
      data: {'encry_shares': result},
      success: function(result) {
        $('#waiting_submit_div').hide();
        if (result != "FAILURE") {
          $('#done_div').show();
        } else {
          alert('verification failed, you probably used the wrong key.');
          reset();
        }
      },
      error: function(error) {
          $('#waiting_submit_div').hide();
          $('#error_div').show();
      }
  });
}

function skip_to_second_step() {
  $('#first_step_div').hide();
  $('#second_step_div').show();
  $('#encry_shares_textarea').html('');
  $('#skip_to_second_step_instructions').hide();
}

function reset() {
  $('#second_step_div').hide();
  $('#skip_to_second_step_instructions').show();
  $('#first_step_div').show();
  $('#encry_shares_textarea').html('');
  $('#first-step-success').hide();
}
