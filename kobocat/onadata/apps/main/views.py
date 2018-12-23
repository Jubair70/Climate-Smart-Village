from datetime import datetime, date

from django.contrib.contenttypes.models import ContentType
import os
import json
import sys
from bson import json_util

from django.conf import settings
from django.core import serializers
from django.core.urlresolvers import reverse
from django.core.files.storage import default_storage
from django.core.files.storage import get_storage_class
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import IntegrityError
from rest_framework.authtoken.models import Token
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect
from django.http import HttpResponseServerError
from django.shortcuts import get_object_or_404
from django.shortcuts import render, render_to_response
from django.template.loader import get_template
from django.template import loader, RequestContext, Context
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from django.db import connection
from guardian.shortcuts import assign_perm, remove_perm, get_users_with_perms

from onadata.apps.main.forms import UserProfileForm, FormLicenseForm, \
    DataLicenseForm, SupportDocForm, QuickConverterFile, QuickConverterURL, \
    QuickConverter, SourceForm, PermissionForm, MediaForm, MapboxLayerForm, \
    ActivateSMSSupportFom, ExternalExportForm
from onadata.apps.main.models import AuditLog, UserProfile, MetaData, Message_Queue
#from onadata.apps.usermodule.models import LoginHistory
from onadata.apps.logger.models import Instance, XForm
from onadata.apps.logger.views import enter_data
from onadata.apps.viewer.models.data_dictionary import DataDictionary, \
    upload_to
from onadata.apps.viewer.models.parsed_instance import \
    DATETIME_FORMAT, ParsedInstance
from onadata.apps.viewer.views import attachment_url
from onadata.apps.sms_support.tools import check_form_sms_compatibility, \
    is_sms_related
from onadata.apps.sms_support.autodoc import get_autodoc_for
from onadata.apps.sms_support.providers import providers_doc
from onadata.libs.utils.bamboo import get_new_bamboo_dataset, \
    delete_bamboo_dataset, ensure_rest_service
from onadata.libs.utils.decorators import is_owner
from onadata.libs.utils.logger_tools import response_with_mimetype_and_name, \
    publish_form
from onadata.libs.utils.user_auth import add_cors_headers
from onadata.libs.utils.user_auth import check_and_set_user_and_form
from onadata.libs.utils.user_auth import check_and_set_user
from onadata.libs.utils.user_auth import get_xform_and_perms
from onadata.libs.utils.user_auth import has_permission
from onadata.libs.utils.user_auth import has_edit_permission
from onadata.libs.utils.user_auth import helper_auth_helper
from onadata.libs.utils.user_auth import set_profile_data
from onadata.libs.utils.log import audit_log, Actions
from onadata.libs.utils.qrcode import generate_qrcode
from onadata.libs.utils.viewer_tools import enketo_url
from onadata.libs.utils.export_tools import upload_template_for_external_export
from onadata.libs.utils.model_tools import queryset_iterator
from onadata.libs.data.query import _dictfetchall, _execute_query
import paho.mqtt.client as mqtt
# this is Mongo Collection where we will store the parsed submissions
from onadata.apps.approval.models.approval import ApprovalDef
from onadata.apps.approval.forms import ApprovalForm
from django.forms.formsets import formset_factory
from onadata.apps.usermodule.forms import ProjectPermissionForm
from onadata.apps.usermodule.views_project import get_own_and_partner_orgs_usermodule_users, get_permissions
from onadata.libs.tasks import instance_parse
from collections import OrderedDict

xform_instances = settings.MONGO_DB.instances
key_whitelist = ['$or', '$and', '$exists', '$in', '$gt', '$gte',
                 '$lt', '$lte', '$regex', '$options', '$all']
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


def home(request):
    if request.user.username:
        return HttpResponseRedirect(
            reverse(profile, kwargs={'username': request.user.username}))

    return render(request, 'home.html')


@login_required
def login_redirect(request):
    return HttpResponseRedirect(reverse(profile,
                                        kwargs={'username': request.user.username}))


@require_POST
@login_required
def clone_xlsform(request, username):
    """
    Copy a public/Shared form to a users list of forms.
    Eliminates the need to download Excel File and upload again.
    """
    to_username = request.user.username
    message = {'type': None, 'text': '....'}
    message_list = []

    def set_form():
        form_owner = request.POST.get('username')
        id_string = request.POST.get('id_string')
        xform = XForm.objects.get(user__username__iexact=form_owner,
                                  id_string__exact=id_string)
        if len(id_string) > 0 and id_string[0].isdigit():
            id_string = '_' + id_string
        path = xform.xls.name
        if default_storage.exists(path):
            xls_file = upload_to(None, '%s%s.xls' % (
                id_string, XForm.CLONED_SUFFIX), to_username)
            xls_data = default_storage.open(path)
            xls_file = default_storage.save(xls_file, xls_data)
            survey = DataDictionary.objects.create(
                user=request.user,
                xls=xls_file
            ).survey
            # log to cloner's account
            audit = {}
            audit_log(
                Actions.FORM_CLONED, request.user, request.user,
                _("Cloned form '%(id_string)s'.") %
                {
                    'id_string': survey.id_string,
                }, audit, request)
            clone_form_url = reverse(
                show, kwargs={
                    'username': to_username,
                    'id_string': xform.id_string + XForm.CLONED_SUFFIX})
            return {
                'type': 'alert-success',
                'text': _(u'Successfully cloned to %(form_url)s into your '
                          u'%(profile_url)s') %
                        {'form_url': u'<a href="%(url)s">%(id_string)s</a> ' % {
                            'id_string': survey.id_string,
                            'url': clone_form_url
                        },
                         'profile_url': u'<a href="%s">profile</a>.' %
                                        reverse(profile, kwargs={'username': to_username})}
            }

    form_result = publish_form(set_form)
    if form_result['type'] == 'alert-success':
        # comment the following condition (and else)
        # when we want to enable sms check for all.
        # until then, it checks if form barely related to sms
        if is_sms_related(form_result.get('form_o')):
            form_result_sms = check_form_sms_compatibility(form_result)
            message_list = [form_result, form_result_sms]
        else:
            message = form_result
    else:
        message = form_result

    context = RequestContext(request, {
        'message': message, 'message_list': message_list})

    if request.is_ajax():
        res = loader.render_to_string(
            'message.html',
            context_instance=context
        ).replace("'", r"\'").replace('\n', '')

        return HttpResponse(
            "$('#mfeedback').html('%s').show();" % res)
    else:
        return HttpResponse(message['text'])


def profile(request, username):
    content_user = get_object_or_404(User, username__iexact=username)
    form = QuickConverter()
    data = {'form': form}

    # xlsform submission...
    if request.method == 'POST' and request.user.is_authenticated():
        def set_form():
            form = QuickConverter(request.POST, request.FILES)
            survey = form.publish(request.user).survey
            audit = {}
            audit_log(
                Actions.FORM_PUBLISHED, request.user, content_user,
                _("Published form '%(id_string)s'.") %
                {
                    'id_string': survey.id_string,
                }, audit, request)
            enketo_webform_url = reverse(
                enter_data,
                kwargs={'username': username, 'id_string': survey.id_string}
            )
            return {
                'type': 'alert-success',
                'preview_url': reverse(enketo_preview, kwargs={
                    'username': username,
                    'id_string': survey.id_string
                }),
                'text': _(u'Successfully published %(form_id)s.'
                          u' <a href="%(form_url)s">Enter Web Form</a>'
                          u' or <a href="#preview-modal" data-toggle="modal">'
                          u'Preview Web Form</a>')
                        % {'form_id': survey.id_string,
                           'form_url': enketo_webform_url},
                'form_o': survey
            }

        form_result = publish_form(set_form)
        if form_result['type'] == 'alert-success':
            # comment the following condition (and else)
            # when we want to enable sms check for all.
            # until then, it checks if form barely related to sms
            if is_sms_related(form_result.get('form_o')):
                form_result_sms = check_form_sms_compatibility(form_result)
                data['message_list'] = [form_result, form_result_sms]
            else:
                data['message'] = form_result
        else:
            data['message'] = form_result

    # profile view...
    # for the same user -> dashboard
    if content_user == request.user:
        show_dashboard = True
        all_forms = content_user.xforms.count()
        form = QuickConverterFile()
        form_url = QuickConverterURL()

        request_url = request.build_absolute_uri(
            "/%s" % request.user.username)
        url = request_url.replace('http://', 'https://')
        xforms = XForm.objects.filter(user=content_user) \
            .select_related('user', 'instances')
        user_xforms = xforms
        # forms shared with user
        xfct = ContentType.objects.get(app_label='logger', model='xform')
        xfs = content_user.userobjectpermission_set.filter(content_type=xfct)
        shared_forms_pks = list(set([xf.object_pk for xf in xfs]))
        forms_shared_with = XForm.objects.filter(
            pk__in=shared_forms_pks).exclude(user=content_user) \
            .select_related('user')
        # all forms to which the user has access
        published_or_shared = XForm.objects.filter(
            pk__in=shared_forms_pks).select_related('user')
        xforms_list = [
            {
                'id': 'published',
                'xforms': user_xforms,
                'title': _(u"Published Forms"),
                'small': _("Export, map, and view submissions.")
            },
            {
                'id': 'shared',
                'xforms': forms_shared_with,
                'title': _(u"Shared Forms"),
                'small': _("List of forms shared with you.")
            },
            {
                'id': 'published_or_shared',
                'xforms': published_or_shared,
                'title': _(u"Published Forms"),
                'small': _("Export, map, and view submissions.")
            }
        ]
        data.update({
            'all_forms': all_forms,
            'show_dashboard': show_dashboard,
            'form': form,
            'form_url': form_url,
            'url': url,
            'user_xforms': user_xforms,
            'xforms_list': xforms_list,
            'forms_shared_with': forms_shared_with
        })
    # for any other user -> profile
    set_profile_data(data, content_user)

    return render(request, "profile.html", data)


