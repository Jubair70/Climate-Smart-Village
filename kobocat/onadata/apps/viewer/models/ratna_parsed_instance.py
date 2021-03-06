import base64
import datetime
import json
import re
import os
import sys
import traceback

from bson import json_util, ObjectId
from celery import task
from dateutil import parser
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.utils.translation import ugettext as _
from onadata.apps.main.models import Approveline
from onadata.apps.logger.models import Instance
from onadata.apps.logger.models import Note
from onadata.apps.restservice.utils import call_service
from onadata.libs.utils.common_tags import ID, UUID, ATTACHMENTS, GEOLOCATION,\
    SUBMISSION_TIME, MONGO_STRFTIME, BAMBOO_DATASET_ID, DELETEDAT, TAGS,\
    NOTES, SUBMITTED_BY,APPROVE

from onadata.libs.utils.decorators import apply_form_field_names
from onadata.libs.utils.model_tools import queryset_iterator
import logging
from onadata.apps.main.models import Approveline,Approval
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

# for sending email
import smtplib
from django.core.mail import EmailMessage

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# from onadata.apps.main.models import Approveline,Approval


# this is Mongo Collection where we will store the parsed submissions
from onadata.apps.approval.models.approval import ApprovalDef
from onadata.apps.approval.models.approval import ApprovalList
from onadata.apps.approval.models.approval import InstanceApproval


# this is Mongo Collection where we will store the parsed submissions
xform_instances = settings.MONGO_DB.instances
key_whitelist = ['$or', '$and', '$exists', '$in', '$gt', '$gte',
                 '$lt', '$lte', '$regex', '$options', '$all']
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


class ParseError(Exception):
    pass


def datetime_from_str(text):
    # Assumes text looks like 2011-01-01T09:50:06.966
    if text is None:
        return None
    dt = None
    try:
        dt = parser.parse(text)
    except Exception:
        return None
    return dt


def dict_for_mongo(d):
    for key, value in d.items():
        if type(value) == list:
            value = [dict_for_mongo(e)
                     if type(e) == dict else e for e in value]
        elif type(value) == dict:
            value = dict_for_mongo(value)
        elif key == '_id':
            try:
                d[key] = int(value)
            except ValueError:
                # if it is not an int don't convert it
                pass
        if _is_invalid_for_mongo(key):
            del d[key]
            d[_encode_for_mongo(key)] = value
    return d


def _encode_for_mongo(key):
    return reduce(lambda s, c: re.sub(c[0], base64.b64encode(c[1]), s),
                  [(r'^\$', '$'), (r'\.', '.')], key)


def _decode_from_mongo(key):
    re_dollar = re.compile(r"^%s" % base64.b64encode("$"))
    re_dot = re.compile(r"\%s" % base64.b64encode("."))
    return reduce(lambda s, c: c[0].sub(c[1], s),
                  [(re_dollar, '$'), (re_dot, '.')], key)


def _is_invalid_for_mongo(key):
    return key not in\
        key_whitelist and (key.startswith('$') or key.count('.') > 0)


@task
def update_mongo_instance(record):
    # since our dict always has an id, save will always result in an upsert op
    # - so we dont need to worry whether its an edit or not
    # http://api.mongodb.org/python/current/api/pymongo/collection.html#pymong\
    # o.collection.Collection.save
    try:
        return xform_instances.save(record)
    except Exception:
        # todo: mail admins about the exception
        pass


