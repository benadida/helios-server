from django.shortcuts import redirect
from django.db import IntegrityError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
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
    inst_filter = request.GET.get('inst_filter')
    if inst_filter:
        users = users.filter(institution__name__icontains=inst_filter)
    uname_filter = request.GET.get('uname_filter')
    if uname_filter:
        users = users.filter(user_id__icontains=uname_filter)
    # pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(users, 10)
    try:
        users = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        users = paginator.page(1)

    return render_template(
        request,
        'account_administration/list_users',
        {'users': users},
    )


@manager_or_superadmin_required
def list_institutions(request):
    institutions = get_active_insts()
    institutions = institutions.order_by('id')
    #filtering
    inst_filter = request.GET.get('inst_filter')
    if inst_filter:
        institutions = institutions.filter(name__icontains=inst_filter)
    #count users of institution
    #if users 0, inst can be deleted
    users_count = {}
    can_be_deleted = {}
    for inst in institutions:
        users_count[inst.name] = (
            User
            .objects
            .filter(institution__name=inst.name)
            .count())
        #which insts can be deleted
        if users_count[inst.name] > 0:
            can_be_deleted[inst.name] = False
        else:
            can_be_deleted[inst.name] = True
    #pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(institutions, 10)
    try:
        institutions = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        institutions = paginator.page(1)

    context = {
        'institutions': institutions,
        'users_count': users_count,
        'can_be_deleted': can_be_deleted,
        'request': request
    }

    return render_template(
        request,
        'account_administration/list_institutions',
        context)


@manager_or_superadmin_required
def create_user(request):
    users = get_active_users() 
    edit_id = request.GET.get('edit_id')
    edit_id = sanitize_get_param(edit_id)
    try:
        instance = users.get(id=edit_id)
    except User.DoesNotExist:
        instance = None

    if request.method == 'POST':
        form = userForm(request.POST, instance=instance)
        if form.is_valid():
            data = form.cleaned_data
            if instance:
                user = form.save()
                message = _("Changes on user were successfully saved")
                messages.success(request, message)
                return redirect('/account_administration/user_management/'
                                '?user_id_filter='+str(user.id))

            else:
                user = form.save(commit=False)
                user.name = data.get('name')
                password = random_password()
                user.info = {'name': user.name or user.user_id,
                            'password': make_password(password)}
                user.institution = data['institution']
                user.management_p = False
                user.admin_p = True
                user.user_type = 'password'
                user.superadmin_p = False
                user.ecounting_account = False
                user.save()
                message = _("User %(uid)s was created with"
                            " password %(password)s.") % {'uid': user.user_id,
                                                        'password': password}
                messages.success(request, message)
                return redirect('/account_administration/user_management/'
                                '?user_id_filter='+str(user.id))
        else:
            context = {'form': form}
            return render_template(
                request,
                'account_administration/create_user',
                context)
    else:
        inst_filter = request.GET.get('id')
        inst_filter = sanitize_get_param(inst_filter)
        try:
            insts = get_active_insts()
            inst = insts.get(id=inst_filter)
        except(Institution.DoesNotExist):
            inst = None
        if inst:
            form = userForm(initial={'institution': inst.name})
        elif instance:
            form = userForm(initial={'institution': instance.institution.name} ,
                            instance=instance)
        else:
            form = userForm()
        context = {'form': form}
        return render_template(
            request,
            'account_administration/create_user',
            context)


@manager_or_superadmin_required
def create_institution(request):
    if request.method == 'POST':
        form = institutionForm(request.POST)
        if form.is_valid():
            inst = form.save()
            inst.save()
            messages.success(request, _("Institution created."))
            return redirect('/account_administration/institution_creation')
        else:
            return render_template(
                request,
                'account_administration/create_institution',
                {'form': form})
    else:
        form = institutionForm()
        context = {'form': form}
        return render_template(
            request,
            'account_administration/create_institution',
            context)


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
        return redirect('/account_administration/user_list')
    return redirect('/account_administration/user_management'
                    '?user_id_filter='+str(user.id))


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
                (_("Institution $(inst_name)s deleted") %
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
    return redirect('/account_administration/institution_list')


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
        '/account_administration/delete_user',
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

    return redirect('/account_administration/user_list')

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