def members_list(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden(_(u'Forbidden.'))
    users = User.objects.all()
    template = 'people.html'

    return render(request, template, {'template': template, 'users': users})


@login_required
def profile_settings(request, username):
    content_user = check_and_set_user(request, username)
    profile, created = UserProfile.objects.get_or_create(user=content_user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            # get user
            # user.email = cleaned_email
            form.instance.user.email = form.cleaned_data['email']
            form.instance.user.save()
            form.save()
            # todo: add string rep. of settings to see what changed
            audit = {}
            audit_log(
                Actions.PROFILE_SETTINGS_UPDATED, request.user, content_user,
                _("Profile settings updated."), audit, request)
            return HttpResponseRedirect(reverse(
                public_profile, kwargs={'username': request.user.username}
            ))
    else:
        form = UserProfileForm(
            instance=profile, initial={"email": content_user.email})

    return render(request, "settings.html",
                  {'content_user': content_user, 'form': form})


@require_GET
def public_profile(request, username):
    content_user = check_and_set_user(request, username)
    if isinstance(content_user, HttpResponseRedirect):
        return content_user
    data = {}
    set_profile_data(data, content_user)
    data['is_owner'] = request.user == content_user
    audit = {}
    audit_log(
        Actions.PUBLIC_PROFILE_ACCESSED, request.user, content_user,
        _("Public profile accessed."), audit, request)

    return render(request, "profile.html", data)


@login_required
def dashboard(request):
    content_user = request.user
    data = {
        'form': QuickConverter(),
        'content_user': content_user,
        'url': request.build_absolute_uri("/%s" % request.user.username)
    }
    set_profile_data(data, content_user)

    return render(request, "dashboard.html", data)


def redirect_to_public_link(request, uuid):
    xform = get_object_or_404(XForm, uuid=uuid)
    request.session['public_link'] = \
        xform.uuid if MetaData.public_link(xform) else False

    return HttpResponseRedirect(reverse(show, kwargs={
        'username': xform.user.username,
        'id_string': xform.id_string
    }))


def set_xform_owner_data(data, xform, request, username, id_string):
    data['sms_support_form'] = ActivateSMSSupportFom(
        initial={'enable_sms_support': xform.allows_sms,
                 'sms_id_string': xform.sms_id_string})
    if not xform.allows_sms:
        data['sms_compatible'] = check_form_sms_compatibility(
            None, json_survey=json.loads(xform.json))
    else:
        url_root = request.build_absolute_uri('/')[:-1]
        data['sms_providers_doc'] = providers_doc(
            url_root=url_root,
            username=username,
            id_string=id_string)
        data['url_root'] = url_root

    data['form_license_form'] = FormLicenseForm(
        initial={'value': data['form_license']})
    data['data_license_form'] = DataLicenseForm(
        initial={'value': data['data_license']})
    data['doc_form'] = SupportDocForm()
    data['source_form'] = SourceForm()
    data['media_form'] = MediaForm()
    data['mapbox_layer_form'] = MapboxLayerForm()
    data['external_export_form'] = ExternalExportForm()
    approval_list = ApprovalDef.objects.filter(formid=id_string).order_by('-id')
    data['approve_form'] = ApprovalForm(username)
    data['approval_list'] = approval_list
    users_with_perms = []

    for perm in get_users_with_perms(xform, attach_perms=True).items():
        has_perm = []
        if 'change_xform' in perm[1]:
            has_perm.append(_(u"Can Edit"))
        if 'view_xform' in perm[1]:
            has_perm.append(_(u"Can View"))
        if 'report_xform' in perm[1]:
            has_perm.append(_(u"Can submit to"))
        users_with_perms.append((perm[0], u" | ".join(has_perm)))
    data['users_with_perms'] = users_with_perms
    data['permission_form'] = PermissionForm(username)


def show_project_settings(request, username, id_string):
    xform, is_owner, can_edit, can_view = get_xform_and_perms(
        username, id_string, request)
    # no access
    if not (xform.shared or can_view or request.session.get('public_link')):
        return HttpResponseRedirect(reverse(home))

    data = {}
    data.update({
        'cloned': len(
            XForm.objects.filter(user__username__iexact=request.user.username,
                                 id_string__exact=id_string + XForm.CLONED_SUFFIX)
        ) > 0,
        'public_link': MetaData.public_link(xform),
        'is_owner': is_owner,
        'can_edit': can_edit,
        'can_view': can_view or request.session.get('public_link'),
        'xform': xform,
        'content_user': xform.user,
        'base_url': "https://%s" % request.get_host(),
        'source': MetaData.source(xform),
        'form_license': MetaData.form_license(xform).data_value,
        'data_license': MetaData.data_license(xform).data_value,
        'supporting_docs': MetaData.supporting_docs(xform),
        'media_upload': MetaData.media_upload(xform),
        'mapbox_layer': MetaData.mapbox_layer_upload(xform),
        'external_export': MetaData.external_export(xform),
    })

    if is_owner:
        set_xform_owner_data(data, xform, request, username, id_string)

    if xform.allows_sms:
        data.update({
            'sms_support_doc': get_autodoc_for(xform),
        })

    """
    Adjusts the view, edit and submit 
    permission of a project/form to the
    usermodule users of currently logged in
    user's organization and its partner 
    organization.
    N.B. When edit permission is assigned
    view permission is also assigned.
    """

    user_list = get_own_and_partner_orgs_usermodule_users(request)

    initial_list = get_permissions(user_list, xform)
    PermisssionFormSet = formset_factory(ProjectPermissionForm, max_num=len(user_list))
    permisssion_form_set = PermisssionFormSet(initial=initial_list)
    data.update({
        'form_id_string':id_string,
        'permisssion_form_set': permisssion_form_set,
    })
    # print 'data##################'
    # print str(data)
    if request.method == 'POST':
        permisssion_form_set = PermisssionFormSet(data=request.POST)
        for idx, user_role_form in enumerate(permisssion_form_set):
            u_id = request.POST['form-' + str(idx) + '-user']
            mist = initial_list[idx]['perm_type']
            current_user = User.objects.get(pk=u_id)
            results = map(str, request.POST.getlist('perm-' + str(idx + 1)))
            for result in results:
                if result == 'view' and not current_user.has_perm('view_xform', xform):
                    assign_perm('view_xform', current_user, xform)
                elif result == 'report' and not current_user.has_perm('report_xform', xform):
                    assign_perm('report_xform', current_user, xform)
                elif result == 'edit' and not current_user.has_perm('change_xform', xform):
                    assign_perm('change_xform', current_user, xform)
                    if not current_user.has_perm('view_xform', xform):
                        assign_perm('view_xform', current_user, xform)

            deleter = list(set(['edit', 'view', 'report']) - set(results))
            for delete_item in deleter:
                if delete_item == 'view' and current_user.has_perm('view_xform', xform) and not current_user.has_perm(
                        'change_xform', xform):
                    remove_perm('view_xform', current_user, xform)
                elif delete_item == 'report' and current_user.has_perm('report_xform', xform):
                    remove_perm('report_xform', current_user, xform)
                elif delete_item == 'edit' and current_user.has_perm('change_xform', xform):
                    remove_perm('change_xform', current_user, xform)
            message = "Permissions Saved"
            initial_list = get_permissions(user_list, xform)
            permisssion_form_set = PermisssionFormSet(initial=initial_list)
            data.update({
                'form_id_string':id_string,
                'message': message,
                'permisssion_form_set': permisssion_form_set,
            })

    return render(request, "project_settings.html", data)


@require_GET
def show(request, username=None, id_string=None, uuid=None):
    if uuid:
        return redirect_to_public_link(request, uuid)

    xform, is_owner, can_edit, can_view = get_xform_and_perms(
        username, id_string, request)
    # no access
    if not (xform.shared or can_view or request.session.get('public_link')):
        return HttpResponseRedirect(reverse(home))

    data = {}
    data['cloned'] = len(
        XForm.objects.filter(user__username__iexact=request.user.username,
                             id_string__exact=id_string + XForm.CLONED_SUFFIX)
    ) > 0
    data['public_link'] = MetaData.public_link(xform)
    data['is_owner'] = is_owner
    data['can_edit'] = can_edit
    data['can_view'] = can_view or request.session.get('public_link')
    data['xform'] = xform
    data['content_user'] = xform.user
    data['base_url'] = "https://%s" % request.get_host()
    data['source'] = MetaData.source(xform)
    data['form_license'] = MetaData.form_license(xform).data_value
    data['data_license'] = MetaData.data_license(xform).data_value
    data['supporting_docs'] = MetaData.supporting_docs(xform)
    data['media_upload'] = MetaData.media_upload(xform)
    data['mapbox_layer'] = MetaData.mapbox_layer_upload(xform)
    data['external_export'] = MetaData.external_export(xform)

    if is_owner:
        set_xform_owner_data(data, xform, request, username, id_string)

    if xform.allows_sms:
        data['sms_support_doc'] = get_autodoc_for(xform)

    return render(request, "show.html", data)


@require_GET
def api_token(request, username=None):
    user = get_object_or_404(User, username=username)
    data = {}
    data['token_key'], created = Token.objects.get_or_create(user=user)

    return render(request, "api_token.html", data)


@require_http_methods(["GET", "OPTIONS"])
def api(request, username=None, id_string=None):
    """
    Returns all results as JSON.  If a parameter string is passed,
    it takes the 'query' parameter, converts this string to a dictionary, an
    that is then used as a MongoDB query string.

    NOTE: only a specific set of operators are allow, currently $or and $and.
    Please send a request if you'd like another operator to be enabled.

    NOTE: Your query must be valid JSON, double check it here,
    http://json.parser.online.fr/

    E.g. api?query='{"last_name": "Smith"}'
    """
    if request.method == "OPTIONS":
        response = HttpResponse()
        add_cors_headers(response)

        return response
    helper_auth_helper(request)
    helper_auth_helper(request)
    xform, owner = check_and_set_user_and_form(username, id_string, request)

    if not xform:
        return HttpResponseForbidden(_(u'Not shared.'))

    try:
        args = {
            'username': username,
            'id_string': id_string,
            'query': request.GET.get('query'),
            'fields': request.GET.get('fields'),
            'sort': request.GET.get('sort')
        }
        if 'start' in request.GET:
            args["start"] = int(request.GET.get('start'))
        if 'limit' in request.GET:
            args["limit"] = int(request.GET.get('limit'))
        if 'count' in request.GET:
            args["count"] = True if int(request.GET.get('count')) > 0 \
                else False
        cursor = ParsedInstance.query_mongo(**args)
    except ValueError as e:
        return HttpResponseBadRequest(e.__str__())

    records = list(record for record in cursor)
    response_text = json_util.dumps(records)

    if 'callback' in request.GET and request.GET.get('callback') != '':
        callback = request.GET.get('callback')
        response_text = ("%s(%s)" % (callback, response_text))

    response = HttpResponse(response_text, content_type='application/json')
    add_cors_headers(response)

    return response


@require_GET
def public_api(request, username, id_string):
    """
    Returns public information about the form as JSON
    """

    xform = get_object_or_404(XForm,
                              user__username__iexact=username,
                              id_string__exact=id_string)

    _DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    exports = {'username': xform.user.username,
               'id_string': xform.id_string,
               'bamboo_dataset': xform.bamboo_dataset,
               'shared': xform.shared,
               'shared_data': xform.shared_data,
               'downloadable': xform.downloadable,
               'title': xform.title,
               'date_created': xform.date_created.strftime(_DATETIME_FORMAT),
               'date_modified': xform.date_modified.strftime(_DATETIME_FORMAT),
               'uuid': xform.uuid,
               }
    response_text = json.dumps(exports)

    return HttpResponse(response_text, content_type='application/json')


@login_required
def edit(request, username, id_string):
    xform = XForm.objects.get(user__username__iexact=username,
                              id_string__exact=id_string)
    owner = xform.user

    if username == request.user.username or \
            request.user.has_perm('logger.change_xform', xform):
        if request.POST.get('description'):
            audit = {
                'xform': xform.id_string
            }
            audit_log(
                Actions.FORM_UPDATED, request.user, owner,
                _("Description for '%(id_string)s' updated from "
                  "'%(old_description)s' to '%(new_description)s'.") %
                {
                    'id_string': xform.id_string,
                    'old_description': xform.description,
                    'new_description': request.POST['description']
                }, audit, request)
            xform.description = request.POST['description']
        elif request.POST.get('title'):
            audit = {
                'xform': xform.id_string
            }
            audit_log(
                Actions.FORM_UPDATED, request.user, owner,
                _("Title for '%(id_string)s' updated from "
                  "'%(old_title)s' to '%(new_title)s'.") %
                {
                    'id_string': xform.id_string,
                    'old_title': xform.title,
                    'new_title': request.POST.get('title')
                }, audit, request)
            xform.title = request.POST['title']
        elif request.POST.get('toggle_shared'):
            if request.POST['toggle_shared'] == 'data':
                audit = {
                    'xform': xform.id_string
                }
                audit_log(
                    Actions.FORM_UPDATED, request.user, owner,
                    _("Data sharing updated for '%(id_string)s' from "
                      "'%(old_shared)s' to '%(new_shared)s'.") %
                    {
                        'id_string': xform.id_string,
                        'old_shared': _("shared")
                        if xform.shared_data else _("not shared"),
                        'new_shared': _("shared")
                        if not xform.shared_data else _("not shared")
                    }, audit, request)
                xform.shared_data = not xform.shared_data
            elif request.POST['toggle_shared'] == 'form':
                audit = {
                    'xform': xform.id_string
                }
                audit_log(
                    Actions.FORM_UPDATED, request.user, owner,
                    _("Form sharing for '%(id_string)s' updated "
                      "from '%(old_shared)s' to '%(new_shared)s'.") %
                    {
                        'id_string': xform.id_string,
                        'old_shared': _("shared")
                        if xform.shared else _("not shared"),
                        'new_shared': _("shared")
                        if not xform.shared else _("not shared")
                    }, audit, request)
                xform.shared = not xform.shared
            elif request.POST['toggle_shared'] == 'dbexp':
                print ('enter db export%%%%%%%%%%%%%%%%%%%', xform.db_export)
                xform.db_export = not xform.db_export
            elif request.POST['toggle_shared'] == 'active':
                audit = {
                    'xform': xform.id_string
                }
                audit_log(
                    Actions.FORM_UPDATED, request.user, owner,
                    _("Active status for '%(id_string)s' updated from "
                      "'%(old_shared)s' to '%(new_shared)s'.") %
                    {
                        'id_string': xform.id_string,
                        'old_shared': _("shared")
                        if xform.downloadable else _("not shared"),
                        'new_shared': _("shared")
                        if not xform.downloadable else _("not shared")
                    }, audit, request)
                xform.downloadable = not xform.downloadable
        elif request.POST.get('form-license'):
            audit = {
                'xform': xform.id_string
            }
            audit_log(
                Actions.FORM_UPDATED, request.user, owner,
                _("Form License for '%(id_string)s' updated to "
                  "'%(form_license)s'.") %
                {
                    'id_string': xform.id_string,
                    'form_license': request.POST['form-license'],
                }, audit, request)
            MetaData.form_license(xform, request.POST['form-license'])
        elif request.POST.get('data-license'):
            audit = {
                'xform': xform.id_string
            }
            audit_log(
                Actions.FORM_UPDATED, request.user, owner,
                _("Data license for '%(id_string)s' updated to "
                  "'%(data_license)s'.") %
                {
                    'id_string': xform.id_string,
                    'data_license': request.POST['data-license'],
                }, audit, request)
            MetaData.data_license(xform, request.POST['data-license'])
        elif request.POST.get('source') or request.FILES.get('source'):
            audit = {
                'xform': xform.id_string
            }
            audit_log(
                Actions.FORM_UPDATED, request.user, owner,
                _("Source for '%(id_string)s' updated to '%(source)s'.") %
                {
                    'id_string': xform.id_string,
                    'source': request.POST.get('source'),
                }, audit, request)
            MetaData.source(xform, request.POST.get('source'),
                            request.FILES.get('source'))
        elif request.POST.get('enable_sms_support_trigger') is not None:
            sms_support_form = ActivateSMSSupportFom(request.POST)
            if sms_support_form.is_valid():
                audit = {
                    'xform': xform.id_string
                }
                enabled = \
                    sms_support_form.cleaned_data.get('enable_sms_support')
                if enabled:
                    audit_action = Actions.SMS_SUPPORT_ACTIVATED
                    audit_message = _(u"SMS Support Activated on")
                else:
                    audit_action = Actions.SMS_SUPPORT_DEACTIVATED
                    audit_message = _(u"SMS Support Deactivated on")
                audit_log(
                    audit_action, request.user, owner,
                    audit_message
                    % {'id_string': xform.id_string}, audit, request)
                # stored previous states to be able to rollback form status
                # in case we can't save.
                pe = xform.allows_sms
                pid = xform.sms_id_string
                xform.allows_sms = enabled
                xform.sms_id_string = \
                    sms_support_form.cleaned_data.get('sms_id_string')
                compat = check_form_sms_compatibility(None,
                                                      json.loads(xform.json))
                if compat['type'] == 'alert-error':
                    xform.allows_sms = False
                    xform.sms_id_string = pid
                try:
                    xform.save()
                except IntegrityError:
                    # unfortunately, there's no feedback mechanism here
                    xform.allows_sms = pe
                    xform.sms_id_string = pid

        elif request.POST.get('media_url'):
            uri = request.POST.get('media_url')
            MetaData.media_add_uri(xform, uri)
        elif request.FILES.get('media'):
            audit = {
                'xform': xform.id_string
            }
            audit_log(
                Actions.FORM_UPDATED, request.user, owner,
                _("Media added to '%(id_string)s'.") %
                {
                    'id_string': xform.id_string
                }, audit, request)
            for aFile in request.FILES.getlist("media"):
                MetaData.media_upload(xform, aFile)
        elif request.POST.get('map_name'):
            mapbox_layer = MapboxLayerForm(request.POST)
            if mapbox_layer.is_valid():
                audit = {
                    'xform': xform.id_string
                }
                audit_log(
                    Actions.FORM_UPDATED, request.user, owner,
                    _("Map layer added to '%(id_string)s'.") %
                    {
                        'id_string': xform.id_string
                    }, audit, request)
                MetaData.mapbox_layer_upload(xform, mapbox_layer.cleaned_data)
        elif request.FILES.get('doc'):
            audit = {
                'xform': xform.id_string
            }
            audit_log(
                Actions.FORM_UPDATED, request.user, owner,
                _("Supporting document added to '%(id_string)s'.") %
                {
                    'id_string': xform.id_string
                }, audit, request)
            MetaData.supporting_docs(xform, request.FILES.get('doc'))
        elif request.POST.get("template_token") \
                and request.POST.get("template_token"):
            template_name = request.POST.get("template_name")
            template_token = request.POST.get("template_token")
            audit = {
                'xform': xform.id_string
            }
            audit_log(
                Actions.FORM_UPDATED, request.user, owner,
                _("External export added to '%(id_string)s'.") %
                {
                    'id_string': xform.id_string
                }, audit, request)
            merged = template_name + '|' + template_token
            MetaData.external_export(xform, merged)
        elif request.POST.get("external_url") \
                and request.FILES.get("xls_template"):
            template_upload_name = request.POST.get("template_upload_name")
            external_url = request.POST.get("external_url")
            xls_template = request.FILES.get("xls_template")

            result = upload_template_for_external_export(external_url,
                                                         xls_template)
            status_code = result.split('|')[0]
            token = result.split('|')[1]
            if status_code == '201':
                data_value = \
                    template_upload_name + '|' + external_url + '/xls/' + token
                MetaData.external_export(xform, data_value=data_value)

        xform.update()

        if request.is_ajax():
            return HttpResponse(_(u'Updated succeeded.'))
        else:
            return HttpResponseRedirect(reverse(show, kwargs={
                'username': username,
                'id_string': id_string
            }))

    return HttpResponseForbidden(_(u'Update failed.'))


def getting_started(request):
    template = 'getting_started.html'

    return render(request, 'base.html', {'template': template})


def support(request):
    template = 'support.html'

    return render(request, 'base.html', {'template': template})


def faq(request):
    template = 'faq.html'

    return render(request, 'base.html', {'template': template})


def xls2xform(request):
    template = 'xls2xform.html'

    return render(request, 'base.html', {'template': template})


def tutorial(request):
    template = 'tutorial.html'
    username = request.user.username if request.user.username else \
        'your-user-name'
    url = request.build_absolute_uri("/%s" % username)

    return render(request, 'base.html', {'template': template, 'url': url})


def resources(request):
    if 'fr' in request.LANGUAGE_CODE.lower():
        deck_id = 'a351f6b0a3730130c98b12e3c5740641'
    else:
        deck_id = '1a33a070416b01307b8022000a1de118'

    return render(request, 'resources.html', {'deck_id': deck_id})


def about_us(request):
    a_flatpage = '/about-us/'
    username = request.user.username if request.user.username else \
        'your-user-name'
    url = request.build_absolute_uri("/%s" % username)

    return render(request, 'base.html', {'a_flatpage': a_flatpage, 'url': url})


def privacy(request):
    template = 'privacy.html'

    return render(request, 'base.html', {'template': template})


def tos(request):
    template = 'tos.html'

    return render(request, 'base.html', {'template': template})


def syntax(request):
    template = 'syntax.html'

    return render(request, 'base.html', {'template': template})


def form_gallery(request):
    """
    Return a list of urls for all the shared xls files. This could be
    made a lot prettier.
    """
    data = {}
    if request.user.is_authenticated():
        data['loggedin_user'] = request.user
    data['shared_forms'] = XForm.objects.filter(shared=True)
    # build list of shared forms with cloned suffix
    id_strings_with_cloned_suffix = [
        x.id_string + XForm.CLONED_SUFFIX for x in data['shared_forms']
        ]
    # build list of id_strings for forms this user has cloned
    data['cloned'] = [
        x.id_string.split(XForm.CLONED_SUFFIX)[0]
        for x in XForm.objects.filter(
            user__username__iexact=request.user.username,
            id_string__in=id_strings_with_cloned_suffix
        )
        ]

    return render(request, 'form_gallery.html', data)


def download_metadata(request, username, id_string, data_id):
    xform = get_object_or_404(XForm,
                              user__username__iexact=username,
                              id_string__exact=id_string)
    owner = xform.user
    if username == request.user.username or xform.shared:
        data = get_object_or_404(MetaData, pk=data_id)
        file_path = data.data_file.name
        filename, extension = os.path.splitext(file_path.split('/')[-1])
        extension = extension.strip('.')
        dfs = get_storage_class()()
        if dfs.exists(file_path):
            audit = {
                'xform': xform.id_string
            }
            audit_log(
                Actions.FORM_UPDATED, request.user, owner,
                _("Document '%(filename)s' for '%(id_string)s' downloaded.") %
                {
                    'id_string': xform.id_string,
                    'filename': "%s.%s" % (filename, extension)
                }, audit, request)
            response = response_with_mimetype_and_name(
                data.data_file_type,
                filename, extension=extension, show_date=False,
                file_path=file_path)
            return response
        else:
            return HttpResponseNotFound()

    return HttpResponseForbidden(_(u'Permission denied.'))


@login_required()
def delete_metadata(request, username, id_string, data_id):
    xform = get_object_or_404(XForm,
                              user__username__iexact=username,
                              id_string__exact=id_string)
    owner = xform.user
    data = get_object_or_404(MetaData, pk=data_id)
    dfs = get_storage_class()()
    req_username = request.user.username
    if request.GET.get('del', False) and username == req_username:
        try:
            dfs.delete(data.data_file.name)
            data.delete()
            audit = {
                'xform': xform.id_string
            }
            audit_log(
                Actions.FORM_UPDATED, request.user, owner,
                _("Document '%(filename)s' deleted from '%(id_string)s'.") %
                {
                    'id_string': xform.id_string,
                    'filename': os.path.basename(data.data_file.name)
                }, audit, request)
            return HttpResponseRedirect(reverse(show, kwargs={
                'username': username,
                'id_string': id_string
            }))
        except Exception:
            return HttpResponseServerError()
    elif (request.GET.get('map_name_del', False) or
              request.GET.get('external_del', False)) and username == req_username:
        data.delete()
        audit = {
            'xform': xform.id_string
        }
        audit_log(
            Actions.FORM_UPDATED, request.user, owner,
            _("Map layer deleted from '%(id_string)s'.") %
            {
                'id_string': xform.id_string,
            }, audit, request)
        return HttpResponseRedirect(reverse(show, kwargs={
            'username': username,
            'id_string': id_string
        }))

    return HttpResponseForbidden(_(u'Permission denied.'))


def download_media_data(request, username, id_string, data_id):
    xform = get_object_or_404(
        XForm, user__username__iexact=username,
        id_string__exact=id_string)
    owner = xform.user
    data = get_object_or_404(MetaData, id=data_id)
    dfs = get_storage_class()()
    if request.GET.get('del', False):
        if username == request.user.username:
            try:
                # ensure filename is not an empty string
                if data.data_file.name != '':
                    dfs.delete(data.data_file.name)

                data.delete()
                audit = {
                    'xform': xform.id_string
                }
                audit_log(
                    Actions.FORM_UPDATED, request.user, owner,
                    _("Media download '%(filename)s' deleted from "
                      "'%(id_string)s'.") %
                    {
                        'id_string': xform.id_string,
                        'filename': os.path.basename(data.data_file.name)
                    }, audit, request)
                return HttpResponseRedirect(reverse(show, kwargs={
                    'username': username,
                    'id_string': id_string
                }))
            except Exception as e:
                return HttpResponseServerError(e)
    else:
        if username:  # == request.user.username or xform.shared:
            if data.data_file.name == '' and data.data_value is not None:
                return HttpResponseRedirect(data.data_value)

            file_path = data.data_file.name
            filename, extension = os.path.splitext(file_path.split('/')[-1])
            extension = extension.strip('.')
            if dfs.exists(file_path):
                audit = {
                    'xform': xform.id_string
                }
                audit_log(
                    Actions.FORM_UPDATED, request.user, owner,
                    _("Media '%(filename)s' downloaded from "
                      "'%(id_string)s'.") %
                    {
                        'id_string': xform.id_string,
                        'filename': os.path.basename(file_path)
                    }, audit, request)
                response = response_with_mimetype_and_name(
                    data.data_file_type,
                    filename, extension=extension, show_date=False,
                    file_path=file_path)
                return response
            else:
                return HttpResponseNotFound()

    return HttpResponseForbidden(_(u'Permission denied.'))


def form_photos(request, username, id_string):
    xform, owner = check_and_set_user_and_form(username, id_string, request)

    if not xform:
        return HttpResponseForbidden(_(u'Not shared.'))

    data = {}
    data['form_view'] = True
    data['content_user'] = owner
    data['xform'] = xform
    image_urls = []

    for instance in xform.instances.all():
        for attachment in instance.attachments.all():
            # skip if not image e.g video or file
            if not attachment.mimetype.startswith('image'):
                continue

            data = {}

            for i in ['small', 'medium', 'large', 'original']:
                url = reverse(attachment_url, kwargs={'size': i})
                url = '%s?media_file=%s' % (url, attachment.media_file.name)
                data[i] = url

            image_urls.append(data)

    data['images'] = image_urls
    data['profilei'], created = UserProfile.objects.get_or_create(user=owner)

    return render(request, 'form_photos.html', data)


@require_POST
def set_perm(request, username, id_string):
    xform = get_object_or_404(XForm,
                              user__username__iexact=username,
                              id_string__exact=id_string)
    owner = xform.user
    if username != request.user.username \
            and not has_permission(xform, username, request):
        return HttpResponseForbidden(_(u'Permission denied.'))

    try:
        perm_type = request.POST['perm_type']
        for_user = request.POST['for_user']
    except KeyError:
        return HttpResponseBadRequest()

    if perm_type in ['edit', 'view', 'report', 'remove']:
        try:
            user = User.objects.get(username=for_user)
        except User.DoesNotExist:
            messages.add_message(
                request, messages.INFO,
                _(u"Wrong username <b>%s</b>." % for_user),
                extra_tags='alert-error')
        else:
            if perm_type == 'edit' and \
                    not user.has_perm('change_xform', xform):
                audit = {
                    'xform': xform.id_string
                }
                audit_log(
                    Actions.FORM_PERMISSIONS_UPDATED, request.user, owner,
                    _("Edit permissions on '%(id_string)s' assigned to "
                      "'%(for_user)s'.") %
                    {
                        'id_string': xform.id_string,
                        'for_user': for_user
                    }, audit, request)
                assign_perm('change_xform', user, xform)
            elif perm_type == 'view' and \
                    not user.has_perm('view_xform', xform):
                audit = {
                    'xform': xform.id_string
                }
                audit_log(
                    Actions.FORM_PERMISSIONS_UPDATED, request.user, owner,
                    _("View permissions on '%(id_string)s' "
                      "assigned to '%(for_user)s'.") %
                    {
                        'id_string': xform.id_string,
                        'for_user': for_user
                    }, audit, request)
                assign_perm('view_xform', user, xform)
            elif perm_type == 'report' and \
                    not user.has_perm('report_xform', xform):
                audit = {
                    'xform': xform.id_string
                }
                audit_log(
                    Actions.FORM_PERMISSIONS_UPDATED, request.user, owner,
                    _("Report permissions on '%(id_string)s' "
                      "assigned to '%(for_user)s'.") %
                    {
                        'id_string': xform.id_string,
                        'for_user': for_user
                    }, audit, request)
                assign_perm('report_xform', user, xform)
            elif perm_type == 'remove':
                audit = {
                    'xform': xform.id_string
                }
                audit_log(
                    Actions.FORM_PERMISSIONS_UPDATED, request.user, owner,
                    _("All permissions on '%(id_string)s' "
                      "removed from '%(for_user)s'.") %
                    {
                        'id_string': xform.id_string,
                        'for_user': for_user
                    }, audit, request)
                remove_perm('change_xform', user, xform)
                remove_perm('view_xform', user, xform)
                remove_perm('report_xform', user, xform)
    elif perm_type == 'link':
        current = MetaData.public_link(xform)
        if for_user == 'all':
            MetaData.public_link(xform, True)
        elif for_user == 'none':
            MetaData.public_link(xform, False)
        elif for_user == 'toggle':
            MetaData.public_link(xform, not current)
        audit = {
            'xform': xform.id_string
        }
        audit_log(
            Actions.FORM_PERMISSIONS_UPDATED, request.user, owner,
            _("Public link on '%(id_string)s' %(action)s.") %
            {
                'id_string': xform.id_string,
                'action': "created"
                if for_user == "all" or
                   (for_user == "toggle" and not current) else "removed"
            }, audit, request)

    if request.is_ajax():
        return HttpResponse(
            json.dumps(
                {'status': 'success'}), content_type='application/json')

    # return HttpResponseRedirect(reverse(show, kwargs={
    #    'username': username,
    #    'id_string': id_string
    # }))
    return HttpResponseRedirect(reverse(show_project_settings, kwargs={
        'username': username,
        'id_string': id_string
    }))


@require_POST
@login_required
def delete_data(request, username=None, id_string=None):
    xform, owner = check_and_set_user_and_form(username, id_string, request)
    response_text = u''
    if not xform or not has_edit_permission(
            xform, owner, request, xform.shared
    ):
        return HttpResponseForbidden(_(u'Not shared.'))

    data_id = request.POST.get('id')
    if not data_id:
        return HttpResponseBadRequest(_(u"id must be specified"))

    Instance.set_deleted_at(data_id)
    audit = {
        'xform': xform.id_string
    }
    audit_log(
        Actions.SUBMISSION_DELETED, request.user, owner,
        _("Deleted submission with id '%(record_id)s' "
          "on '%(id_string)s'.") %
        {
            'id_string': xform.id_string,
            'record_id': data_id
        }, audit, request)
    response_text = json.dumps({"success": "Deleted data %s" % data_id})
    if 'callback' in request.GET and request.GET.get('callback') != '':
        callback = request.GET.get('callback')
        response_text = ("%s(%s)" % (callback, response_text))

    return HttpResponse(response_text, content_type='application/json')


@require_POST
@is_owner
def link_to_bamboo(request, username, id_string):
    xform = get_object_or_404(XForm,
                              user__username__iexact=username,
                              id_string__exact=id_string)
    owner = xform.user
    audit = {
        'xform': xform.id_string
    }

    # try to delete the dataset first (in case it exists)
    if xform.bamboo_dataset and delete_bamboo_dataset(xform):
        xform.bamboo_dataset = u''
        xform.save()
        audit_log(
            Actions.BAMBOO_LINK_DELETED, request.user, owner,
            _("Bamboo link deleted on '%(id_string)s'.")
            % {'id_string': xform.id_string}, audit, request)

    # create a new one from all the data
    dataset_id = get_new_bamboo_dataset(xform)

    # update XForm
    xform.bamboo_dataset = dataset_id
    xform.save()
    ensure_rest_service(xform)

    audit_log(
        Actions.BAMBOO_LINK_CREATED, request.user, owner,
        _("Bamboo link created on '%(id_string)s'.") %
        {
            'id_string': xform.id_string,
        }, audit, request)

    return HttpResponseRedirect(reverse(show, kwargs={
        'username': username,
        'id_string': id_string
    }))


@require_POST
@is_owner
def update_xform(request, username, id_string):
    xform = get_object_or_404(
        XForm, user__username__iexact=username, id_string__exact=id_string)
    owner = xform.user

    def set_form():
        form = QuickConverter(request.POST, request.FILES)
        survey = form.publish(request.user, id_string).survey
        enketo_webform_url = reverse(
            enter_data,
            kwargs={'username': username, 'id_string': survey.id_string}
        )
        audit = {
            'xform': xform.id_string
        }
        audit_log(
            Actions.FORM_XLS_UPDATED, request.user, owner,
            _("XLS for '%(id_string)s' updated.") %
            {
                'id_string': xform.id_string,
            }, audit, request)
        return {
            'type': 'alert-success',
            'text': _(u'Successfully published %(form_id)s.'
                      u' <a href="%(form_url)s">Enter Web Form</a>'
                      u' or <a href="#preview-modal" data-toggle="modal">'
                      u'Preview Web Form</a>')
                    % {'form_id': survey.id_string,
                       'form_url': enketo_webform_url}
        }

    message = publish_form(set_form)
    messages.add_message(
        request, messages.INFO, message['text'], extra_tags=message['type'])

    return HttpResponseRedirect(reverse(show, kwargs={
        'username': username,
        'id_string': id_string
    }))


@is_owner
def activity(request, username):
    owner = get_object_or_404(User, username=username)

    return render(request, 'activity.html', {'user': owner})


def activity_fields(request):
    fields = [
        {
            'id': 'created_on',
            'label': _('Performed On'),
            'type': 'datetime',
            'searchable': False
        },
        {
            'id': 'action',
            'label': _('Action'),
            'type': 'string',
            'searchable': True,
            'options': sorted([Actions[e] for e in Actions.enums])
        },
        {
            'id': 'user',
            'label': 'Performed By',
            'type': 'string',
            'searchable': True
        },
        {
            'id': 'msg',
            'label': 'Description',
            'type': 'string',
            'searchable': True
        },
    ]
    response_text = json.dumps(fields)

    return HttpResponse(response_text, content_type='application/json')


@is_owner
def activity_api(request, username):
    from bson.objectid import ObjectId

    def stringify_unknowns(obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.strftime(DATETIME_FORMAT)
        return None

    try:
        query_args = {
            'username': username,
            'query': json.loads(request.GET.get('query'))
            if request.GET.get('query') else {},
            'fields': json.loads(request.GET.get('fields'))
            if request.GET.get('fields') else [],
            'sort': json.loads(request.GET.get('sort'))
            if request.GET.get('sort') else {}
        }
        if 'start' in request.GET:
            query_args["start"] = int(request.GET.get('start'))
        if 'limit' in request.GET:
            query_args["limit"] = int(request.GET.get('limit'))
        if 'count' in request.GET:
            query_args["count"] = True \
                if int(request.GET.get('count')) > 0 else False
        cursor = AuditLog.query_mongo(**query_args)
    except ValueError as e:
        return HttpResponseBadRequest(e.__str__())

    records = list(record for record in cursor)
    response_text = json.dumps(records, default=stringify_unknowns)
    if 'callback' in request.GET and request.GET.get('callback') != '':
        callback = request.GET.get('callback')
        response_text = ("%s(%s)" % (callback, response_text))

    return HttpResponse(response_text, content_type='application/json')


def qrcode(request, username, id_string):
    try:
        formhub_url = "http://%s/" % request.META['HTTP_HOST']
    except:
        formhub_url = "http://formhub.org/"
    formhub_url = formhub_url + username

    if settings.TESTING_MODE:
        formhub_url = "https://{}/{}".format(settings.TEST_HTTP_HOST,
                                             settings.TEST_USERNAME)

    results = _(u"Unexpected Error occured: No QRCODE generated")
    status = 200
    try:
        url = enketo_url(formhub_url, id_string)
    except Exception as e:
        error_msg = _(u"Error Generating QRCODE: %s" % e)
        results = """<div class="alert alert-error">%s</div>""" % error_msg
        status = 400
    else:
        if url:
            image = generate_qrcode(''.join((url, '#qr')))
            results = """<img class="qrcode" src="%s" alt="%s" />
                    </br><a href="%s" target="_blank">%s</a>""" \
                      % (image, url, url, url)
        else:
            status = 400

    return HttpResponse(results, content_type='text/html', status=status)


def enketo_preview(request, username, id_string):
    xform = get_object_or_404(
        XForm, user__username__iexact=username, id_string__exact=id_string)
    owner = xform.user
    if not has_permission(xform, owner, request, xform.shared):
        return HttpResponseForbidden(_(u'Not shared.'))
    enekto_preview_url = \
        "%(enketo_url)s?server=%(profile_url)s&id=%(id_string)s" % {
            'enketo_url': settings.ENKETO_PREVIEW_URL,
            'profile_url': request.build_absolute_uri(
                reverse(profile, kwargs={'username': owner.username})),
            'id_string': xform.id_string
        }
    return HttpResponseRedirect(enekto_preview_url)


@require_GET
@login_required
def username_list(request):
    data = []
    query = request.GET.get('query', None)
    if query:
        users = User.objects.values('username') \
            .filter(username__startswith=query, is_active=True, pk__gte=0)
        data = [user['username'] for user in users]

    return HttpResponse(json.dumps(data), content_type='application/json')


@login_required
def query_chart(request, username):
    surveyData = {}
    totalSubmission = []
    surveyObj = []
    xforms = XForm.objects.filter(user__username__iexact=username)
    cursor = connection.cursor()
    _DATETIME_FORMAT_SUBMIT = '%Y-%m-%d'
    xformObj = get_object_or_404(XForm, id=4)
    surveyObj.append(xformObj)
    form_id = str(xformObj.id_string)
    submission_date_query = "SELECT (json->>'start')::timestamp::date AS day_of_submission FROM logger_instance WHERE xform_id=11"
    cursor.execute(submission_date_query)
    fetchVal = cursor.fetchall()
    # print fetchVal
    value = []
    # try:
    for each in fetchVal:
        value.append(each[0].strftime(_DATETIME_FORMAT_SUBMIT))
        surveyData[form_id] = value
        # except Exception as e:
        #    surveyData[form_id] = fetchVal

        # print surveyData
    # print surveyData
    data_type = "num"
    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'surveyObj': surveyObj,
        'surveydata': json.dumps(surveyData),
        'data_type': data_type,
    })
    output = render(request, 'query_report.html', variables)
    return HttpResponse(output)


# submission_date_query = "SELECT row_to_json(t) FROM ( SELECT id, user_id, xform_id, survey_type_id, date_created, date_modified, status, uuid FROM public.logger_instance )t"
@login_required
def survey_summary(request):
    instance_parse()
    surveyData = {}
    permission_data = {}
    ownership = {}
    totalSubmission = []
    surveyObj = []
    xforms = get_viewable_projects(request)

    cursor = connection.cursor()
    _DATETIME_FORMAT_SUBMIT = '%Y-%m-%d'

    for xform in xforms:
        surveyObj.append(xform)
        form_id = str(xform.id_string)
        is_owner = xform.user == request.user
        users_with_perms = []
        for perm in get_users_with_perms(xform, attach_perms=True).items():
            has_perm = []
            if 'change_xform' in perm[1]:
                has_perm.append("Can Edit")
            if 'view_xform' in perm[1]:
                has_perm.append("Can View")
            if 'report_xform' in perm[1]:
                has_perm.append("Can submit to")
            users_with_perms.append(str(perm[0]) + "|" + "|".join(has_perm))
            permission_data[str(form_id)] = users_with_perms
        owner_data = []
        owner_data.append(is_owner)
        owner_data.append(xform.user.username)
        owner_data.append(request.user.username)
        ownership[form_id] = owner_data
        submission_date_query = "SELECT (json->>'_submission_time')::timestamp::date AS day_of_submission FROM logger_instance WHERE xform_id=" + str(
            xform.id) + ""
        cursor.execute(submission_date_query)
        fetchVal = cursor.fetchall()
        rowcount = cursor.rowcount
        date = []
        if rowcount == 0:
            date.append('no submission')
            surveyData[form_id] = date
        else:
            for each in fetchVal:
                date.append(each[0].strftime(_DATETIME_FORMAT_SUBMIT))
                surveyData[form_id] = date
                # print '----------surveyObj----------'
    # print surveyData

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'total_submission': totalSubmission,
        'surveyObj': surveyObj,
        'surveydata': json.dumps(surveyData),
        'ownership': json.dumps(ownership),
        'permission': json.dumps(permission_data),
    })
    output = render(request, 'survey_summary.html', variables)
    return HttpResponse(output)


