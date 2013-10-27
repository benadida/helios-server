alter table auth_user rename to helios_auth_user;
drop table celery_taskmeta;
drop table celery_tasksetmeta;
drop table djkombu_message;
drop table djkombu_queue;
delete from south_migrationhistory where app_name='auth';
