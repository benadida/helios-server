from django.shortcuts import redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.utils.translation import ugettext as _

from helios.view_utils import render_template
from heliosauth.models import User
from heliosauth.auth_systems.password import make_password
from zeus.models.zeus_models import Institution
from zeus.auth import manager_or_superadmin_required
from account_administration.forms import userForm, institutionForm
from generate_password import random_password


@manager_or_superadmin_required
def list_users(request):
    users = get_active_users()
    users = users.order_by('id')
    # filtering
    inst = request.GET.get('inst')
    if inst:
        users = users.filter(institution__name__icontains=inst)
    uid = request.GET.get('uid')
    if uid:
        users = users.filter(user_id__icontains=uid)
    # pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(users, 10)
    try:
        users = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        users = paginator.page(1)
    context = {
        'users': users,
        'inst': inst,
        'uid': uid,
        }
    return render_template(
        request,
        'account_administration/list_users',
        context
        )

@manager_or_superadmin_required
def list_institutions(request):
    institutions = get_active_insts()
    institutions = institutions.order_by('id')
    #filtering
    inst_name = request.GET.get('inst_filter')
    if inst_name:
        institutions = institutions.filter(name__icontains=inst_name)
    #pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(institutions, 10)
    try:
        institutions = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        institutions = paginator.page(1)
    context = {
        'inst_name': inst_name,
        'institutions': institutions,
        'request': request
    }
    return render_template(
        request,
        'account_administration/list_institutions',
        context)

@manager_or_superadmin_required
def create_user(request):
    users = get_active_users() 
    insts = get_active_insts()
    inst_id = sanitize_get_param(request.GET.get('id'))
    try:
        institution = insts.get(id=inst_id)
    except Institution.DoesNotExist:
        institution = None
    edit_id = sanitize_get_param(request.GET.get('edit_id'))
    try:
        edit_user = users.get(id=edit_id)
    except User.DoesNotExist:
        edit_user = None
    if edit_user:
        initial = {'institution': edit_user.institution.name}
    elif institution:
        initial = {'institution': institution.name}
    else:
        initial = None
    form = None

    if request.method == 'POST':
        form = userForm(request.POST, initial=initial, instance=edit_user)
        if form.is_valid():
            user, password = form.save()
            if edit_user:
                message = _("Changes on user were successfully saved")
            else:
                message = _("User %(uid)s was created with"
                            " password %(password)s.")\
                            % {'uid': user.user_id, 'password': password}
            messages.success(request, message)
            url = "%s?user_id_filter=%s" % (reverse('user_management'), \
                str(user.id))
            return redirect(url)

    if request.method == 'GET':
        form = userForm(initial=initial, instance=edit_user)

    tpl = 'account_administration/create_user',
    context = {'form': form}
    return render_template(request, tpl, context)

@manager_or_superadmin_required
def create_institution(request):
    form = None
    if request.method == 'POST':
        form = institutionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Institution created."))
            return redirect(reverse('create_institution'))
    if request.method == 'GET': 
        form = institutionForm()
    context = {'form': form}
    return render_template(
        request,
        'account_administration/create_institution',
        context
        )

@manager_or_superadmin_required
def manage_user(request):
    users = get_active_users()
    user_id_filter = request.GET.get('user_id_filter')
    user_id_filter = sanitize_get_param(user_id_filter)

    if request.zeususer._user.management_p:
        user_type = 'manager'
    else:
        user_type = 'superadmin'

    try:
        user = users.get(id=user_id_filter)
    except(User.DoesNotExist):
        user = None
        message = _("You didn't choose a user")
        messages.error(request, message)
    context = {'u_data': user, 'user_type': user_type}
    return render_template(
        request,
        'account_administration/user_manage',
        context)

@manager_or_superadmin_required
def reset_password(request):
    users = get_active_users()
    user_id_filter = request.GET.get('user_id_filter')
    user_id_filter = sanitize_get_param(user_id_filter)
    try:
        user = users.get(id=user_id_filter)
    except(User.DoesNotExist):
        user = None
    context = {"u_data": user}
    return render_template(
        request,
        'account_administration/reset_password',
        context)


