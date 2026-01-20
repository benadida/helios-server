# Migration to add indexes for frequently queried fields
# Based on analysis of query patterns across the codebase

from django.db import migrations, models


class Migration(migrations.Migration):

  dependencies = [
    ('helios', '0009_add_deleted_at_index'),
  ]

  operations = [
    # Priority 1: Voter.uuid - used in get_by_election_and_uuid()
    migrations.AlterField(
      model_name='voter',
      name='uuid',
      field=models.CharField(max_length=50, db_index=True),
    ),

    # Priority 1: CastVote compound index on (verified_at, invalidated_at)
    # Used in num_pending_votes, stats dashboard, verify_cast_votes command
    migrations.AddIndex(
      model_name='castvote',
      index=models.Index(
        fields=['verified_at', 'invalidated_at'],
        name='helios_cv_verified_invld_idx',
      ),
    ),

    # Priority 1: CastVote.vote_hash - used in ballot verification
    migrations.AlterField(
      model_name='castvote',
      name='vote_hash',
      field=models.CharField(max_length=100, db_index=True),
    ),

    # Priority 1: Trustee.uuid - used in get_by_uuid() and get_by_election_and_uuid()
    migrations.AlterField(
      model_name='trustee',
      name='uuid',
      field=models.CharField(max_length=50, db_index=True),
    ),

    # Priority 2: Election.featured_p - used in get_featured() for homepage
    migrations.AlterField(
      model_name='election',
      name='featured_p',
      field=models.BooleanField(default=False, db_index=True),
    ),

    # Priority 2: ElectionLog compound index on (election_id, at)
    # Used in get_log() with order_by('-at')
    migrations.AddIndex(
      model_name='electionlog',
      index=models.Index(
        fields=['election', 'at'],
        name='helios_eleclog_elec_at_idx',
      ),
    ),

    # Priority 3: AuditedBallot compound index on (election_id, vote_hash)
    # Used in get() for ballot audit lookups
    migrations.AddIndex(
      model_name='auditedballot',
      index=models.Index(
        fields=['election', 'vote_hash'],
        name='helios_ab_elec_hash_idx',
      ),
    ),
  ]
