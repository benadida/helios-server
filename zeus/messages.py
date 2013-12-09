from django.utils.translation import ugettext_lazy as _


VOTER_REMOVE_CONFIRM = _("Confirm voter removal: {{ voter.voter_name}} "
                         "{{ voter.voter_surname }} "
                         "{{ voter.voter_fathername }} "
                         "({{ voter.voter_email }})")


TRUSTEE_REMOVE_CONFIRM = _("Are you sure you want to delete the selected"
                           " trustee ?")

ELECTION_FREEZE_CONFIRM = _("Are you sure you want to freeze the election ?")
POLL_DELETE_CONFIRM = _("Are you sure you want to delete the selected poll ?")
