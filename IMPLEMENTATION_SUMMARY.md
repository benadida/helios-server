# Implementation Summary: Auto-Email Reminders

## Overview
This implementation adds the ability for election administrators to configure automatic email reminders that are sent to voters who haven't yet cast their ballots.

## Changes Made

### 1. Database Schema (helios/models.py)
Added three new fields to the `Election` model:
- `auto_reminder_enabled_p` (Boolean, default=False): Enable/disable auto-reminders
- `auto_reminder_hours` (Integer, default=24): Hours before voting ends to send reminder
- `auto_reminder_sent_at` (DateTime, nullable): Timestamp when reminder was sent

### 2. Migration (helios/migrations/0008_add_auto_reminder_fields.py)
Django migration to add the new fields to the database.

### 3. Celery Task (helios/tasks.py)
New `send_auto_reminders()` task that:
- Queries elections with auto-reminders enabled
- Filters for active elections (started but not ended)
- Checks if current time is within the reminder window
- Sends email to voters who haven't voted using existing `voters_email` task
- Marks reminder as sent to prevent duplicates
- Includes error handling for URL generation failures

### 4. Admin Interface
**Form (helios/forms.py):**
- `AutoReminderForm`: Configure auto-reminder settings

**View (helios/views.py):**
- `auto_reminder_settings()`: View to manage reminder configuration
- Shows current settings and sent timestamp if applicable

**URL (helios/election_urls.py):**
- `/voters/auto-reminder`: Route to settings page

**Template (helios/templates/auto_reminder_settings.html):**
- Form to enable/configure reminders
- Display when reminder was sent

**UI Integration (helios/templates/voters_list.html):**
- Added "auto-reminder settings" button next to "email voters" button

### 5. Tests (helios/tests.py)
`AutoReminderTests` class with comprehensive test coverage:
- Field existence and defaults
- Enabling/disabling functionality
- Task execution logic
- Reminder window detection

### 6. Documentation (AUTO_REMINDERS.md)
Complete guide covering:
- Feature overview
- Setup instructions (Celery Beat configuration)
- Usage guide for administrators
- Technical details
- Testing instructions

## How It Works

1. **Configuration**: Admin enables auto-reminders and sets hours before voting ends
2. **Scheduling**: Celery Beat runs `send_auto_reminders` periodically (e.g., every hour)
3. **Detection**: Task finds elections where:
   - Auto-reminders are enabled
   - Voting has started but not ended
   - Current time >= (voting_end_time - reminder_hours)
   - Reminder hasn't been sent yet
4. **Sending**: Task queues emails to voters with `vote_hash = None` (haven't voted)
5. **Tracking**: `auto_reminder_sent_at` is updated to prevent duplicate sends

## Key Design Decisions

1. **One Reminder Per Election**: Each election sends only one reminder to keep it simple
2. **Leverage Existing Infrastructure**: Uses existing `voters_email` task and email templates
3. **Per-Election Configuration**: Each election can have different reminder settings
4. **Non-Intrusive**: Respects EmailOptOut system and existing email preferences
5. **Error Handling**: Gracefully handles URL generation failures

## Integration Points

- Uses existing email sending infrastructure (`voters_email`, `single_voter_email`)
- Respects `EmailOptOut` system
- Uses standard email templates (`email/vote_subject.txt`, `email/vote_body.txt`)
- Follows existing code conventions (naming, indentation, decorators)

## Testing
```bash
# Run auto-reminder specific tests
python manage.py test helios.tests.AutoReminderTests

# Run all tests
python manage.py test helios -v 2
```

## Deployment Requirements

**Required:**
- PostgreSQL database
- Celery worker running
- Celery Beat scheduler configured and running

**Configuration Example:**
```python
# settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'check-auto-reminders': {
        'task': 'helios.tasks.send_auto_reminders',
        'schedule': crontab(minute='0', hour='*/1'),  # Every hour
    },
}
```

## Files Modified/Created

**Created:**
- `helios/migrations/0008_add_auto_reminder_fields.py`
- `helios/templates/auto_reminder_settings.html`
- `AUTO_REMINDERS.md`
- `IMPLEMENTATION_SUMMARY.md` (this file)

**Modified:**
- `helios/models.py` - Added fields
- `helios/tasks.py` - Added send_auto_reminders task
- `helios/views.py` - Added auto_reminder_settings view
- `helios/forms.py` - Added AutoReminderForm
- `helios/election_url_names.py` - Added URL name
- `helios/election_urls.py` - Added URL pattern
- `helios/tests.py` - Added AutoReminderTests
- `helios/templates/voters_list.html` - Added UI button

## Future Enhancements (Not Implemented)

Potential improvements for future consideration:
- Multiple reminders per election (e.g., 48h, 24h, 6h before)
- Different reminder templates
- Reminder statistics/reporting
- Admin notification when reminders are sent
- Preview reminder before enabling
- A/B testing different reminder timings