@login_required
def sendMessageSubscriber(request, username):
    jsonData = {}
    NEW = 0
    PROCESSING = 1
    SUCCESS = 2
    FAIL = 3
    TYPE_MSG = 0
    TYPE_SMS = 1
    TYPE_EMAIL = 2
    SUBSCRIPTION_ID = "testshiam"
    responseText = "Default Text"
    if request.is_ajax():
        responseText = request.POST.get('delivermsg', 'Default Text')
        SUBSCRIPTION_ID = request.POST.get('subscribeid', 'Default Text')
        print 'responseText:: ' + responseText
    message = Message_Queue(subscribeid=SUBSCRIPTION_ID, status=NEW, response=responseText, msg_type=TYPE_MSG)
    message.save()
    message2 = Message_Queue(subscribeid=SUBSCRIPTION_ID, status=NEW, response=responseText, msg_type=TYPE_SMS)
    message2.save()
    message = Message_Queue(subscribeid=SUBSCRIPTION_ID, status=NEW, response=responseText, msg_type=TYPE_SMS)
    message.save()
    message2 = Message_Queue(subscribeid=SUBSCRIPTION_ID, status=NEW, response=responseText, msg_type=TYPE_EMAIL)
    message2.save()
    output = 'Sending Started...'
    variables = RequestContext(request, {
        'message': 'SaveComplete'
    })

    # redirect('/highchart/{}'.format(request.user))
    if request.is_ajax():
        jsonData[str('send')] = str('Sending started...')
        output = json.dumps(jsonData)
        return HttpResponse(output, content_type='application/json')
    return HttpResponseRedirect(
        reverse(survey_summary, kwargs={'username': request.user.username}))
    # return render_to_response('survey_summary.html', variables)