class ParsedInstance(models.Model):
    USERFORM_ID = u'_userform_id'
    STATUS = u'_status'
    DEFAULT_LIMIT = 30000
    DEFAULT_BATCHSIZE = 1000

    instance = models.OneToOneField(Instance, related_name="parsed_instance")
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    # TODO: decide if decimal field is better than float field.
    lat = models.FloatField(null=True)
    lng = models.FloatField(null=True)

    class Meta:
        app_label = "viewer"

    @classmethod
    @apply_form_field_names
    def query_mongo(cls, username, id_string, query, fields, sort, start=0,
                    limit=DEFAULT_LIMIT, count=False, hide_deleted=True):
        fields_to_select = {cls.USERFORM_ID: 0}
        # TODO: give more detailed error messages to 3rd parties
        # using the API when json.loads fails
        if isinstance(query, basestring):
            query = json.loads(query, object_hook=json_util.object_hook)
        query = query if query else {}
        query = dict_for_mongo(query)
        query[cls.USERFORM_ID] = u'%s_%s' % (username, id_string)

        # check if query contains and _id and if its a valid ObjectID
        if '_uuid' in query and ObjectId.is_valid(query['_uuid']):
            query['_uuid'] = ObjectId(query['_uuid'])

        if hide_deleted:
            # display only active elements
            # join existing query with deleted_at_query on an $and
            query = {"$and": [query, {"_deleted_at": None}]}

        # fields must be a string array i.e. '["name", "age"]'
        if isinstance(fields, basestring):
            fields = json.loads(fields, object_hook=json_util.object_hook)
        fields = fields if fields else []

        # TODO: current mongo (2.0.4 of this writing)
        # cant mix including and excluding fields in a single query
        if type(fields) == list and len(fields) > 0:
            fields_to_select = dict(
                [(_encode_for_mongo(field), 1) for field in fields])
        if isinstance(sort, basestring):
            sort = json.loads(sort, object_hook=json_util.object_hook)
        sort = sort if sort else {}
        #query = {"$and": [query, {"approve": 'new'}]}
        cursor = xform_instances.find(query, fields_to_select)
        if count:
            return [{"count": cursor.count()}]

        if start < 0 or limit < 0:
            raise ValueError(_("Invalid start/limit params"))

        cursor.skip(start).limit(limit)
        if type(sort) == dict and len(sort) == 1:
            sort_key = sort.keys()[0]
            # TODO: encode sort key if it has dots
            sort_dir = int(sort[sort_key])  # -1 for desc, 1 for asc
            cursor.sort(_encode_for_mongo(sort_key), sort_dir)
        # set batch size
        cursor.batch_size = cls.DEFAULT_BATCHSIZE
        return cursor

    @classmethod
    @apply_form_field_names
    def mongo_aggregate(cls, query, pipeline, hide_deleted=True):
        """Perform mongo aggregate queries
        query - is a dict which is to be passed to $match, a pipeline operator
        pipeline - list of dicts or dict of mongodb pipeline operators,
        http://docs.mongodb.org/manual/reference/operator/aggregation-pipeline
        """
        if isinstance(query, basestring):
            query = json.loads(
                query, object_hook=json_util.object_hook) if query else {}
        if not (isinstance(pipeline, dict) or isinstance(pipeline, list)):
            raise Exception(_(u"Invalid pipeline! %s" % pipeline))
        if not isinstance(query, dict):
            raise Exception(_(u"Invalid query! %s" % query))
        query = dict_for_mongo(query)
        if hide_deleted:
            # display only active elements
            deleted_at_query = {
                "$or": [{"_deleted_at": {"$exists": False}},
                        {"_deleted_at": None}]}
            # join existing query with deleted_at_query on an $and
            query = {"$and": [query, deleted_at_query]}
        k = [{'$match': query}]
        if isinstance(pipeline, list):
            k.extend(pipeline)
        else:
            k.append(pipeline)
        results = xform_instances.aggregate(k)
        return results['result']

    @classmethod
    @apply_form_field_names
    def query_mongo_minimal(
            cls, query, fields, sort, start=0, limit=DEFAULT_LIMIT,
            count=False, hide_deleted=True):
        fields_to_select = {cls.USERFORM_ID: 0}
        # TODO: give more detailed error messages to 3rd parties
        # using the API when json.loads fails
        query = json.loads(
            query, object_hook=json_util.object_hook) if query else {}
        query = dict_for_mongo(query)
        if hide_deleted:
            # display only active elements
            # join existing query with deleted_at_query on an $and
            query = {"$and": [query, {"_deleted_at": None}]}
        # fields must be a string array i.e. '["name", "age"]'
        fields = json.loads(
            fields, object_hook=json_util.object_hook) if fields else []
        # TODO: current mongo (2.0.4 of this writing)
        # cant mix including and excluding fields in a single query
        if type(fields) == list and len(fields) > 0:
            fields_to_select = dict(
                [(_encode_for_mongo(field), 1) for field in fields])
        sort = json.loads(
            sort, object_hook=json_util.object_hook) if sort else {}
        cursor = xform_instances.find(query, fields_to_select)
        if count:
            return [{"count": cursor.count()}]

        if start < 0 or limit < 0:
            raise ValueError(_("Invalid start/limit params"))

        cursor.skip(start).limit(limit)
        if type(sort) == dict and len(sort) == 1:
            sort_key = sort.keys()[0]
            # TODO: encode sort key if it has dots
            sort_dir = int(sort[sort_key])  # -1 for desc, 1 for asc
            cursor.sort(_encode_for_mongo(sort_key), sort_dir)
        # set batch size
        cursor.batch_size = cls.DEFAULT_BATCHSIZE
        return cursor

    def to_dict_for_mongo(self):
        d = self.to_dict()
        data = {
            UUID: self.instance.uuid,
            ID: self.instance.id,
            BAMBOO_DATASET_ID: self.instance.xform.bamboo_dataset,
            self.USERFORM_ID: u'%s_%s' % (
                self.instance.xform.user.username,
                self.instance.xform.id_string),
            ATTACHMENTS: _get_attachments_from_instance(self.instance),
            self.STATUS: self.instance.status,
            GEOLOCATION: [self.lat, self.lng],
            SUBMISSION_TIME: self.instance.date_created.strftime(
                MONGO_STRFTIME),
            TAGS: list(self.instance.tags.names()),
            NOTES: self.get_notes(),
            SUBMITTED_BY: self.instance.user.username
            if self.instance.user else None
        }

        if isinstance(self.instance.deleted_at, datetime.datetime):
            data[DELETEDAT] = self.instance.deleted_at.strftime(MONGO_STRFTIME)

        d.update(data)

        return dict_for_mongo(d)

    def update_mongo(self, async=True):
        d = self.to_dict_for_mongo()
        d[APPROVE] = 'new'
        pipeline = ApprovalDef.objects.filter(formid=self.instance.xform.id_string).distinct()
        approval = ApprovalList.objects.filter(formid=self.instance.xform.id_string,
                                               userid=self.instance.xform.user.username, subbmissionid=self.instance.id)
        if pipeline is not None and not approval.exists():
            for user in pipeline:
                self.add_approval_list(user)
                #self.send_email_to_approver(user)

        if async:
            update_mongo_instance.apply_async((), {"record": d})
        else:
            update_mongo_instance(d)
        self.add_instance_approval()

    def add_approval_list(self, approver):
        approval_list = ApprovalList()
        approval_list.formid = self.instance.xform.id_string
        print('\n \n \t xform_id = ')
        print(self.instance.xform)
        approval_list.subbmissionid = self.instance.id
        approval_list.userid = approver.userid
        approval_list.status = self.get_approval_status(approver)
        approval_list.label = approver.approver_label
        approval_list.approval_def = approver
        approval_list.save();

    def get_approval_status(self, approver):
        if approver.approver_type == 'approver' and approver.approver_label is 1:
            return 'Pending'
        elif approver.approver_type == 'notify':
            return 'Notify'
        else:
            return 'Upcoming'

    def send_email_to_approver(self, approver):
        print('\n\n send_email_to_approver:')

        kobocat_url = os.environ.get('KOBOCAT_URL')
        smtp_url = getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com')
        smtp_port = getattr(settings, 'EMAIL_PORT', 587)
        sender = getattr(settings, 'EMAIL_HOST_USER', 'ratnacse06@gmail.com')
        password = getattr(settings, 'EMAIL_HOST_PASSWORD', 'cmecsrktwwithqml')
        receiver = 'mpower@gmail.com'
        send_msg = False;
        if not kobocat_url.endswith('/'):
            kobocat_url += '/'
        url = kobocat_url + approver.userid + '/forms/' + self.instance.xform.id_string + '/pending_instance/?s_id=' + str(
            self.instance.id) + '#/' + str(self.instance.id)
        msg = MIMEMultipart('alternative')
        text = ''
        html_part = ''
        if approver.approver_type == 'approver' and approver.approver_label is 1:
            content_user = get_object_or_404(User, username__iexact=approver.userid)
            receiver = content_user.email

            text = "Hi!\nYou have received an approval data \nHere is the link to view approval data:\nhttp://www.python.org"
            html_part = "You have received an approval data<br>"
            send_msg = True;

        elif approver.approver_type == 'approver' and approver.approver_label is 2:
            content_user = get_object_or_404(User, username__iexact=approver.userid)
            receiver = content_user.email

            text = "Hi!\nYou have received an Upcoming data \nHere is the link to view approval data:\nhttp://www.python.org"
            html_part = "You have received an Upcoming approval data<br>"
            send_msg = True;
        elif approver.approver_type == 'notify' and approver.approver_label is 1:
            content_user = get_object_or_404(User, username__iexact=approver.userid)
            receiver = content_user.email

            text = "Hi!\nYou have received an Notifying data \nHere is the link to view approval data:\nhttp://www.python.org"
            html_part = "You have received an Notifying data<br>"
            send_msg = True;

        html_first = """\
            <html>
            <head></head>
            <body>
            <p>Hi!<br>
            """

        html_second = """
            Here is the <a href=" """ + url + """ ">link</a> to view approval data.
            </p>
            </body>
            </html>
            """
        if send_msg is True:
            html = html_first + html_part + html_second
            print ('\n')
            print(html)
            print('\n receiver: ' + receiver)

            msg['Subject'] = 'The content for data approval'
            msg['From'] = sender
            msg['To'] = receiver

            # Record the MIME types of both parts - text/plain and text/html.
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
            # Attach parts into message container.
            # According to RFC 2046, the last part of a multipart message, in this case
            # the HTML message, is best and preferred.
            msg.attach(part1)
            msg.attach(part2)

            # Send the message via office365 SMTP server.

            s = smtplib.SMTP(smtp_url, smtp_port)
            # send mail function takes 3 arguments: sender's address, recipient's address
            # and message to send - here it is sent as one string.

            try:
                s.ehlo()
                s.starttls()
                s.ehlo()
                s.login(sender, password)
                s.sendmail(sender, receiver, msg.as_string())
                s.quit()
            except smtplib.SMTPServerDisconnected:
                print('Email sending failed, Reason: SMTPServerDisconnected: Connection unexpectedly closed')
            except smtplib.SMTPSenderRefused:
                print('Email sending failed, Reason: SMTPSenderRefused:')
            except smtplib.SMTPException:
                print "Error: unable to send email"

    def add_instance_approval(self):
        approver_count = ApprovalDef.objects.filter(formid=self.instance.xform.id_string).count()
        print('\n approver_count')
        print(approver_count)
        instance_approval = InstanceApproval()

        instance_approval.formid = self.instance.xform.id_string
        instance_approval.instance = self.instance
        instance_approval.json = self.instance.json
        instance_approval.senderid = self.instance.user.username
        if approver_count is None or approver_count == 0:
            instance_approval.status = 'Approved'
        else:
            instance_approval.status = 'New'
	
        instance_approval.save();
        print('\n data stored into instance_approval where instance_approval_id = ')
        #print(self.instance_approval.id)

    def to_dict(self):
        if not hasattr(self, "_dict_cache"):
            self._dict_cache = self.instance.get_dict()
        return self._dict_cache

    @classmethod
    def dicts(cls, xform):
        qs = cls.objects.filter(instance__xform=xform)
        for parsed_instance in queryset_iterator(qs):
            yield parsed_instance.to_dict()

    def _get_name_for_type(self, type_value):
        """
        We cannot assume that start time and end times always use the same
        XPath. This is causing problems for other peoples' forms.

        This is a quick fix to determine from the original XLSForm's JSON
        representation what the 'name' was for a given
        type_value ('start' or 'end')
        """
        datadict = json.loads(self.instance.xform.json)
        for item in datadict['children']:
            if type(item) == dict and item.get(u'type') == type_value:
                return item['name']

    def get_data_dictionary(self):
        # TODO: fix hack to get around a circular import
        from onadata.apps.viewer.models.data_dictionary import\
            DataDictionary
        return DataDictionary.objects.get(
            user=self.instance.xform.user,
            id_string=self.instance.xform.id_string
        )

    data_dictionary = property(get_data_dictionary)

    # TODO: figure out how much of this code should be here versus
    # data_dictionary.py.
    def _set_geopoint(self):
        if self.instance.point:
            self.lat = self.instance.point.y
            self.lng = self.instance.point.x

    def save(self, async=False, *args, **kwargs):
        # start/end_time obsolete: originally used to approximate for
        # instanceID, before instanceIDs were implemented
        self.start_time = None
        self.end_time = None
        self._set_geopoint()
        super(ParsedInstance, self).save(*args, **kwargs)
        # insert into Mongo
        self.update_mongo(async)

    def add_note(self, note):
        note = Note(instance=self.instance, note=note)
        note.save()

    def remove_note(self, pk):
        note = self.instance.notes.get(pk=pk)
        note.delete()

    def get_notes(self):
        notes = []
        note_qs = self.instance.notes.values(
            'id', 'note', 'date_created', 'date_modified')
        for note in note_qs:
            note['date_created'] = \
                note['date_created'].strftime(MONGO_STRFTIME)
            note['date_modified'] = \
                note['date_modified'].strftime(MONGO_STRFTIME)
            notes.append(note)
        return notes


def _get_attachments_from_instance(instance):
    attachments = []
    for a in instance.attachments.all():
        attachment = dict()
        attachment['download_url'] = a.media_file.url
        attachment['mimetype'] = a.mimetype
        attachment['filename'] = a.media_file.name
        attachment['instance'] = a.instance.pk
        attachment['xform'] = instance.xform.id
        attachment['id'] = a.id
        attachments.append(attachment)

    return attachments


def _remove_from_mongo(sender, **kwargs):
    instance_id = kwargs.get('instance').instance.id
    xform_instances.remove(instance_id)

pre_delete.connect(_remove_from_mongo, sender=ParsedInstance)


def rest_service_form_submission(sender, **kwargs):
    parsed_instance = kwargs.get('instance')
    created = kwargs.get('created')
    if created:
        call_service(parsed_instance)


post_save.connect(rest_service_form_submission, sender=ParsedInstance)
