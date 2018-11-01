CouchDB on K8s Integration
===========================

== Description ==

Apache CouchDB is open source database software that focuses on ease of use and having a scalable architecture.

This integration will monitor your CouchDB cluster running on Kubernetes by collecting metrics from its RESTful HTTP APIs.

Once enabled you will get a default CouchDB dashboard to help you get started monitoring your key CouchDB metrics.

== Metrics Collected ==

|Metric Name                                                         |Type   |Labels      |Unit       |Description                                                                    |
|--------------------------------------------------------------------|-------|------------|-----------|-------------------------------------------------------------------------------|
|couchdb.database_writes.value                                       |Gauge  |            |           |                               |
|couchdb.database_reads.value                                        |Gauge  |            |           |                                           |
|couchdb.open_databases.value                                        |Gauge  |            |                                                     |
|couchdb.open_os_files.value                                         |Gauge  |            |           |                                                  |
|couchdb.request_time.value                                          |Gauge  |            |                                                         |
|couchdb.httpd.bulk_requests.value                                   |Gauge  |            |           |                                                   |
|couchdb.httpd.temporary_view_reads.value                            |Gauge  |            |           |                      |
|couchdb.httpd.view_reads.value                                      |Gauge  |            |           |                                                   |
|couchdb.httpd_request_methods.COPY.value                            |Gauge  |            |           |    |
|couchdb.httpd_request_methods.DELETE.value  |Gauge | | | |
|couchdb.httpd_request_methods.GET.value  |Gauge | | | |
|couchdb.httpd_request_methods.HEAD.value |Gauge | | | |
|couchdb.httpd_request_methods.POST.value |Gauge | | | |
|couchdb.httpd_request_methods.PUT.value |Gauge | | | |
|couchdb.httpd_status_codes.200.value |Gauge | | | |
|couchdb.httpd_status_codes.201.value |Gauge | | | |
|couchdb.httpd_status_codes.202.value |Gauge | | | |
|couchdb.httpd_status_codes.204.value |Gauge | | | |
|couchdb.httpd_status_codes.206.value |Gauge | | | |
|couchdb.httpd_status_codes.301.value |Gauge | | | |
|couchdb.httpd_status_codes.302.value |Gauge | | | |
|couchdb.httpd_status_codes.304.value |Gauge | | | |
|couchdb.httpd_status_codes.400.value |Gauge | | | |
|couchdb.httpd_status_codes.401.value |Gauge | | | |
|couchdb.httpd_status_codes.403.value |Gauge | | | |
|couchdb.httpd_status_codes.404.value |Gauge | | | |
|couchdb.httpd_status_codes.405.value |Gauge | | | |
|couchdb.httpd_status_codes.406.value |Gauge | | | |
|couchdb.httpd_status_codes.409.value |Gauge | | | |
|couchdb.httpd_status_codes.412.value |Gauge | | | |
|couchdb.httpd_status_codes.413.value |Gauge | | | |
|couchdb.httpd_status_codes.414.value |Gauge | | | |
|couchdb.httpd_status_codes.415.value |Gauge | | | |
|couchdb.httpd_status_codes.416.value |Gauge | | | |
|couchdb.httpd_status_codes.417.value |Gauge | | | |
|couchdb.httpd_status_codes.500.value |Gauge | | | |
|couchdb.httpd_status_codes.501.value |Gauge | | | |
|compact_running |Gauge | | | |
|data_size |Gauge | | | |
|disk_size |Gauge | | | |
|doc_count |Gauge | | | |
|doc_del_count |Gauge | | | |
|sizes.active |Gauge | | | |
|sizes.external |Gauge | | | |
|sizes.file |Gauge | | | |

== Installation ==

Run the CouchDB_K8s plugin against your Kubernetes master and it will start collecting the metrics.


### Plugin Environment Variables

The CouchDB_K8s plugin can be customized via environment variables.

|Variable        |Default              |Description                                           |
|----------------|---------------------|------------------------------------------------------|
|username        |admin                |CouchDB admin username.                               |
|password        |password             |CouchDB admin password.                               |
|sharded_port    |5984                 |Port to access sharded data.                          |
|local_port      |5986                 |Port to access local nodes.                           |
|password        |                     |Basic authentication password.                        |


== Changelog ==

|Version|Release Date|Description                                                 |
|-------|------------|------------------------------------------------------------|
|1.0    |1-Nov-2018  |Initial version of the CouchDB_K8s monitoring integration.  |