def get_viewable_projects(request):
    """
    Returns the list of projects/forms 
    which are created or shared to the currently
    logged in user.
    """
    content_user = get_object_or_404(User, username__iexact=request.user.username)
    form = QuickConverter()
    data = {'form': form}
    content_user = request.user
    all_forms = content_user.xforms.count()
    xforms = XForm.objects.filter(user=content_user) \
        .select_related('user', 'instances')
    user_xforms = xforms
    xfct = ContentType.objects.get(app_label='logger', model='xform')
    xfs = content_user.userobjectpermission_set.filter(content_type=xfct)
    shared_forms_pks = list(set([xf.object_pk for xf in xfs]))
    forms_shared_with = XForm.objects.filter(
        pk__in=shared_forms_pks).exclude(user=content_user) \
        .select_related('user')
    published_or_shared = XForm.objects.filter(
        pk__in=shared_forms_pks).select_related('user')
    xforms_list = [
        {
            'id': 'published',
            'xforms': user_xforms,
            'title': _(u"Published Forms"),
            'small': _("Export, map, and view submissions.")
        },
        {
            'id': 'shared',
            'xforms': forms_shared_with,
            'title': _(u"Shared Forms"),
            'small': _("List of forms shared with you.")
        },
        {
            'id': 'published_or_shared',
            'xforms': published_or_shared,
            'title': _(u"Published Forms"),
            'small': _("Export, map, and view submissions.")
        }
    ]

    new_list = []
    for xform_list in xforms_list:
        if xform_list['xforms'] not in new_list:
            new_list.extend(xform_list['xforms'])
    xforms_list = list(set(new_list))
    return xforms_list


