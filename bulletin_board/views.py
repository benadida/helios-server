# Create your views here.
from django.http import HttpResponse
from models import *
from helios.models import Election, Trustee, Thresholdscheme
from django.template import Context, loader
from helios_auth.security import *
from helios.crypto import algs,elgamal
from helios import utils
from helios.crypto import utils as cryptoutils
from helios.constants import *
from helios.crypto.algs import Utils
import thresholdalgs
from django.utils.encoding import smart_str
from django.core.files import File
from django.shortcuts import get_object_or_404
import mimetypes, os
from bulletin_board.view_utils import *
from helios.crypto import elgamal


ELGAMAL_PARAMS = elgamal.Cryptosystem()

# trying new ones from OlivierP
ELGAMAL_PARAMS.p = p
ELGAMAL_PARAMS.q = q

ELGAMAL_PARAMS.g = g

# object ready for serialization
ELGAMAL_PARAMS_LD_OBJECT = datatypes.LDObject.instantiate(ELGAMAL_PARAMS, datatype='legacy/EGParams')

def index(request):
    template = loader.get_template('bulletin_board/index.html')
    context = Context()
    return render_template(request,'index',{},)

def keys_home(request):
    key_list = Key.objects.order_by('id')
    template = loader.get_template('bulletin_board/home_keys.html')
    context = Context({'key_list': key_list,})
    
    return render_template(request, 'home_keys',{'key_list': key_list,} )

def public_key_form(request):
    if request.method == "POST":
        # get the public key and the hash, and add it
        key  = Key()
        key.name = request.POST['name']
        key.email = request.POST['email']
        public_key_and_proof_enc = utils.from_json(request.POST['public_key_json_enc'])
        public_key_enc = algs.EGPublicKey.fromJSONDict(public_key_and_proof_enc['public_key'])
        pok_enc = algs.DLogProof.fromJSONDict(public_key_and_proof_enc['pok'])
        
        # verify the pok
        if not public_key_enc.verify_sk_proof(pok_enc, algs.DLog_challenge_generator):
          raise Exception("bad pok for public key encrypting")
        key.public_key_encrypt = utils.to_json(public_key_enc.to_dict())
        key.pok_encrypt = utils.to_json(pok_enc.to_dict())
        key.public_key_encrypt_hash = cryptoutils.hash_b64(key.public_key_encrypt)
        
        public_key_and_proof_sign = utils.from_json(request.POST['public_key_json_sign'])
        public_key_sign = algs.EGPublicKey.fromJSONDict(public_key_and_proof_sign['public_key'])
        pok_sign = algs.DLogProof.fromJSONDict(public_key_and_proof_sign['pok'])
        
        # verify the pok
        if not public_key_sign.verify_sk_proof(pok_sign, algs.DLog_challenge_generator):
          raise Exception("bad pok for public key signing")
        key.public_key_signing = utils.to_json(public_key_sign.to_dict())
        key.pok_signing = utils.to_json(pok_sign.to_dict())
        key.public_key_signing_hash = cryptoutils.hash_b64(key.public_key_signing)
        
        key.save()
        # send a note to admin
        try:
          election.admin.send_message("pk upload, " +"%s uploaded a pk for communication." % (key.name))
        except:
          # oh well, no message sent
          pass
    
        return HttpResponseRedirect('/bulletin_board/')

    """
    A key generator with the current params, like the trustee home but without a specific election.
    """
    eg_params_json = utils.to_json(ELGAMAL_PARAMS_LD_OBJECT.toJSONDict())

    return render_template(request, "election_publickeygenerator", {'eg_params_json': eg_params_json})


def trustee_upload_pk(request, election, trustee):
  if request.method == "POST":
    # get the public key and the hash, and add it
    public_key_and_proof = utils.from_json(request.POST['public_key_json'])
    trustee.public_key = algs.EGPublicKey.fromJSONDict(public_key_and_proof['public_key'])
    trustee.pok = algs.DLogProof.fromJSONDict(public_key_and_proof['pok'])
    
    # verify the pok
    if not trustee.public_key.verify_sk_proof(trustee.pok, algs.DLog_challenge_generator):
      raise Exception("bad pok for this public key")
    
    trustee.public_key_hash = utils.hash_b64(utils.to_json(trustee.public_key.toJSONDict()))

    trustee.save()
    
    # send a note to admin
    try:
      election.admin.send_message("%s - trustee pk upload" % election.name, "trustee %s (%s) uploaded a pk." % (trustee.name, trustee.email))
    except:
      # oh well, no message sent
      pass
    
  return HttpResponseRedirect(reverse(trustee_home, args=[election.uuid, trustee.uuid]))

