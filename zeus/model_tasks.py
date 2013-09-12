import datetime

from Crypto import Random

from django.db import models
from django.db.models.base import ModelBase
from django.db import transaction

from zeus.model_features import feature

from helios import datatypes

LOCAL_MIXES_COUNT = 1


def _get_fields_for_task(task_name):
    keys = [
        '%s_started_at' % task_name,
        '%s_finished_at' % task_name,
        '%s_status' % task_name,
        '%s_error' % task_name
    ]
    fields = [
        models.DateTimeField(null=True, default=None),
        models.DateTimeField(null=True, default=None),
        models.CharField(max_length=50, default='pending'),
        models.TextField(null=True, default=None)
    ]
    return dict(zip(keys, fields))


class Task(object):

    def __init__(self, name=None):
        self.name = name


def task_fields(task):
    extra_fields = {}
    task_name = task._task_name
    # include fields
    extra_fields.update(_get_fields_for_task(task_name))

    # register task status feature methods
    feature_fields = {}
    status_field = '%s_status' % task_name
    error_field = '%s_error' % task_name
    started_field = '%s_started_at' % task_name
    finished_field = '%s_finished_at' % task_name

    can_status = ["pending", "waiting"]

    def feat_can(self):
        required = task._required_features
        ok = self.check_features(*required)
        return ok and (getattr(self, status_field) in can_status)

    def feat_finished(self):
        return bool(getattr(self, finished_field))

    def feat_running(self):
        return getattr(self, status_field) in ["running"]

    def feat_error(self):
        return bool(getattr(self, error_field))

    key = task._features_key
    extra_fields['_feature_can_%s' % task_name] = \
            feature(key, 'can_%s' % task_name)(feat_can)
    extra_fields['_feature_can_do_%s' % task_name] = \
            feature(key, 'can_do_%s' % task_name)(feat_can)
    extra_fields['_feature_%s_finished' % task_name] = \
            feature(key, '%s_finished' % task_name)(feat_finished)
    extra_fields['_feature_%s_running' % task_name] = \
            feature(key, '%s_running' % task_name)(feat_running)
    extra_fields['_feature_%s_error' % task_name] = \
            feature(key, '%s_error' % task_name)(feat_error)
    return extra_fields


class TaskModelBase(ModelBase):

    def __new__(cls, name, bases, attrs):
        supernew = super(TaskModelBase, cls).__new__
        extra_fields = {}
        for key, value in attrs.iteritems():
            # find methods registered as task
            if hasattr(value, '_task'):
                extra_fields.update(task_fields(value))

        attrs.update(extra_fields)
        return supernew(cls, name, bases, attrs)


class TaskModel(models.Model):

    __metaclass__ = TaskModelBase

    class Meta:
        abstract = True


def task(name, required_features=(), is_recurrent=False, completed_cb=None,
         features_key=''):
    status_field = '%s_status' % name
    error_field = '%s_error' % name
    started_field = '%s_started_at' % name
    finished_field = '%s_finished_at' % name

    def wrapper(func):
        def inner(self, *args, **kwargs):
            status = getattr(self, status_field)
            if status == 'finished':
                #raise Exception('Cannot rerun')
                return

            with transaction.commit_on_success():
                setattr(self, started_field, datetime.datetime.now())
                setattr(self, status_field, 'running')
                self.save()

            with transaction.commit_manually():
                try:
                    func(self, *args, **kwargs)
                    finished = False
                    if not is_recurrent:
                        finished = True
                    else:
                        if completed_cb and completed_cb(self):
                            finished = True

                    if finished:
                        self.__setattr__(finished_field,
                                     datetime.datetime.now())
                        setattr(self, status_field, 'finished')
                        setattr(self, error_field, None)
                    else:
                        setattr(self, status_field, 'waiting')
                    self.save()
                    transaction.commit()
                except Exception, e:
                    transaction.rollback()
                    with transaction.commit_on_success():
                        error = str(e)
                        setattr(self, error_field, error)
                        setattr(self, started_field, None)
                        setattr(self, status_field, 'pending')
                        self.save()
        setattr(inner, '_task', True)
        setattr(inner, '_task_name', name)
        setattr(inner, '_features_key', features_key)
        setattr(inner, '_required_features', required_features)
        return inner
    return wrapper


def election_task(*args, **kwargs):
    kwargs['features_key'] = 'election'
    return task(*args, **kwargs)


def poll_task(*args, **kwargs):
    kwargs['features_key'] = 'poll'
    return task(*args, **kwargs)


# Task completion methods
def mixing_completed_check(poll):
    return poll.mixes.finished().count() == LOCAL_MIXES_COUNT

def partial_decryptions_completed_check(poll):
    return poll.partial_decryptions.filter().no_secret().count() == \
            poll.election.trustees.filter().no_secret().count()


class ElectionTasks(TaskModel):

    class Meta:
        abstract = True


class PollTasks(TaskModel):

    class Meta:
        abstract = True

    @poll_task('validate_create', ('frozen',))
    def validate_create(self):
        e = self.election.__class__.objects.select_for_update().get(pk=self.election.pk)
        Random.atfork()
        self.zeus.validate_creating()
        self.frozen_at = datetime.datetime.now()
        self.save()
        e.save()
        if e.polls_feature_frozen:
            e.frozen_at = datetime.datetime.now()
            e.save()

    @poll_task('mix', ('validate_voting_finished',),
               completed_cb=mixing_completed_check)
    def mix(self, remote=None):
        if self.mixes.count() == 0:
            self.mixes.create(name="zeus mix", mix_order=0, mix_type='local')
        mix = self.mixes.filter().pending()[0]
        mix.mix_ciphers()

    @poll_task('validate_mixing', ('mix_finished',))
    def validate_mixing(self):
        ciphers = self.zeus.get_mixed_ballots()
        tally_dict = {'num_tallied': len(ciphers), 'tally': [
          [{'alpha':c[0], 'beta':c[1]} for c in ciphers]]}
        tally = datatypes.LDObject.fromDict(tally_dict,
                                            type_hint='phoebus/Tally')
        self.encrypted_tally = tally
        self.save()
        self.zeus.validate_mixing()

    @poll_task('validate_voting', ('closed',))
    def validate_voting(self):
        self.zeus.validate_voting()
        self.save()

    @poll_task('zeus_partial_decrypt', ('validate_mixing_finished',))
    def zeus_partial_decrypt(self):
        self.zeus.compute_zeus_factors()

    @poll_task('partial_decrypt', ('validate_mixing_finished',),
               completed_cb=partial_decryptions_completed_check,
               is_recurrent=True)
    def partial_decrypt(self, trustee, factors, proofs):
        dec = self.partial_decryptions.create(trustee=trustee, poll=self)
        dec.decryption_factors = factors
        dec.decryption_proofs = proofs
        dec.save()

        modulus, generator, order = self.zeus.do_get_cryptosystem()
        zeus_factors = self.zeus._get_zeus_factors(trustee)
        # zeus add_trustee_factors requires some extra info
        zeus_factors = {'trustee_public': trustee.public_key.y,
                        'decryption_factors': zeus_factors,
                        'modulus': modulus,
                        'generator': generator,
                        'order': order}
        self.zeus.add_trustee_factors(zeus_factors)
        trustee.save()

    @poll_task('decrypt', ('partial_decryptions_finished',))
    def decrypt(self):
        self.zeus.decrypt_ballots()
        self.store_zeus_proofs()

    @poll_task('compute_results')
    def compute_results(self):
        self.get_module().compute_results()

    class Meta:
        abstract = True


class ElectionTasks(object):
    pass