@login_required
def d2dashboard(request, **kwargs):
    pow_piedata = []
    pl_piedata = []
    uht_piedata = []
    upl_piedata = []
    location_barchart = []
    income_barchart = []

    #pow_pie_query = 'SELECT brand_name,sum(pow) Amt  FROM vwPowBrand,vwMilkType WHERE vwPowBrand.id=vwMilkType.id Group by brand_name'
    #pl_pie_query = 'SELECT brand_name,sum(pl) Amt  FROM vwPLBrand,vwMilkType WHERE vwPLBrand.id=vwMilkType.id Group by brand_name'
    #uht_pie_query = 'SELECT brand_name,sum(uht) Amt  FROM vwUHTBrand,vwMilkType WHERE vwUHTBrand.id=vwMilkType.id Group by brand_name'
    #upl_pie_query = 'SELECT brand_name,sum(upl) Amt  FROM vwUPLBrand,vwMilkType WHERE vwUPLBrand.id=vwMilkType.id Group by brand_name'

    pow_pie_query = "with f as(with m as(with t as(select serial_number,brand_type,otherbrand_type from milk_survey_new where milk_type='POW')select distinct serial_number,brand_type brand_name from t where brand_type <>'' union all select distinct serial_number, otherbrand_type brand_name from t where otherbrand_type <>'') select brand_name,(count(distinct serial_number))::float amt,tc::float from m,(select count(distinct serial_number) tc from m) as n group by brand_name,tc order by amt desc)select brand_name,round((amt*100/tc)) from f"

    pl_pie_query = "with f as(with m as(with t as(select serial_number,brand_type,otherbrand_type from milk_survey_new where milk_type='PL')select distinct serial_number,brand_type brand_name from t where brand_type <>'' union all select distinct serial_number, otherbrand_type brand_name from t where otherbrand_type <>'') select brand_name,(count(distinct serial_number))::float amt,tc::float from m,(select count(distinct serial_number) tc from m) as n group by brand_name,tc order by amt desc)select brand_name,round((amt*100/tc)) from f"

    uht_pie_query = "with f as(with m as(with t as(select serial_number,brand_type,otherbrand_type from milk_survey_new where milk_type='UHT')select distinct serial_number,brand_type brand_name from t where brand_type <>'' union all select distinct serial_number, otherbrand_type brand_name from t where otherbrand_type <>'') select brand_name,(count(distinct serial_number))::float amt,tc::float from m,(select count(distinct serial_number) tc from m) as n group by brand_name,tc order by amt desc)select brand_name,round((amt*100/tc)) from f"

    upl_pie_query = "with f as(with m as(with t as(select serial_number,brand_type,otherbrand_type from milk_survey_new where milk_type='UPL')select distinct serial_number,brand_type brand_name from t where brand_type <>'' union all select distinct serial_number, otherbrand_type brand_name from t where otherbrand_type <>'') select brand_name,(count(distinct serial_number))::float amt,tc::float from m,(select count(distinct serial_number) tc from m) as n group by brand_name,tc order by amt desc)select brand_name,round((amt*100/tc)) from f"

    second_tab_table_query = "with f as(WITH m as(with t as(select serial_number,milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_uht,often_use_milk_for_consumption_or_making_milk_based_dishes_pl,often_use_milk_for_consumption_or_making_milk_based_dishes_upl,often_use_milk_for_consumption_or_making_milk_based_dishes_pow from milk_survey_new) select distinct serial_number,milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_pl frq from t where milk_type='PL' AND often_use_milk_for_consumption_or_making_milk_based_dishes_pl<>'' union ALL select distinct serial_number, milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_upl frq from t where milk_type='UPL' AND often_use_milk_for_consumption_or_making_milk_based_dishes_upl<>'' union ALL select distinct serial_number, milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_pow frq from t where milk_type='POW' AND often_use_milk_for_consumption_or_making_milk_based_dishes_pow<>'' union ALL  select distinct serial_number, milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_uht frq from t where milk_type='UHT' AND often_use_milk_for_consumption_or_making_milk_based_dishes_uht<>'') select frq,sum((case when milk_type='PL' then 1 else 0 end)::float) pl,sum((case when milk_type='POW' then 1 else 0 end)::float) pow,sum((case when milk_type='UHT' then 1 else 0 end)::float) uht,sum((case when milk_type='UPL' then 1 else 0 end)::float) upl,(select count(*) from m where milk_type='PL') tpl,(select count(*) from m where milk_type='UPL') tupl,(select count(*) from m where milk_type='POW') tpow,(select count(*) from m where milk_type='UHT') tuht from m group by frq order by frq) select frq,round((pl*100)/(case when tpl >0 then tpl else 1 end)) pl,round((pow*100)/(case when tpow >0 then tpl else 1 end)) pow,round((uht*100)/(case when tuht >0 then tpl else 1 end)) uht,round((upl*100)/(case when tupl >0 then tpl else 1 end)) upl from f"


    #location_barchart_query = "with m as(" \
    #                            "with t as(" \
    #                            "select center,milk_type,count(*) cnt from milk_survey_new " \
    #                            "group by center,milk_type order by 1,2)select center, " \
    #                            "(case when milk_type='PL' then cnt else 0 end) pl," \
    #                            "(case when milk_type='UPL' then cnt else 0 end) upl," \
    #                            "(case when milk_type='UHT' then cnt else 0 end) uht," \
    #                            "(case when milk_type='POW' then cnt else 0 end) pow" \
    #                            " from t) select center,sum(pl)::bigint pl,sum(upl)::bigint upl,sum(uht)::bigint uht,sum(pow)::bigint pow from m group by center"
    location_barchart_query = "with t1 as(with m as(with t as(select center,milk_type,count(distinct serial_number) cnt from milk_survey_new group by center,milk_type order by 1,2)select center,(case when milk_type='PL' then cnt else 0 end) pl,(case when milk_type='UPL' then cnt else 0 end) upl,(case when milk_type='UHT' then cnt else 0 end) uht,(case when milk_type='POW' then cnt else 0 end) pow from t) select center, sum(pl) pl,sum(upl) upl,sum(uht) uht, sum(pow) pow from m group by center)select t1.center,round((pl*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint pl,round((upl*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint upl,round((uht*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint uht,round((pow*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint pow  from t1,(select center,count(distinct serial_number) cnt_hh from milk_survey_new group by center) as t2 where t1.center=t2.center"
    
    #income_barchart_query = "with m as(" \
    #                        "with t as(" \
    #                        "select what_is_the_aggregated_monthly_household_income_range,milk_type,count(*) cnt from milk_survey_new " \
    #                        "group by what_is_the_aggregated_monthly_household_income_range,milk_type order by 1,2)select what_is_the_aggregated_monthly_household_income_range, " \
    #                        "(case when milk_type='PL' then cnt else 0 end) pl," \
    #                        "(case when milk_type='UPL' then cnt else 0 end) upl," \
    #                        "(case when milk_type='UHT' then cnt else 0 end) uht," \
    #                        "(case when milk_type='POW' then cnt else 0 end) pow" \
    #                        " from t) select what_is_the_aggregated_monthly_household_income_range,sum(pl)::bigint pl,sum(upl)::bigint upl,sum(uht)::bigint uht,sum(pow)::bigint pow from m group by what_is_the_aggregated_monthly_household_income_range"

    income_barchart_query ="with t1 as(with m as(with t as(select what_is_the_aggregated_monthly_household_income_range,milk_type,count(distinct serial_number) cnt from milk_survey_new group by what_is_the_aggregated_monthly_household_income_range,milk_type order by 1,2)select what_is_the_aggregated_monthly_household_income_range,(case when milk_type='PL' then cnt else 0 end) pl,(case when milk_type='UPL' then cnt else 0 end) upl,(case when milk_type='UHT' then cnt else 0 end) uht,(case when milk_type='POW' then cnt else 0 end) pow from t) select what_is_the_aggregated_monthly_household_income_range, sum(pl) pl,sum(upl) upl,sum(uht) uht, sum(pow) pow from m group by what_is_the_aggregated_monthly_household_income_range)select t1.what_is_the_aggregated_monthly_household_income_range,round((pl*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint pl,round((upl*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint upl,round((uht*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint uht,round((pow*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint pow  from t1,(select what_is_the_aggregated_monthly_household_income_range,count(distinct serial_number) cnt_hh from milk_survey_new group by what_is_the_aggregated_monthly_household_income_range) as t2 where t1.what_is_the_aggregated_monthly_household_income_range=t2.what_is_the_aggregated_monthly_household_income_range"

    consumption_first_query = "with m as(with t as(with h as (with k as (select serial_number,center,milk_type,packed_pasteurized_liquid_milk_pl,powder_milk_pow,unpacked_liquid_milk_upl,packed_uht_liquid_milk_uht from milk_survey_new)select distinct serial_number,center,milk_type,packed_pasteurized_liquid_milk_pl cnt from k  where milk_type='PL' union all select distinct serial_number,center,milk_type,powder_milk_pow cnt from k  where milk_type='POW' union all select distinct serial_number,center,milk_type,unpacked_liquid_milk_upl cnt from k  where milk_type='UPL' union all select distinct serial_number,center,milk_type,packed_uht_liquid_milk_uht cnt from k  where milk_type='UHT')select center,milk_type,AVG(cnt::float) cnt from h group by center,milk_type)select center,(case when milk_type='PL' then cnt else 0 end) pl,(case when milk_type='UPL' then cnt else 0 end) upl,(case when milk_type='UHT' then cnt else 0 end) uht,(case when milk_type='POW' then cnt else 0 end) pow from t) select center,round(sum(pl)::float) pl,round(sum(upl)::float) upl,round(sum(uht)::float) uht,round(sum(pow)::float) pow from m group by center"

                            
    consumption_second_query = "with m as(with t as(with h as (with k as (select serial_number,what_is_the_aggregated_monthly_household_income_range,milk_type,packed_pasteurized_liquid_milk_pl,powder_milk_pow,unpacked_liquid_milk_upl,packed_uht_liquid_milk_uht from milk_survey_new)select distinct serial_number,what_is_the_aggregated_monthly_household_income_range,milk_type,packed_pasteurized_liquid_milk_pl cnt from k  where milk_type='PL' union all select distinct serial_number,what_is_the_aggregated_monthly_household_income_range,milk_type,powder_milk_pow cnt from k  where milk_type='POW' union all select distinct serial_number,what_is_the_aggregated_monthly_household_income_range,milk_type,unpacked_liquid_milk_upl cnt from k  where milk_type='UPL' union all select distinct serial_number,what_is_the_aggregated_monthly_household_income_range,milk_type,packed_uht_liquid_milk_uht cnt from k  where milk_type='UHT')select what_is_the_aggregated_monthly_household_income_range,milk_type,AVG(cnt::float) cnt from h group by what_is_the_aggregated_monthly_household_income_range,milk_type)select what_is_the_aggregated_monthly_household_income_range,(case when milk_type='PL' then cnt else 0 end) pl,(case when milk_type='UPL' then cnt else 0 end) upl,(case when milk_type='UHT' then cnt else 0 end) uht,(case when milk_type='POW' then cnt else 0 end) pow from t) select what_is_the_aggregated_monthly_household_income_range,round(sum(pl)::float) pl,round(sum(upl)::float) upl,round(sum(uht)::float) uht,round(sum(pow)::float) pow from m group by what_is_the_aggregated_monthly_household_income_range"



    consumer_purchase_behaviour_fquery = "with m as(with t as(select preferred_sku1,avg_unit_sku1,preferred_sku2,avg_unit_sku2 from milk_survey_new)select preferred_sku1 sku, avg_unit_sku1 sku_unit from t where preferred_sku1<>'' and avg_unit_sku1<>'' union all select preferred_sku2 sku, avg_unit_sku2 sku_unit from t where preferred_sku2<>'' and avg_unit_sku2 <>'') select sku,count(*) rc,avg(sku_unit::bigint)::bigint avgsku from m group by sku order by sku"


    consumer_purchase_behaviour_aux_fquery = "select count(*) tr from milk_survey_new"

    
    counsumer_purchase_behaviour_second_query = "with m as(with t as(select q3a1_from_where_do_you_usually_purchase_milk,q3b1_how_many_times_in_a_month_you_purchase_the_product_from,q3a2_from_where_do_you_usually_purchase_milk,q3b2_how_many_times_in_a_month_you_purchase_the_product_from,q3a3_from_where_do_you_usually_purchase_milk,q3b3_how_many_times_in_a_month_you_purchase_the_product_from  from milk_survey_new )select q3a1_from_where_do_you_usually_purchase_milk place,q3b1_how_many_times_in_a_month_you_purchase_the_product_from frq from t union all select q3a2_from_where_do_you_usually_purchase_milk place,q3b2_how_many_times_in_a_month_you_purchase_the_product_from frq from t union all select q3a3_from_where_do_you_usually_purchase_milk place,q3b3_how_many_times_in_a_month_you_purchase_the_product_from frq from t)select place,count(*) rc,avg(frq::bigint)::bigint avgpf from m where place <>'' and frq <>'' group by place order by rc desc"

    consumer_purchase_behaviour_bc_query = "with m as(with t as(select center,what_is_the_aggregated_monthly_household_income_range,AVG((case when milk_type='PL' then packed_pasteurized_liquid_milk_pl when milk_type='POW' then powder_milk_pow  when milk_type='UPL' then unpacked_liquid_milk_upl when milk_type='UHT' then packed_uht_liquid_milk_uht  else '0' end)::float) cnt from milk_survey_new  group by center,what_is_the_aggregated_monthly_household_income_range order by 1,2)select center,(case when what_is_the_aggregated_monthly_household_income_range='BDT 11,001 to BDT 15,000' then cnt else 0 end) BDT_11_15_K,(case when what_is_the_aggregated_monthly_household_income_range='BDT 15001 to BDT 20,000' then cnt else 0 end) BDT_15_20_K,(case when what_is_the_aggregated_monthly_household_income_range='BDT 20001 to BDT 25,000' then cnt else 0 end) BDT_20_25_K,(case when what_is_the_aggregated_monthly_household_income_range='BDT 25001 to BDT 30,000' then cnt else 0 end) BDT_25_30_K from t) select center,sum(BDT_11_15_K) BDT_11_15_K,sum(BDT_15_20_K) BDT_15_20_K,sum(BDT_20_25_K) BDT_20_25_K,sum(BDT_25_30_K) BDT_25_30_K from m group by center"

    ###############################
    cursor = connection.cursor()

    cursor.execute(consumer_purchase_behaviour_aux_fquery)
    dcount = cursor.fetchone()

    cursor.execute(consumer_purchase_behaviour_fquery)
    fetchVal = cursor.fetchall()
    consumer_purchase_behaviour_first_table_data = fetchVal
    cpbft_full_data = []
    for crow in consumer_purchase_behaviour_first_table_data:
        sublist = []
        sublist.append(crow[0])
        sublist.append(round((crow[1]/float(dcount[0]))*100))
        sublist.append(crow[2])
        cpbft_full_data.append(sublist)

    cpbft_data = json.dumps(cpbft_full_data)
    #########################################

    cursor.execute(counsumer_purchase_behaviour_second_query)
    fetchVal = cursor.fetchall()
    consumer_purchase_behaviour_second_table_data = fetchVal
    cpbst_full_data = []
    #for crow in consumer_purchase_behaviour_first_table_data:
    for crow in consumer_purchase_behaviour_second_table_data:
        sublist = []
        sublist.append(crow[0])        
        sublist.append(round((crow[1]/float(dcount[0]))*100))        
        sublist.append(crow[2])
        cpbst_full_data.append(sublist)

    cpbst_data = json.dumps(cpbst_full_data)

    ##################################

    cursor.execute(second_tab_table_query)
    fetchVal = cursor.fetchall()
    table_data = json.dumps(fetchVal)

    cursor.execute(pow_pie_query)
    fetchVal = cursor.fetchall()
    for eachval in fetchVal:
        d = {"name": eachval[0], "y": eachval[1]}
        pow_piedata.append(d)

    pow_pie = json.dumps(pow_piedata)

    cursor.execute(pl_pie_query)
    fetchVal = cursor.fetchall()

    for eachval in fetchVal:
        d = {"name": eachval[0], "y": eachval[1]}
        pl_piedata.append(d)

    pl_pie = json.dumps(pl_piedata)

    cursor.execute(uht_pie_query)
    fetchVal = cursor.fetchall()
    for eachval in fetchVal:
        d = {"name": eachval[0], "y": eachval[1]}
        uht_piedata.append(d)

    #uht_pie = json.dumps(pow_piedata)
    uht_pie = json.dumps(uht_piedata)

    cursor.execute(upl_pie_query)
    fetchVal = cursor.fetchall()
    for eachval in fetchVal:
        d = {"name": eachval[0], "y": eachval[1]}
        upl_piedata.append(d)

    upl_pie = json.dumps(upl_piedata)
    
    ########################################
    cursor.execute(location_barchart_query)
    fetchVal = cursor.fetchall()

    location_bc = create_bar_chart_data(fetchVal)
    
    ########################################
    cursor.execute(income_barchart_query)
    fetchVal = cursor.fetchall()

    income_bc = create_bar_chart_data(fetchVal)

    ########################################
    cursor.execute(consumption_first_query)
    fetchVal = cursor.fetchall()

    consumption_first = create_bar_chart_data(fetchVal)

    ########################################
    cursor.execute(consumption_second_query)
    fetchVal = cursor.fetchall()

    consumption_second = create_bar_chart_data(fetchVal)

    #########################################
    cursor.execute(consumer_purchase_behaviour_bc_query)
    fetchVal = cursor.fetchall()
    cpbbc_data = create_bar_chart_data(fetchVal)


    cursor.close()

    return render(request, "d2dashboard.html",
                  {'cpbbc_data':cpbbc_data,'cpbst_data':cpbst_data,'cpbft_data':cpbft_data,'table_data':table_data,'pow_pie': pow_pie, 'pl_pie': pl_pie, 'upl_pie': upl_pie, 'uht_pie': uht_pie,
                   'location_bc': location_bc, 'income_bc': income_bc,'consumption_first':consumption_first,'consumption_second':consumption_second})


