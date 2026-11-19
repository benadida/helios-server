import django.db.models.deletion
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
  # the voter table is large: add the column, index and foreign key
  # without blocking cast votes
  atomic = False

  dependencies = [
    ('helios', '0012_site_announcement'),
  ]

  operations = [
    migrations.AddField(
      model_name='voter',
      name='cast_vote',
      field=models.ForeignKey(db_constraint=False, db_index=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='helios.castvote'),
    ),
    AddIndexConcurrently(
      model_name='voter',
      index=models.Index(fields=['cast_vote'], name='helios_voter_cast_vote_idx'),
    ),
    # NOT VALID then VALIDATE avoids holding a write lock while checking every voter
    migrations.SeparateDatabaseAndState(
      database_operations=[
        migrations.RunSQL(
          "ALTER TABLE helios_voter ADD CONSTRAINT helios_voter_cast_vote_id_fk FOREIGN KEY (cast_vote_id) "
          "REFERENCES helios_castvote (id) DEFERRABLE INITIALLY DEFERRED NOT VALID",
          reverse_sql="ALTER TABLE helios_voter DROP CONSTRAINT helios_voter_cast_vote_id_fk",
        ),
        migrations.RunSQL(
          "ALTER TABLE helios_voter VALIDATE CONSTRAINT helios_voter_cast_vote_id_fk",
          reverse_sql=migrations.RunSQL.noop,
        ),
      ],
      state_operations=[
        migrations.AlterField(
          model_name='voter',
          name='cast_vote',
          field=models.ForeignKey(db_index=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='helios.castvote'),
        ),
      ],
    ),
  ]