@login_required
def add(request):
    if request.method == 'POST': # If the form has been submitted...
        form = KeyForm(request.POST) # A form bound to the POST data
        
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            # ...
            instances = form.save(commit=False)
            public_key_encrypt=algs.EGPublicKey.from_dict(utils.from_json(instances.public_key_encrypt))
            pok_encrypt = algs.DLogProof.from_dict(utils.from_json(instances.pok_encrypt))
            public_key_signing=algs.EGPublicKey.from_dict(utils.from_json(instances.public_key_signing))
            pok_signing = algs.DLogProof.from_dict(utils.from_json(instances.pok_signing))
            
            if public_key_encrypt.verify_sk_proof(pok_encrypt,algs.DLog_challenge_generator):
                pass
            else:
                return HttpResponse('Wrong pok_encrypt')
            if public_key_signing.verify_sk_proof(pok_signing, algs.DLog_challenge_generator):
                pass
            else:
                return HttpResponse('Wrong pok_signing')
            
            
            form.save()
            return HttpResponseRedirect('/bulletin_board/communication_keys/view') # Redirect after POST
    else:
        form = KeyForm() # An unbound form
    template = loader.get_template('bulletin_board/add_key.html')
    context = Context()

    return render_template(request,'add_key',{})
    
    # create the trustee
    

    
    
    #key = Key(name=name, public_key=public_key)
    #key.save()
    #return HttpResponse('Your public_key has been stored')

def show_key_encrypt(request, key_id):
    key = Key.objects.filter(id=key_id)[0]
    return HttpResponse(key.public_key_encrypt)

def show_key_signing(request, key_id):
    key = Key.objects.filter(id=key_id)[0]
    return HttpResponse(key.public_key_signing)
def show_pok_encrypt(request, key_id):
    key = Key.objects.filter(id=key_id)[0]
    return HttpResponse(key.pok_encrypt)
def show_pok_signing(request, key_id):
    key = Key.objects.filter(id=key_id)[0]
    return HttpResponse(key.pok_signing)


    
def show_all(request, receiver_id):
    shares_list =  Signed_Encrypted_Share.objects.filter(receiver_id=receiver_id).order_by('signer_id')
    Ei_list = Ei.objects.order_by('signer_id').order_by('id')
    string = ''
    for i in range(len(shares_list)):
        share = shares_list[i]
        string= string+share.share + '\n'
    for i in range(len(Ei_list)):
        com = Ei_list[i]
        string = string + com.value+'\n'
    return HttpResponse(string)

def show_elections(request):
    election_list = Election.objects.filter(frozen_trustee_list = True)
    template = loader.get_template('bulletin_board/election_list.html')
    context = Context({'election_list': election_list,})
    return render_template(request, 'election_list', {'election_list': election_list})

def election_index(request, election_id): 
    election = Election.objects.get(id=election_id)
    trustees =  Trustee.objects.filter(election=election)
    scheme = Thresholdscheme.objects.get(election=election)
    
        
            
            
    template = loader.get_template('bulletin_board/election_index.html')
    context = Context()
    
    return render_template(request,'election_index',{'election' :election, 'scheme': scheme, 'trustees':trustees})

def election_trustees_home(request, election_id):
    election=  Election.objects.filter(id=election_id)
    trustee_list = Trustee.objects.filter(election = election).order_by('id')
    template = loader.get_template('bulletin_board/trustee_list.html')
    context = Context({'trustee_list': trustee_list,})
    return HttpResponse(template.render(context))

@login_required
def election_trustees_add(request, election_id):
    
    election =Election.objects.filter(id = election_id)[0]
    trustees = Trustee.objects.filter(election=election)

    id_list = []
    for t in trustees:
        id_list.append(t.key_id) 
    key_list = Key.objects.exclude(id__in=id_list)
    template = loader.get_template('bulletin_board/trustee_key_list.html')
    context = Context({'election': election, 'key_list': key_list,})
    return render_template(request, 'trustee_key_list', {'election': election, 'trustees': trustees, 'key_list': key_list},)