def splitIntoWords(s):
    words = []
    inword = 0
    for c in s:
        if c in " \r\n\t":  # whitespace
            inword = 0
        elif not inword:
            words = words + [c]
            inword = 1
        else:
            words[-1] = words[-1] + c
    return words

def searchByRegionCat(request):
    category = request.POST.get("category")
    region = request.POST.get("region")
    income = request.POST.get("income")
    brands = request.POST.get("brands")
    split_cats = category.split("_")
    split_region = region.split("_")
    split_income = income.split("_")
    split_brands = brands.split("_")

    cat_where_clause = ""
    for sc in split_cats:
        if cat_where_clause == "":
            cat_where_clause += "'"+sc+"'"
        else:
            cat_where_clause += ",'" + sc + "'"

    region_where_clause = ""
    for dc in split_region:
        if region_where_clause == "":
            region_where_clause += "'"+dc+"'"
        else:
            region_where_clause += ",'" + dc + "'"

    income_where_clause = ""
    for ic in split_income:
        if income_where_clause == "":
            income_where_clause += "'"+ic+"'"
        else:
            income_where_clause += ",'" + ic + "'"

    brand_where_clause = ""
    for vc in split_brands:
        if brand_where_clause == "":
            brand_where_clause += "'"+vc+"'"
        else:
            brand_where_clause += ",'" + vc + "'"

    
    replacement = ""

    
    #devashish 
    if cat_where_clause != "":
        replacement="milk_type in("+cat_where_clause+")"
    if region_where_clause != "":
        if replacement != "":
            replacement+=" and center in(" + region_where_clause + ")"
        else:
            replacement=" center in(" + region_where_clause + ")"
    if income_where_clause != "":
        if replacement != "":
            replacement+=" and what_is_the_aggregated_monthly_household_income_range in(" + income_where_clause + ")"
        else:
            replacement=" what_is_the_aggregated_monthly_household_income_range in(" + income_where_clause + ")"
    if brand_where_clause != "":
        if replacement != "":
            replacement+=" and brand_type in(" + brand_where_clause + ")"
        else:
            replacement=" brand_type in(" + brand_where_clause + ")"
    if replacement != "":
        replacement="where "+replacement
    #end devashish
    
                         
    location_barchart_query = "with t1 as(with m as(with t as(select center,milk_type,count(distinct serial_number) cnt from milk_survey_new "+replacement+" group by center,milk_type order by 1,2)select center,(case when milk_type='PL' then cnt else 0 end) pl,(case when milk_type='UPL' then cnt else 0 end) upl,(case when milk_type='UHT' then cnt else 0 end) uht,(case when milk_type='POW' then cnt else 0 end) pow from t) select center, sum(pl) pl,sum(upl) upl,sum(uht) uht, sum(pow) pow from m group by center)select t1.center,round((pl*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint pl,round((upl*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint upl,round((uht*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint uht,round((pow*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint pow  from t1,(select center,count(distinct serial_number) cnt_hh from milk_survey_new group by center) as t2 where t1.center=t2.center"

    income_barchart_query ="with t1 as(with m as(with t as(select what_is_the_aggregated_monthly_household_income_range,milk_type,count(distinct serial_number) cnt from milk_survey_new "+replacement+" group by what_is_the_aggregated_monthly_household_income_range,milk_type order by 1,2)select what_is_the_aggregated_monthly_household_income_range,(case when milk_type='PL' then cnt else 0 end) pl,(case when milk_type='UPL' then cnt else 0 end) upl,(case when milk_type='UHT' then cnt else 0 end) uht,(case when milk_type='POW' then cnt else 0 end) pow from t) select what_is_the_aggregated_monthly_household_income_range, sum(pl) pl,sum(upl) upl,sum(uht) uht, sum(pow) pow from m group by what_is_the_aggregated_monthly_household_income_range)select t1.what_is_the_aggregated_monthly_household_income_range,round((pl*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint pl,round((upl*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint upl,round((uht*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint uht,round((pow*100)/(case when cnt_hh=0 then 1 else cnt_hh end))::bigint pow  from t1,(select what_is_the_aggregated_monthly_household_income_range,count(distinct serial_number) cnt_hh from milk_survey_new group by what_is_the_aggregated_monthly_household_income_range) as t2 where t1.what_is_the_aggregated_monthly_household_income_range=t2.what_is_the_aggregated_monthly_household_income_range"

    firstcon_barchart_query = "with m as(with t as(with h as (with k as (select serial_number,center,milk_type,packed_pasteurized_liquid_milk_pl,powder_milk_pow,unpacked_liquid_milk_upl,packed_uht_liquid_milk_uht from milk_survey_new "+replacement+")select distinct serial_number,center,milk_type,packed_pasteurized_liquid_milk_pl cnt from k  where milk_type='PL' union all select distinct serial_number,center,milk_type,powder_milk_pow cnt from k  where milk_type='POW' union all select distinct serial_number,center,milk_type,unpacked_liquid_milk_upl cnt from k  where milk_type='UPL' union all select distinct serial_number,center,milk_type,packed_uht_liquid_milk_uht cnt from k  where milk_type='UHT')select center,milk_type,AVG(cnt::float) cnt from h group by center,milk_type)select center,(case when milk_type='PL' then cnt else 0 end) pl,(case when milk_type='UPL' then cnt else 0 end) upl,(case when milk_type='UHT' then cnt else 0 end) uht,(case when milk_type='POW' then cnt else 0 end) pow from t) select center,round(sum(pl)::float) pl,round(sum(upl)::float) upl,round(sum(uht)::float) uht,round(sum(pow)::float) pow from m group by center"

                            
    secondcon_barchart_query = "with m as(with t as(with h as (with k as (select serial_number,what_is_the_aggregated_monthly_household_income_range,milk_type,packed_pasteurized_liquid_milk_pl,powder_milk_pow,unpacked_liquid_milk_upl,packed_uht_liquid_milk_uht from milk_survey_new "+replacement+" )select distinct serial_number,what_is_the_aggregated_monthly_household_income_range,milk_type,packed_pasteurized_liquid_milk_pl cnt from k  where milk_type='PL' union all select distinct serial_number,what_is_the_aggregated_monthly_household_income_range,milk_type,powder_milk_pow cnt from k  where milk_type='POW' union all select distinct serial_number,what_is_the_aggregated_monthly_household_income_range,milk_type,unpacked_liquid_milk_upl cnt from k  where milk_type='UPL' union all select distinct serial_number,what_is_the_aggregated_monthly_household_income_range,milk_type,packed_uht_liquid_milk_uht cnt from k  where milk_type='UHT')select what_is_the_aggregated_monthly_household_income_range,milk_type,AVG(cnt::float) cnt from h group by what_is_the_aggregated_monthly_household_income_range,milk_type)select what_is_the_aggregated_monthly_household_income_range,(case when milk_type='PL' then cnt else 0 end) pl,(case when milk_type='UPL' then cnt else 0 end) upl,(case when milk_type='UHT' then cnt else 0 end) uht,(case when milk_type='POW' then cnt else 0 end) pow from t) select what_is_the_aggregated_monthly_household_income_range,round(sum(pl)::float) pl,round(sum(upl)::float) upl,round(sum(uht)::float) uht,round(sum(pow)::float) pow from m group by what_is_the_aggregated_monthly_household_income_range"

    #second_tab_table_query = "WITH m as(with t as(select serial_number,milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_uht,often_use_milk_for_consumption_or_making_milk_based_dishes_pl,often_use_milk_for_consumption_or_making_milk_based_dishes_upl,often_use_milk_for_consumption_or_making_milk_based_dishes_pow from milk_survey_new "+replacement+" ) select distinct serial_number,milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_pl frq from t where milk_type='PL' AND often_use_milk_for_consumption_or_making_milk_based_dishes_pl<>'' union ALL select distinct serial_number, milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_upl frq from t where milk_type='UPL' AND often_use_milk_for_consumption_or_making_milk_based_dishes_upl<>'' union ALL select distinct serial_number, milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_pow frq from t where milk_type='POW' AND often_use_milk_for_consumption_or_making_milk_based_dishes_pow<>'' union ALL  select distinct serial_number, milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_uht frq from t where milk_type='UHT' AND often_use_milk_for_consumption_or_making_milk_based_dishes_uht<>'') select frq,sum((case when milk_type='PL' then 1 else 0 end)::float) pl,sum((case when milk_type='POW' then 1 else 0 end)::float) pow,sum((case when milk_type='UHT' then 1 else 0 end)::float) uht,sum((case when milk_type='UPL' then 1 else 0 end)::float) upl from m group by frq order by frq"

    second_tab_table_query = "with f as(WITH m as(with t as(select serial_number,milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_uht,often_use_milk_for_consumption_or_making_milk_based_dishes_pl,often_use_milk_for_consumption_or_making_milk_based_dishes_upl,often_use_milk_for_consumption_or_making_milk_based_dishes_pow from milk_survey_new "+replacement+" ) select distinct serial_number,milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_pl frq from t where milk_type='PL' AND often_use_milk_for_consumption_or_making_milk_based_dishes_pl<>'' union ALL select distinct serial_number, milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_upl frq from t where milk_type='UPL' AND often_use_milk_for_consumption_or_making_milk_based_dishes_upl<>'' union ALL select distinct serial_number, milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_pow frq from t where milk_type='POW' AND often_use_milk_for_consumption_or_making_milk_based_dishes_pow<>'' union ALL  select distinct serial_number, milk_type,often_use_milk_for_consumption_or_making_milk_based_dishes_uht frq from t where milk_type='UHT' AND often_use_milk_for_consumption_or_making_milk_based_dishes_uht<>'') select frq,sum((case when milk_type='PL' then 1 else 0 end)::float) pl,sum((case when milk_type='POW' then 1 else 0 end)::float) pow,sum((case when milk_type='UHT' then 1 else 0 end)::float) uht,sum((case when milk_type='UPL' then 1 else 0 end)::float) upl,(select count(*) from m where milk_type='PL') tpl,(select count(*) from m where milk_type='UPL') tupl,(select count(*) from m where milk_type='POW') tpow,(select count(*) from m where milk_type='UHT') tuht from m group by frq order by frq) select frq,round((pl*100)/(case when tpl >0 then tpl else 1 end)) pl,round((pow*100)/(case when tpow >0 then tpl else 1 end)) pow,round((uht*100)/(case when tuht >0 then tpl else 1 end)) uht,round((upl*100)/(case when tupl >0 then tpl else 1 end)) upl from f"




    consumer_purchase_behaviour_aux_fquery = "select count(*) tr from milk_survey_new "+ replacement
   

    cursor = connection.cursor()

    cursor.execute(consumer_purchase_behaviour_aux_fquery)
    dcount = cursor.fetchone()

    consumer_purchase_behaviour_fquery = "with m as(with t as(select preferred_sku1,avg_unit_sku1,preferred_sku2,avg_unit_sku2 from milk_survey_new "+replacement+" )select preferred_sku1 sku, avg_unit_sku1 sku_unit from t where preferred_sku1<>'' and avg_unit_sku1<>'' union all select preferred_sku2 sku, avg_unit_sku2 sku_unit from t where preferred_sku2<>'' and avg_unit_sku2 <>'') select sku,(count(*)*100/"+str(dcount[0])+") rc,avg(sku_unit::bigint)::bigint avgsku from m group by sku order by sku"    

    print consumer_purchase_behaviour_fquery
    counsumer_purchase_behaviour_second_query = "with m as(with t as(select q3a1_from_where_do_you_usually_purchase_milk,q3b1_how_many_times_in_a_month_you_purchase_the_product_from,q3a2_from_where_do_you_usually_purchase_milk,q3b2_how_many_times_in_a_month_you_purchase_the_product_from,q3a3_from_where_do_you_usually_purchase_milk,q3b3_how_many_times_in_a_month_you_purchase_the_product_from  from milk_survey_new "+replacement+")select q3a1_from_where_do_you_usually_purchase_milk place,q3b1_how_many_times_in_a_month_you_purchase_the_product_from frq from t union all select q3a2_from_where_do_you_usually_purchase_milk place,q3b2_how_many_times_in_a_month_you_purchase_the_product_from frq from t union all select q3a3_from_where_do_you_usually_purchase_milk place,q3b3_how_many_times_in_a_month_you_purchase_the_product_from frq from t)select place,(count(*)*100/"+str(dcount[0])+") rc,avg(frq::bigint)::bigint avgpf from m where place <>'' and frq <>'' group by place order by rc desc"


    #location data first tab 
    cursor.execute(location_barchart_query)
    fetchVal = cursor.fetchall()
    location_bc = create_bar_chart_data(fetchVal)

    #income data first tab
    cursor.execute(income_barchart_query)
    fetchVal = cursor.fetchall()
    income_bc = create_bar_chart_data(fetchVal)

    #consumption first chart
    cursor.execute(firstcon_barchart_query)
    fetchVal = cursor.fetchall()
    f_con = create_bar_chart_data(fetchVal)

    #consumption secon chart
    cursor.execute(secondcon_barchart_query)
    fetchVal = cursor.fetchall()
    s_con = create_bar_chart_data(fetchVal)

    #consumption table
    cursor.execute(second_tab_table_query)
    fetchVal = cursor.fetchall()
    f_con_table = json.dumps(fetchVal)

    #consumption behahe table1
    cursor.execute(consumer_purchase_behaviour_fquery)
    fetchVal = cursor.fetchall()
    cpbft_data = json.dumps(fetchVal)

    #consumption behave table2
    cursor.execute(counsumer_purchase_behaviour_second_query)
    fetchVal = cursor.fetchall()
    cpbst_data = json.dumps(fetchVal)
    cursor.close()

    return HttpResponse(json.dumps(
        {'location_bc': location_bc, 'income_bc': income_bc, 'f_con':f_con, 's_con':s_con,'f_con_table':f_con_table,'cpbst_data':cpbst_data,'cpbft_data':cpbft_data}), content_type='application/json')



