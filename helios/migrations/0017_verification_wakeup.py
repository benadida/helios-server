"""Wake hints are delivered by PostgreSQL only when acceptance commits."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('helios', '0016_sendbyte_email_provider')]
    operations = [migrations.RunSQL(
        sql="""
        CREATE FUNCTION helios_verification_wakeup() RETURNS trigger AS $$
        BEGIN
          PERFORM pg_notify('helios_vote_verification', '');
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER helios_verification_wakeup
          AFTER INSERT ON helios_voteverificationjob
          FOR EACH STATEMENT EXECUTE FUNCTION helios_verification_wakeup();
        """,
        reverse_sql="""
        DROP TRIGGER helios_verification_wakeup ON helios_voteverificationjob;
        DROP FUNCTION helios_verification_wakeup();
        """,
    )]