@login_required
def election_trustees_add_from_id(request, election_id, key_id):
    key = Key.objects.filter(id=key_id)[0]
    election = Election.objects.filter(id=election_id)[0]
    if election.frozen_trustee_list == False:
        trustee = Trustee(uuid = str(uuid.uuid1()), election = election, name=key.name, email=key.email, key = key)
        trustee.save()
        
        return HttpResponseRedirect("/helios/elections/"+str(election.uuid)+"/trustees/view")
    else:
        return HttpResponse('No more trustees can be added because the list is frozen')



@login_required
def election_trustees_remove(request, election_id):
    election =Election.objects.filter(id = election_id)[0]
    trustees = Trustee.objects.filter(election=election).order_by('id')
    
    template = loader.get_template('bulletin_board/trustee_key_list.html')
    context = Context({'key_list': trustees,})
    return HttpResponse(template.render(context))

@login_required
def election_trustees_remove_from_id(request, election_id, trustee_id):
    election = Election.objects.filter(id=election_id)[0]
    trustee = Trustee.objects.filter(id = trustee_id)[0]
    name = trustee.name
    if election.frozen_trustee_list == False:

        trustee.delete()
        return HttpResponse(name+' was deleted as trustee')
    else:
        return HttpResponse('No more trustees can be removed because the list is frozen')
        

def freeze_trustees_list(request,election_id):
    if request.method == 'POST': # If the form has been submitted...
        form = kForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            #instances = form.save(commit=False)
            election = Election.objects.filter(id=election_id)[0]
            trustees = Trustee.objects.filter(election = election)
            scheme = Thresholdscheme()
            scheme.election = election
            scheme.n = len(trustees)
            scheme.ground_1 = ground_1
            scheme.ground_2 = ground_2
            scheme.k =  form.cleaned_data['k']
            scheme.save()
            election.frozen_trustee_list = True
            election.save()
            if(election.has_helios_trustee()):
                helios_trustee = election.get_helios_trustee()
                key = helios_trustee.key
                sk = SecretKey.objects.filter(public_key=key)[0]
                sk_signature = sk.secret_key_signing
                add_encrypted_shares(request,election_id,sk_signature)
                
            return HttpResponseRedirect('/helios/elections/'+str(election.uuid)+'/trustees/view')

    else:
        election=Election.objects.filter(id=election_id)[0]
        trustees = Trustee.objects.filter(election=election)
        n = len(trustees)
        template = loader.get_template('bulletin_board/freeze_trustees_list.html')
        context = Context()
        return render_template(request,'freeze_trustees_list',{'election': election, 'n': n, 'n_array': range(1,len(trustees)+1)})
        
            
            
def encrypted_shares_home(request, election_id):
    election = Election.objects.filter(id=election_id)[0]
    shares_list = Signed_Encrypted_Share.objects.filter(election_id=election_id).order_by('signer_id')
    template = loader.get_template('bulletin_board/home_encrypted_shares.html')
    context = Context({'shares_list': shares_list,})
    return HttpResponse(template.render(context))
    
def show_encrypted_share(request, share_id):
    share = Signed_Encrypted_Share.objects.filter(id=share_id)[0].share
    
    return HttpResponse(share)         
    
            
def add_encrypted_shares_js(request, election_id, signer_id):
    election = Election.objects.get(id=election_id)
    trustees = Trustee.objects.filter(election = election)
    scheme = Thresholdscheme.objects.get(election = election)
    SCHEME_PARAMS_LD_OBJECT = datatypes.LDObject.instantiate(scheme, datatype = 'legacy/Thresholdscheme')
    scheme_params_json = utils.to_json(SCHEME_PARAMS_LD_OBJECT.toJSONDict())
   
   #if request.method == 'POST':
       
       
    #Create dictionary with all public_keys
    eg_params_json = utils.to_json(ELGAMAL_PARAMS_LD_OBJECT.toJSONDict())
    pk_encrypt_dict = {}
    pk_signing_dict = {}
    name_dict = {}
    id_dict = {}
    trustee_ids_dict = {}
    email_dict = {}
    pok_encrypt_dict = {}
    pok_signing_dict = {}
    pk_encrypt_hash_dict = {}
    pk_signing_hash_dict = {}
    for i in range(len(trustees)):
        key = Key.objects.get(id=trustees[i].key_id)
        id_dict[str(i)] = key.id
        corresponding_trustee = Trustee.objects.filter(key = key)[0]
        trustee_ids_dict[str(i)] = corresponding_trustee.id
        name_dict[str(i)] = key.name
        email_dict[str(i)]= key.email
        pok_encrypt_dict[str(i)] = key.pok_encrypt
        pok_signing_dict[str(i)] = key.pok_signing
        pk_encrypt_hash_dict[str(i)] = key.public_key_encrypt_hash
        pk_signing_hash_dict[str(i)] = key.public_key_signing_hash
        pk_encrypt_dict[str(i)] = key.public_key_encrypt
        pk_signing_dict[str(i)] = key.public_key_signing
        
    return render_template_threshold(request, '../create_encrypted_shares', {"election_id": election_id, "signer_id": signer_id, "election": election, "trustees": trustees, "trustee_ids_dict": trustee_ids_dict,
                                                                             "scheme_params_json": scheme_params_json , "id_dict": id_dict, "name_dict": utils.to_json(name_dict), "email_dict": utils.to_json(email_dict), 
                                                                             "pok_encrypt_dict": utils.to_json(pok_encrypt_dict), "pok_signing_dict": utils.to_json(pok_signing_dict),"pk_encrypt_hash_dict": utils.to_json(pk_encrypt_hash_dict), 
                                                                             "pk_signing_hash_dict": utils.to_json(pk_signing_hash_dict), "pk_encrypt_dict": utils.to_json(pk_encrypt_dict), "pk_signing_dict": utils.to_json(pk_signing_dict), 
                                                                             "eg_params_json": eg_params_json})
    
  