def searchByRegionCat_consumption(request):
    category = request.POST.get("category")
    region = request.POST.get("region")
    income = request.POST.get("income")
    split_cats = category.split("_")
    split_region = region.split("_")
    split_income = income.split("_")

    cat_where_clause = ""
    for sc in split_cats:
        if cat_where_clause == "":
            cat_where_clause += "'"+sc+"'"
        else:
            cat_where_clause += ",'" + sc + "'"

    region_where_clause = ""
    for dc in split_region:
        if region_where_clause == "":
            region_where_clause += "'"+dc+"'"
        else:
            region_where_clause += ",'" + dc + "'"

    income_where_clause = ""
    for ic in split_income:
        if income_where_clause == "":
            income_where_clause += "'"+ic+"'"
        else:
            income_where_clause += ",'" + ic + "'"

    brand_where_clause = ""

    replacement = ""

    #devashish 
    if cat_where_clause != "":
        replacement="milk_type in("+cat_where_clause+")"
    if region_where_clause != "":
        if replacement != "":
            replacement+=" and center in(" + region_where_clause + ")"
        else:
            replacement=" center in(" + region_where_clause + ")"
    if income_where_clause != "":
        if replacement != "":
            replacement+=" and what_is_the_aggregated_monthly_household_income_range in(" + income_where_clause + ")"
        else:
            replacement=" what_is_the_aggregated_monthly_household_income_range in(" + income_where_clause + ")"
    if brand_where_clause != "":
        if replacement != "":
            replacement+=" and brand_type in(" + brand_where_clause + ")"
        else:
            replacement=" brand_type in(" + brand_where_clause + ")"
    if replacement != "":
        replacement="where "+replacement
    #end devashish
    
                         


    firstcon_barchart_query = "with m as(" \
                                "with t as(" \
                                "select center,milk_type,AVG((case when milk_type='PL' then packed_pasteurized_liquid_milk_pl when milk_type='POW' then powder_milk_pow when milk_type='UPL' then unpacked_liquid_milk_upl when milk_type='UHT' then packed_uht_liquid_milk_uht  else '0' end)::bigint) cnt from milk_survey_new " + replacement + "" \
                                " group by center,milk_type order by 1,2)select center, " \
                                "(case when milk_type='PL' then cnt else 0 end) pl," \
                                "(case when milk_type='UPL' then cnt else 0 end) upl," \
                                "(case when milk_type='UHT' then cnt else 0 end) uht," \
                                "(case when milk_type='POW' then cnt else 0 end) pow" \
                                " from t) select center,sum(pl)::bigint pl,sum(upl)::bigint upl,sum(uht)::bigint uht,sum(pow)::bigint pow from m group by center"
    

    secondcon_barchart_query = "with m as(" \
                            "with t as(" \
                            "select what_is_the_aggregated_monthly_household_income_range,milk_type,AVG((case when milk_type='PL' then packed_pasteurized_liquid_milk_pl when milk_type='POW' then powder_milk_pow when milk_type='UPL' then unpacked_liquid_milk_upl when milk_type='UHT' then packed_uht_liquid_milk_uht  else '0' end)::bigint) cnt from milk_survey_new " + replacement + "" \
                            " group by what_is_the_aggregated_monthly_household_income_range,milk_type order by 1,2)select what_is_the_aggregated_monthly_household_income_range, " \
                            "(case when milk_type='PL' then cnt else 0 end) pl," \
                            "(case when milk_type='UPL' then cnt else 0 end) upl," \
                            "(case when milk_type='UHT' then cnt else 0 end) uht," \
                            "(case when milk_type='POW' then cnt else 0 end) pow" \
                            " from t) select what_is_the_aggregated_monthly_household_income_range,sum(pl)::bigint pl,sum(upl)::bigint upl,sum(uht)::bigint uht,sum(pow)::bigint pow from m group by what_is_the_aggregated_monthly_household_income_range"

    cursor = connection.cursor()

    #location data first tab 
    cursor.execute(location_barchart_query)
    fetchVal = cursor.fetchall()
    location_bc = create_bar_chart_data(fetchVal)

    #income data first tab
    cursor.execute(income_barchart_query)
    fetchVal = cursor.fetchall()
    income_bc = create_bar_chart_data(fetchVal)

    cursor.close()

    return HttpResponse(json.dumps(
        {'location_bc': location_bc, 'income_bc': income_bc}), content_type='application/json')