@manager_or_superadmin_required
def reset_password_confirmed(request):
    users = get_active_users()
    user_id_filter = request.GET.get('user_id_filter')
    user_id_filter = sanitize_get_param(user_id_filter)
    user_logged =request.zeususer
    try:
        user = users.get(id=user_id_filter)
    except(User.DoesNotExist):
        user = None

    if user:
        ok = False
        if user_logged._user.superadmin_p:
            # superadmin can do
            ok = True
        elif user_logged._user.management_p:
            if not (user.superadmin_p or user.management_p):
                # manager can only do if target is not manager/superadmin
                ok = True

        if ok:
            new_password = random_password()
            user.info['password'] = make_password(new_password)
            user.save()
            message = _("New password for user %(uid)s is "
                        "%(new_pass)s") % {'uid': user.user_id,
                                           'new_pass': new_password}
            messages.info(request, message)
        else:
            message = _("You are not authorized to do this")
            messages.error(request, message)
    else:
        message = _("You didn't choose a user")
        messages.error(request, message)
        return redirect(reverse('list_users'))
    url = "%s?user_id_filter=%s" % (reverse('user_management'),
                                   str(user.id))
    return redirect(url)


@manager_or_superadmin_required
def delete_institution(request):
    inst_id = request.GET.get('id')
    inst_id = sanitize_get_param(inst_id) 
    insts = get_active_insts()
    try:
        inst = insts.get(id=inst_id)
    except(Institution.DoesNotExist):
        inst = None
    context = {'inst': inst}
    return render_template(
        request,
        'account_administration/delete_institution',
        context)

@manager_or_superadmin_required
def inst_deletion_confirmed(request):
    insts = get_active_insts()
    inst_id = request.GET.get('id')
    inst_id = sanitize_get_param(inst_id) 

    try:
        inst = insts.get(id=inst_id)
    except(Institution.DoesNotExist):
        inst = None
    if inst:
        if inst.user_set.count() == 0 and  inst.election_set.count() == 0:
            inst.is_disabled = True
            inst.save()
            messages.success(
                request,
                (_("Institution %(inst_name)s deleted") %
                 {'inst_name': inst.name})
                )
        else:
            messages.error(
                request,
                _("Institution %(inst_name)s can't be deleted (users > "
                  "0)") % {'inst_name': inst.name}
                )
    else:
        messages.error(request, _("No such institution"))
    return redirect(reverse('list_institutions'))


@manager_or_superadmin_required
def delete_user(request):
    users = get_active_users()
    u_id = request.GET.get('id')
    u_id = sanitize_get_param(u_id) 
    try:
        user_for_deletion = users.get(id=u_id)
    except(User.DoesNotExist):
        user_for_deletion = None
    context = {'user_for_deletion': user_for_deletion}
    return render_template(
        request,
        'account_administration/delete_user',
        context)


@manager_or_superadmin_required
def user_deletion_confirmed(request):
    users = get_active_users()
    u_id = request.GET.get('id')
    u_id = sanitize_get_param(u_id) 

    try:
        user_for_deletion = users.get(id=u_id)
    except(User.DoesNotExist):
        user_for_deletion = None
    logged_user = request.zeususer._user
    if user_for_deletion:
        if((user_for_deletion.management_p
                or user_for_deletion.superadmin_p)
                and logged_user.superadmin_p):
            user_for_deletion.is_disabled = True
            user_for_deletion.save()
            message = _("User %(ufd)s succesfuly "
                        "deleted!") % {'ufd': user_for_deletion.user_id}
            messages.success(request, message)
        elif((user_for_deletion.management_p
                or user_for_deletion.superadmin_p)
                and logged_user.management_p):
            messages.error(
                request,
                _("You are not authorized to delete that user")
                )
        else:
            user_for_deletion.is_disabled=True
            user_for_deletion.save()
            message = _("User %(ufd)s succesfuly "
                        "deleted!") % {'ufd': user_for_deletion.user_id}
            messages.success(request, message)

    else:
        messages.error(request, _("You didn't choose a user"))

    return redirect(reverse('list_users'))

def get_active_users():
    return User.objects.filter(is_disabled=False)

def get_active_insts():
    return Institution.objects.filter(is_disabled=False)

def sanitize_get_param(param):
    try:
        param = int(param)
    except(ValueError, TypeError):
        param = None
    return param