def add_encrypted_shares(request, election_id, signature = None):
    
    
    ELGAMAL_PARAMS = algs.ElGamal()
    ELGAMAL_PARAMS.p = p
    ELGAMAL_PARAMS.q = q
    ELGAMAL_PARAMS.g = g
    
    election = Election.objects.filter(id=election_id)[0]
    trustees = Trustee.objects.filter(election = election).order_by('id')
    scheme = Thresholdscheme.objects.filter(election=election)[0]
    n = scheme.n
    pk_list = []
    for i in range(len(trustees)):
        pk_list.append(trustees[i].key)
    
    if len(pk_list)!= n:
        return HttpResponse('The number of public keys for communication must equal: '+str(n))
    
    if (request.method == 'POST')or(signature): # If the form has been submitted...
        form = SignatureForm(request.POST) # A form bound to the POST data
        if (form.is_valid())or(signature): # All validation rules pass
            # Process the data in form.cleaned_data
            # ...
            if(signature == None):
                instances = form.save(commit=False)
                signature = instances.signature
            secret_key_sig = algs.EGSecretKey.from_dict(utils.from_json(signature))
            #signer_id = 1
            for j in range(len(pk_list)):
                pk = pk_list[j]
                if (pow(g,secret_key_sig.x,p)==elgamal.PublicKey.from_dict(utils.from_json(pk.public_key_signing)).y):
                    signer=pk.name
                    signer_id = pk.id
                    trustee_signer_id = trustees[j].id
                    break
            
            if not signer:
                return HttpResponse('Your signature doesnt belong to the election: '+election.name)
            
            if (len(Signed_Encrypted_Share.objects.filter(signer_id = signer_id).filter(election_id = election_id))>0):
                return render_template(request, 'shares_already_uploaded', {'signer': signer, 'election': election})
            
            s = Utils.random_mpz_lt(q)
            t = Utils.random_mpz_lt(q)
            
            shares = scheme.share_verifiably(s,t, ELGAMAL_PARAMS)
           
            
            if len(pk_list)==len(shares):
                #f=open('Encrypted_shares'+str(trustee_id)+'.txt','w')
                for i in range(len(trustees)):
                    trustee_temp = trustees[i]
                    key = trustee_temp.key
                    receiver = key.name
                    receiver_id = key.id
            
                    share= shares[i]
                    share_string = cryptoutils.to_json_js(share.to_dict())
                    if(share.point_s.x_value != trustee_temp.id):
                        return HttpResponse('Shares have wrong x_coordinate')
           
                    encry_share = share.encrypt(algs.EGPublicKey.from_dict(utils.from_json(key.public_key_encrypt)))
                    sig = share.sign(secret_key_sig,p,q,g)
                    signed_encry_share = thresholdalgs.Signed_Encrypted_Share(sig,encry_share)
                    
                    encry_share = Signed_Encrypted_Share()
                    encry_share.share = utils.to_json(signed_encry_share.to_dict())
                    pk_sign = Key.objects.filter(id=signer_id)[0]
                    if(sig.verify(share_string,algs.EGPublicKey.from_dict(utils.from_json(pk_sign.public_key_signing)),p,q,g)):
                            encry_share.signer = pk_sign.name
                            encry_share.signer_id = signer_id
                            encry_share.receiver = receiver
                            encry_share.receiver_id = receiver_id
                            encry_share.election_id = election_id
                            encry_share.trustee_receiver_id = trustees[i].id
                            encry_share.trustee_signer_id = trustee_signer_id
                            encry_share.save()
                            

                            
                    else:
                        #Dit doet hij
                        return HttpResponse('Wrong Signature')
                
                    if (len(Signed_Encrypted_Share.objects.filter(signer_id = signer_id).filter(election_id = election.id))== scheme.n):
                        signer_key = Key.objects.get(id=signer_id)
                        signer_trustee = Trustee.objects.filter(key = signer_key)[0]
                        signer_trustee.added_encrypted_shares = True
                        signer_trustee.save()
                return HttpResponseRedirect('/bulletin_board/elections/'+str(election.id)+'/')
            else:
                return HttpResponse('pk_list and shares havent the same length')
            
            return render_template()                    
                    
            
            
    else:
        form = SignatureForm() # An unbound form
    template = loader.get_template('bulletin_board/signature_form.html')
    context = Context()

    return render_template(request, 'signature_form', {'election': election})