def create_bar_chart_data(query_data):
    final_barchart_arr = []
    for eachval in query_data:
        subList = []
        subList.append(eachval[1] if eachval[1] is not None else 0)
        subList.append(eachval[2] if eachval[2] is not None else 0)
        subList.append(eachval[3] if eachval[3] is not None else 0)
        subList.append(eachval[4] if eachval[4] is not None else 0)

        if eachval[0].startswith('BDT'):
            words = splitIntoWords(eachval[0])
            p1 = words[1].replace(' ', '')[:-4] if ',' in words[1] else words[1].replace(' ', '')[:-3]
            p2 = words[4].replace(' ', '')[:-4] if ',' in words[4] else words[1].replace(' ', '')[:-3]
            cname = p1 + 'K-'+ p2 + 'K'
        else:
            cname = eachval[0]

        d = {"name": cname, "data": subList}

        final_barchart_arr.append(d)
        #print "#######################################"
        #print final_barchart_arr
        #print "#######################################"

    return json.dumps(final_barchart_arr)


@login_required
def villages_list(request):
    villages_list_query = "SELECT p.district_english,p.district_bangla,p.upazila_english,p.upazila_bangla,p.union_english,p.union_bangla,p.village_english,p.village_bangla,p.org_english,p.org_bangla,p.population,p.hh_number,p.village_id FROM(WITH t AS (SELECT json ->> 'village' village_id, json ->> 'hh_number' hh_number, json ->> 'population' population FROM logger_instance WHERE xform_id = 399) SELECT vwvillage.*, t.hh_number, t.population FROM t, vwvillage WHERE t.village_id = vwvillage.village_id) p"
    villages_list_data = json.dumps(__db_fetch_values(villages_list_query))
    return render(request, "csvp_villages_list.html", {'villages_list_data':villages_list_data})


@login_required
def csvp_single_village(request,village_id):

    village_info_query = "SELECT union_id, upazilla_id, union_bangla, union_english, district_bangla, district_english, upazila_bangla, upazila_english, district_id, org_id, org_english, org_bangla, village_id, village_bangla, village_english FROM public.vwvillage WHERE village_id = '" + str(village_id) + "'"
    village_info_data = json.dumps(__db_fetch_values_dict(village_info_query))

    legends_query = "SELECT * FROM vwlegend_village WHERE village = '" + str(village_id) + "'"
    legends_data = json.dumps(__db_fetch_values(legends_query))

    crop_query = "SELECT crops_name, crops_name_bn, boishakh, jaistha, ashar, shraban, vadra, aashwin, kartik, agrahayon, poush, magh, falgun, chaitra, land_amount, production, farmer_number, xform_id_string, instance_id FROM public.vwcropcalendar WHERE village = '" + str(village_id) + "'"
    crop_data = json.dumps(__db_fetch_values(crop_query))

    priority_query = "SELECT rank_problem::int, problem, rank_problem_bn,xform_id_string, instance_id FROM public.vwproblemrank WHERE village = '" + str(village_id) + "' ORDER BY rank_problem ASC"
    priority_data = json.dumps(__db_fetch_values(priority_query))

    climate_imapct_query = "SELECT climate_change_type, climate_change_type_bn, climate_change_impact, climate_change_impact_bn,  boishakh, jaistha, ashar, shraban, vadra, aashwin, kartik, agrahayon, poush, magh, falgun, chaitra,xform_id_string, instance_id FROM vwclimateimpact WHERE village = '" + str(village_id) + "'"
    climate_imapct_data = json.dumps(__db_fetch_values(climate_imapct_query))

    season_query = "SELECT parameter, parameter_bn, boishakh_explanation,boishakh_explanation_bn,boishakh, jaistha_explanation,jaistha_explanation_bn,jaistha, ashar_explanation,ashar_explanation_bn,ashar, shraban_explanation,shraban_explanation_bn,shraban, vadra_explanation,vadra_explanation_bn,vadra, aashwin_explanation,aashwin_explanation_bn,aashwin, kartik_explanation,kartik_explanation_bn,kartik, agrahayon_explanation,agrahayon_explanation_bn,agrahayon, poush_explanation,poush_explanation_bn,poush, magh_explanation,magh_explanation_bn,magh, falgun_explanation,falgun_explanation_bn,falgun, chaitra_explanation,chaitra_explanation_bn,chaitra, xform_id_string, instance_id FROM PUBLIC.vwseasoncalendar WHERE village = '" + str(village_id) + "' and instance_id=(select max(instance_id) from vwseasoncalendar where village = '" + str(village_id) + "')"
    season_data = json.dumps(__db_fetch_values(season_query))

    problem_matrix_query = "SELECT work_deatails, work_deatails_bn, problem_type_time, problem_type_time_bnproblem_type_time_bn, short_term_solution, short_term_solution_bn, long_term_solution, long_term_solution_bn, required_resouces, required_resouces_bn, xform_id_string, instance_id FROM public.vwproblemmatrix WHERE village = '" + str(village_id) + "'"
    problem_matrix_data = json.dumps(__db_fetch_values(problem_matrix_query))

    livelihood_query = "SELECT income_source, income_source_bn,hh_involved_income_source_bn,hh_involved_income_source_last_10_years_bn,last_10_years_changes,last_10_years_changes_bn,summer,rainy,autumn,hemonto,winter,spring, type_problem_faced,type_problem_faced_bn,last_10_years_changes,last_10_years_changes_bn, xform_id_string, instance_id FROM public.vwlivelihood WHERE village = '" + str(village_id) + "'"
    livelihood_data = json.dumps(__db_fetch_values(livelihood_query))

    village_labels_query = "SELECT vil.district_english,vil.district_bangla,vil.upazila_english,vil.upazila_bangla,vil.union_english,vil.union_bangla,vil.village_english,vil.village_bangla,vwngo.ngo_english,vwngo.ngo_bangla FROM public.vwvillagesummary vsum LEFT JOIN public.vwvillage vil ON vil.village_id = vsum.village LEFT JOIN public.vwngo ON vwngo.ngoid = vsum.ngo WHERE vil.village_id = '" + str(village_id) + "'"
    village_labels_data = json.dumps(__db_fetch_values(village_labels_query))

    village_summary_query = "SELECT ngo,location,location_bn,village,\"union\",upazila,district,area_size,population,hh_number,average_member_hh,high_sensitive_hh,low_sensitive_hh,medium_sensitive_hh,average_male_earning_per_hh,average_female_earning_per_hh,villagers_main_occupation,villagers_main_occupation_bn,village_main_crops,village_main_crops_bn,percentage_hh_faced_hunger,hunger_duration,hh_average_expenditure,hh_average_food_expenditure,hh_average_income,hh_average_productive_assets,percentage_cultivable_land_family,percentage_cultivable_leased_land_family,percentage_hh_use_homestead,main_natural_disaster,main_natural_disaster_bn,primary_school,secondary_school,madrasa,market,hat,mosque,eidgah,temple,boat_ghat,health_complex,community_clinic,epi_center,flood_shelter,bank_distance,post_office_distance,up_distance,upazila_office_distance,instance_id,xform_id_string FROM PUBLIC.vwvillagesummary WHERE village = '" + str(village_id) + "'"
    village_summary_data = __db_fetch_values_dict(village_summary_query)
    village_summary_data_test = json.dumps(village_summary_data)

    action_plan_query = "SELECT * FROM vwactionplan_new WHERE village = '" + str(village_id) + "'"
    action_plan_data = json.dumps(__db_fetch_values_dict(action_plan_query))

    return render(request, "csvp_single_village.html", { 'legends_data' : legends_data, 'crop_data' : crop_data, 'climate_imapct_data':climate_imapct_data, 'season_data':season_data, 'priority_data':priority_data, 'problem_matrix_data':problem_matrix_data, 'livelihood_data':livelihood_data, 'village_labels_data':village_labels_data, 'village_summary_data_test':village_summary_data_test, 'village_info_data':village_info_data, 'action_plan_data':action_plan_data })


def __db_fetch_values(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchall()
    cursor.close()
    return fetchVal

def __db_fetch_values_dict(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = dictfetchall(cursor)
    cursor.close()
    return fetchVal

def dictfetchall(cursor):
    desc = cursor.description 
    return [
            OrderedDict(zip([col[0] for col in desc], row)) 
            for row in cursor.fetchall() ]


@login_required
def csvp_dashboard(request):
    return render(request, "csvp_dashboard.html")


def form_replace(request,username,id_string):    
    if request.method == 'POST':        
        print request.FILES
        #update_xform_test(request)
        #id_string='dynamic_form'

        xform = get_object_or_404(XForm, user__username__iexact=username, id_string__exact=id_string)
        print xform
        owner = xform.user

        def set_form():
            #print request.POST
            form = QuickConverter(request.POST, request.FILES)
            #print '###########################################123'            
            survey = form.publish(request.user, id_string).survey
            #print '###########################################124'
            enketo_webform_url = reverse(
                enter_data,
                kwargs={'username': username, 'id_string': survey.id_string}
            )
            audit = {
                'xform': xform.id_string
            }
            audit_log(
                Actions.FORM_XLS_UPDATED, request.user, owner,
                _("XLS for '%(id_string)s' updated.") %
                {
                    'id_string': xform.id_string,
                }, audit, request)
            return {
                'type': 'alert-success',
                'text': _(u'Successfully published %(form_id)s.'
                          u' <a href="%(form_url)s">Enter Web Form</a>'
                          u' or <a href="#preview-modal" data-toggle="modal">'
                          u'Preview Web Form</a>')
                        % {'form_id': survey.id_string,
                           'form_url': enketo_webform_url}
            }
        message = publish_form(set_form)
        messages.add_message(
            request, messages.INFO, message['text'], extra_tags=message['type'])

    return render(request,"form_upload.html")
