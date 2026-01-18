# Auto-Email Reminders for Voters

## Overview

Helios now supports automatic email reminders to voters who have not yet cast their ballots. This feature allows election administrators to configure reminders that are sent at a specified time before voting ends.

## How It Works

1. **Election Admin Configuration**: Administrators can enable auto-reminders for each election individually through the admin interface at `/voters/auto-reminder`.

2. **Reminder Timing**: Admins specify how many hours before voting ends the reminder should be sent (e.g., 24 hours = one day before).

3. **Automated Sending**: A periodic Celery task (`send_auto_reminders`) checks all elections and sends reminders when:
   - Auto-reminders are enabled for the election
   - Voting has started but not ended
   - Current time is within the reminder window (e.g., less than 24 hours before voting ends)
   - The reminder hasn't been sent yet for this election

4. **Target Audience**: Reminders are only sent to voters who have not yet cast a ballot (`vote_hash is None`).

## Setup Requirements

### Celery Beat Configuration

To enable automatic reminder checking, you need to configure Celery Beat to run the `send_auto_reminders` task periodically. Add this to your Celery configuration:

```python
# In settings.py or celery configuration
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'check-auto-reminders': {
        'task': 'helios.tasks.send_auto_reminders',
        'schedule': crontab(minute='0', hour='*/1'),  # Run every hour
    },
}
```

Or use timedelta for simpler scheduling:

```python
from datetime import timedelta

CELERY_BEAT_SCHEDULE = {
    'check-auto-reminders': {
        'task': 'helios.tasks.send_auto_reminders',
        'schedule': timedelta(hours=1),  # Run every hour
    },
}
```

### Running Celery

Start Celery worker with beat scheduler:

```bash
celery -A helios worker --beat --scheduler django --loglevel=info
```

Or run beat separately:

```bash
# Terminal 1: Start worker
celery -A helios worker --loglevel=info

# Terminal 2: Start beat scheduler
celery -A helios beat --scheduler django --loglevel=info
```

## Usage for Election Administrators

1. **Access Settings**: Navigate to your election's admin page and click on "Auto-Reminder Settings" or go to `/elections/{uuid}/voters/auto-reminder`.

2. **Enable Reminders**: Check the "Enable Auto-Reminders" checkbox.

3. **Set Timing**: Enter the number of hours before voting ends to send the reminder (default: 24).

4. **Save**: Click "Save Settings" to apply the configuration.

5. **Monitor**: The system will automatically send reminders at the appropriate time. Once sent, the timestamp will be displayed on the settings page.

## Important Notes

- **One Reminder Per Election**: Each election can only send one auto-reminder. Once sent, it won't be sent again even if you change settings.

- **Existing Email Infrastructure**: Auto-reminders use the same email templates and infrastructure as manual voter emails.

- **Opt-Out Respected**: Voters who have opted out of emails will not receive reminders (respects the EmailOptOut system).

- **Frozen Elections Only**: Reminders can only be configured for elections that have been frozen (voting parameters are locked).

## Technical Details

### Database Fields

- `auto_reminder_enabled_p` (Boolean): Whether auto-reminders are enabled
- `auto_reminder_hours` (Integer): Hours before voting ends to send reminder
- `auto_reminder_sent_at` (DateTime): Timestamp when reminder was sent

### Email Template

Reminders use the same "vote" email template as manual voter notifications, with a custom subject and message indicating the urgency of voting before the deadline.

## Testing

Run the test suite to verify auto-reminder functionality:

```bash
python manage.py test helios.tests.AutoReminderTests
```