def download_index(request, election_id):
    election= Election.objects.filter(id = election_id)
    if((len(Signed_Encrypted_Share.objects.filter(election_id=election_id))==n*n) and (len(Ei.objects.filter(election_id=election_id)) ==n*k)):
        trustee_list = Trustee.objects.filter(election=election).order_by('id')
        template = loader.get_template('bulletin_board/download_index.html')
        context = Context({'key_list': trustee_list,})
    
        return HttpResponse(template.render(context))
    
    else:
        return HttpResponse('Download not yet available.\nTry again when all shares are uploaded.')
    
def download_data(request,election_id, receiver_id):
    election = Election.objects.get(id=election_id)
    scheme = Thresholdscheme.objects.get(election=election)
    n = scheme.n
    k = scheme.k
    shares_list =  Signed_Encrypted_Share.objects.filter(election_id=election_id).filter(receiver_id=receiver_id).order_by('signer_id')
    trustees = Trustee.objects.filter(election=election)
    if (len(trustees)==scheme.n):
        pk_list_string  = []
        for i in range(len(trustees)):
            pk_list_string.append(trustees[i].key)
    else: 
        pk_list_string = None
    pk_list = []
    pk_id_list= []
    for i in range(len(pk_list_string)):
        pk_list.append(elgamal.PublicKey.from_dict(utils.from_json(pk_list_string[i].public_key_signing)))
        pk_id_list.append(pk_list_string[i].id)
    string = ''
    string= string + utils.to_json({'p': p, 'q': q, 'g': g, 'ground_1': scheme.ground_1, 'ground_2': scheme.ground_2, 'k': scheme.k, 'n': n })+ '\n'
    for i in range(len(pk_list)):
        string = string + str(pk_id_list[i])+'\n'
        string = string + utils.to_json(pk_list[i].to_dict())+'\n'
        
    for i in range(len(shares_list)):
        share = shares_list[i]
        string= string+ utils.to_json({'share': share.share,'election_id': share.election_id,'signer': share.signer, 'signer_id': share.signer_id, 'receiver': share.receiver, 'receiver_id': share.receiver_id})
        
        string = string + '\n'
    
    file = open('bulletin_board/files/data_receiver_'+str(receiver_id)+'.txt',"w")
    file.write(string)
    file.close()
    
    file = open('bulletin_board/files/data_receiver_'+str(receiver_id)+'.txt',"r")
    mimetype = mimetypes.guess_type('data_receiver_'+str(receiver_id)+'.txt')[0]
    if not mimetype: mimetype = "application/octet-stream"

    response = HttpResponse(file.read(), mimetype=mimetype)
    response["Content-Disposition"]= "attachment; filename=%s" % os.path.split('data_receiver.txt')[1]
    return response

def decrypt_shares(request,election_id, receiver_id):
    election = Election.objects.get(id = election_id)
    key_receiver = Key.objects.get(id = receiver_id)
    scheme = Thresholdscheme.objects.get(election=election)
    n = scheme.n
    k = scheme.k
    shares_list =  Signed_Encrypted_Share.objects.filter(election_id=election_id).filter(receiver_id=receiver_id).order_by('signer_id')
    trustees = Trustee.objects.filter(election=election)
    
