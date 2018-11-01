#!/usr/bin/env python3

# $ sudo -H pip install kubernetes
# --> Ran into issue """Cannot uninstall 'PyYAML'. It is a distutils installed project and thus we cannot accurately determine which files belong to it which would lead to only a partial uninstall.""""
# ----> Installed older version of pip as a workaround: ```$ sudo -H pip3 install pip==8.1.1```
# --> Also had to install packages `python3-dev build-essential autoconf libtool pkg-config libssl-dev` for source that pyopenssl can be compiled against and the appropriate build tools.

from kubernetes import client, config
from kubernetes.client import Configuration
from outlyer_plugin import Status, Plugin
import datetime
import json
import requests
import sys
import urllib3

# Disable the "Unverified HTTPS request is being made. blah blah" error warning.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# TODO: Configurable namespace...

# Setup Kubernetes access from within a pod and disable SSL verification.
# TODO: Make this a configurable switch.
config.load_incluster_config()
client.configuration.assert_hostname = False
client.configuration.verify_ssl = False
c = Configuration()
c.assert_hostname = False
c.verify_ssl = False
Configuration.set_default(c)


METRICS = [
    'couchdb.database_writes.value',
    'couchdb.database_reads.value',
    'couchdb.open_databases.value',
    'couchdb.open_os_files.value',
    'couchdb.request_time.value',
    'couchdb.httpd.bulk_requests.value',
    'couchdb.httpd.requests.value',
    'couchdb.httpd.temporary_view_reads.value',
    'couchdb.httpd.view_reads.value',
    'couchdb.httpd_request_methods.COPY.value',
    'couchdb.httpd_request_methods.DELETE.value',
    'couchdb.httpd_request_methods.GET.value',
    'couchdb.httpd_request_methods.HEAD.value',
    'couchdb.httpd_request_methods.POST.value',
    'couchdb.httpd_request_methods.PUT.value',
    'couchdb.httpd_status_codes.200.value',
    'couchdb.httpd_status_codes.201.value',
    'couchdb.httpd_status_codes.202.value',
    'couchdb.httpd_status_codes.204.value',
    'couchdb.httpd_status_codes.206.value',
    'couchdb.httpd_status_codes.301.value',
    'couchdb.httpd_status_codes.302.value',
    'couchdb.httpd_status_codes.304.value',
    'couchdb.httpd_status_codes.400.value',
    'couchdb.httpd_status_codes.401.value',
    'couchdb.httpd_status_codes.403.value',
    'couchdb.httpd_status_codes.404.value',
    'couchdb.httpd_status_codes.405.value',
    'couchdb.httpd_status_codes.406.value',
    'couchdb.httpd_status_codes.409.value',
    'couchdb.httpd_status_codes.412.value',
    'couchdb.httpd_status_codes.413.value',
    'couchdb.httpd_status_codes.414.value',
    'couchdb.httpd_status_codes.415.value',
    'couchdb.httpd_status_codes.416.value',
    'couchdb.httpd_status_codes.417.value',
    'couchdb.httpd_status_codes.500.value',
    'couchdb.httpd_status_codes.501.value'
]

DB_METRICS = [
    'compact_running',
    'data_size',
    'disk_size',
    'doc_count',
    'doc_del_count',
    'sizes.active',
    'sizes.external',
    'sizes.file'
]


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that converts datetime objects to ISO 8601 formatted strings."""

    def default(self, obj):
        """Overrides the default serialization of JSONEncoder then calls the JSONEncoder default() method.

        :param obj: Object to serialize.
        :type obj: *
        :return: json.JSONEncoder.default() object.
        :rtype: instance
        """
        try:
            if isinstance(obj, (datetime.datetime, datetime.time, datetime.date)):
                obj = obj.isoformat()
                return obj
            if isinstance(obj, datetime.timedelta):
                return int(obj.days * 86400 + obj.seconds)
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return json.JSONEncoder.default(self, obj)


def pretty_json(data, encoder=CustomJSONEncoder):
    """Takes a dictionary or list and converts it into a pretty-print JSON string.

    :param data: Dictionary or list to be converted.
    :type data: dict or list
    :param encoder: (optional) Custom encoder to supplement complex serializations. (default: CustomJSONEncoder)
    :type encoder: instance
    :return: String of pretty JSON awesomeness.
    :rtype: str
    """
    if encoder is not None:
        return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '), ensure_ascii=True,
                          cls=encoder)
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '), ensure_ascii=True)


def flatten(obj, parent_key=None, sep='.'):
    """Flattens multi-level dictionary to a single-level dictionary.

    :param obj: Dictionary object to flatten.
    :type obj: dict
    :param parent_key: (optional) Prefix for the flattened key. (default: None)
    :type parent_key: basestring, str, or unicode
    :param sep: (optional) Separator for the nested key names. (default: '.')
    :type sep: basestring, str, or unicode
    :return: Sexy flattened dictionary.
    :rtype: dict
    """
    items = []
    for obj_key, obj_val in obj.items():
        obj_key = obj_key.replace(' ', '_')

        new_key = '{}{}{}'.format(parent_key, sep, obj_key) if parent_key else obj_key
        if isinstance(obj_val, dict):
            items.extend(flatten(obj_val, new_key, sep=sep).items())
        else:
            items.append([new_key, obj_val])
    return dict(items)


def percentile_expander(flat_stats):
    # Since we are iterating over the dictionary keys, we can't update it in-flight so create a new object that will
    # be merged. Alternatively, one could get a list of keys to iterate over then manipulate the original object
    # since it won't be actively in-use. So many possibilities!
    expanded_percentiles = {}
    keys_to_prune = []

    for item_name in flat_stats:
        if 'percentile' not in item_name.lower():
            continue

        percentile_data = flat_stats.get(item_name)
        if not percentile_data:
            continue

        if not isinstance(percentile_data, (list, tuple, set)):
            continue

        found_bad_percentile = False
        for percentile in percentile_data:
            if len(percentile) != 2:
                if not found_bad_percentile:
                    found_bad_percentile = True
                continue

            # Add the flattened percentile to the new dictionary.
            expanded_percentiles['{}.{}'.format(item_name, str(percentile[0]))] = percentile[1]

        # Only destroy the percentile data if it was legit otherwise leave it be (useful for debugging) otherwise
        # try to conserve a little bit of memory.
        if not found_bad_percentile:
            keys_to_prune.append(item_name)

    # Like merging two dictionaries together -- the new dictionary would overwrite any existing values in the
    # dictionary being updated.
    flat_stats.update(expanded_percentiles)

    # And now for a little pruning... This method
    for key in keys_to_prune:
        # Option 1: This option is saver and shouldn't have a significant memory/performance impact.
        _ = flat_stats.pop(key)

        # Option 2: This can throw an exception if the key was removed after the `if` statement was evaluated. This
        #           may be more ideal for memory usage when garbage collection happens.
        #if key in flat_stats: del flat_stats[key]

    return flat_stats


def bool_to_int(flat_stats):
    updated = {}
    for key in flat_stats:
        data = flat_stats.get(key)
        if not isinstance(data, bool):
            continue

        if data is True:
            updated[key] = 1
            continue

        updated[key] = 0

    if updated:
        flat_stats.update(updated)
    return flat_stats


class CouchDBPlugin(Plugin):
    def _find_pods(self):
        # Create a Kubernetes client API instance
        v1 = client.CoreV1Api()
        # List the pods (hopefully)
        try:
            ret = v1.list_pod_for_all_namespaces(watch=False)
        except Exception as err:
            self.logger.exception(err)
            return None

        pod_results = []

        # Get the "items" list from the returned dictionary and if "items" is not available then use an empty
        # list as to prevent code from breaking.
        for pod in ret.items:
            couchdb_pod = False

            #pod_spec = pod.get('spec', {})
            if not pod.spec:
                continue

            # If we can't find what we're looking for then rely on the global/default settings.
            tmp_pod_info = {
                'COUCHDB_USER': self.get('username', None),
                'COUCHDB_PASSWORD': self.get('password', None),
                'SHARDED_PORT': self.get('sharded_port', 5984),
                'LOCAL_PORT': self.get('local_port', 5986),
                'URI_PREFIX': 'https://' if self.get('use_ssl', False) else 'http://',
                'HOSTNAME': pod.spec.hostname,
                'NODE_NAME': pod.spec.node_name,
                'IP': None
            }

            if not pod.spec.containers:
                continue

            for container in pod.spec.containers:
                # Check for CouchDB container auth credentials
                if container.env:
                    for env_item in container.env:
                        env_name = env_item.name
                        if not env_name:
                            continue

                        if env_name.upper() not in ['COUCHDB_USER', 'COUCHDB_PASSWORD']:
                            continue

                        tmp_pod_info[env_name] = env_item.value

                # Check for network ports that belong to CouchDB and mark it as a valid CouchDB pod/container.
                # If no ports are configured then `ports` will be `None` rather than an array.
                if container.ports:
                    for port in container.ports:
                        container_port = port.container_port
                        container_port_name = port.name
                        if not container_port or not container_port_name:
                            continue

                        if container_port_name.lower() == 'couchdb-port':
                            tmp_pod_info['SHARDED_PORT'] = container_port
                            # Make sure we set this gem so we don't omit a valid pod!
                            couchdb_pod = True

            if not pod.status:
                continue

            if not pod.status.pod_ip:
                continue

            tmp_pod_info['IP'] = pod.status.pod_ip

            # If it's a legit pod, add the dictionary to the list for use later.
            if couchdb_pod:
                pod_results.append(tmp_pod_info)

        return pod_results

    def _url_get(self, url):
        """Requests data from a URL.

        :returns: Response JSON as Python object if OK, False if a non-OK response is returned, and None if there was
                  a problem decoding JSON.
        """
        response = requests.get(url)
        if response.status_code != requests.codes.ok:
            return False

        try:
            return response.json()
        except Exception as err:
            self.logger.exception(err)
            self.logger.error(
                'Error parsing JSON response from "{url}". Dumping response content: {raw}'.format(
                    url=url,
                    raw=response.text
                )
            )
            return None

    def _get_stats(self, sharded_url, local_url):
        # Try the local URL before the sharded URL
        stats = self._url_get(url='{url_base}/_stats'.format(url_base=local_url))
        #print('local /_stats: {}'.format(pretty_json(stats)))

        if not stats:
            stats = self._url_get(url='{url_base}/_stats'.format(url_base=sharded_url))
        #print('sharded /_stats: {}'.format(pretty_json(stats)))

        if not stats:
            return None

        flat_stats = flatten(stats)

        # Since we're essentially duplicating the data, let garbage collection free up some memory.
        del stats

        flat_stats = bool_to_int(flat_stats)
        flat_stats = percentile_expander(flat_stats)

        if not flat_stats:
            return None
        return flat_stats

    def _get_db_stats(self, sharded_url, local_url, dbs=None, include_local=False, hide_underscore=True):
        """

        """
        results = {}

        fetch_dbs = False

        # If databases are not specified then fetch them. Use a boolean to see if we need to fetch them if we want to
        # fetch database information from local.
        if not dbs:
            fetch_dbs = True
            dbs = []

            # Try the sharded URL before the local URL
            found_dbs = self._url_get(url='{url_base}/_all_dbs'.format(url_base=sharded_url))
            #print('sharded /_all_dbs: {}'.format(pretty_json(found_dbs)))
            for db in found_dbs:
                # Hide the db names that start with an underscore because those are usually super-secret.
                if hide_underscore and db.startswith('_'):
                    continue

                dbs.append(db)

        for db in dbs:
            db_stats = self._url_get(url='{url_base}/{db_name}'.format(url_base=sharded_url, db_name=db))
            if not db_stats:
                self.logger.warning(
                    'Received "{}" when trying to get DB stats for "{}" ({}).'.format(
                        db_stats,
                        db,
                        '{url_base}/{db_name}'.format(url_base=sharded_url, db_name=db)
                    )
                )
                continue
            db_stats = flatten(db_stats)
            db_stats = bool_to_int(db_stats)

            # Create an entry in the results dictionary corresponding to the specific database.
            results[db] = {}

            for metric in DB_METRICS:
                metric_val = db_stats.get(metric)
                # Explicitly check for Python NoneType (None) because int(0) is equivalent to False as is None. Here,
                # only add the metric and value to the results if it exists.
                if metric_val is not None:
                    results[db][metric] = metric_val

        # If we're not including databases from local then return what we have so far instead of doing unnecessary work.
        if not include_local:
            return results

        # Only fetch if we had to previously and reset the dbs list.
        if fetch_dbs:
            dbs = []

            # Do the same thing as above but since the data is already in the results dictionary, overwrite objects to
            # allow garbage collection to free-up some memory.
            found_dbs = self._url_get(url='{url_base}/_all_dbs'.format(url_base=local_url))
            #print('local /_all_dbs: {}'.format(pretty_json(dbs)))
            for db in found_dbs:
                # Hide the db names that start with an underscore because those are usually super-secret.
                if hide_underscore and db.startswith('_'):
                    continue

                dbs.append(db)

        for db in dbs:
            # Odd things happen but we shouldn't fetch this data if it was already fetched previously because that
            # would just be silly.
            if db in results:
                continue

            db_stats = self._url_get(url='{url_base}/{db_name}'.format(url_base=local_url, db_name=db))
            if not db_stats:
                self.logger.warning(
                    'Received "{}" when trying to get DB stats for "{}" ({}).'.format(
                        db_stats,
                        db,
                        '{url_base}/{db_name}'.format(url_base=sharded_url, db_name=db)
                    )
                )
                continue
            db_stats = flatten(db_stats)
            db_stats = bool_to_int(db_stats)

            # Create an entry in the results dictionary corresponding to the specific database.
            results[db] = {}

            for metric in DB_METRICS:
                metric_val = db_stats.get(metric)
                # Explicitly check for Python NoneType (None) because int(0) is equivalent to False as is None. Here,
                # only add the metric and value to the results if it exists.
                if metric_val is not None:
                    results[db][metric] = metric_val

        if not results:
            return None
        return results

    def collect(self, _):
        pods = self._find_pods()

        for pod in pods:
            auth_string = ''
            if pod.get('COUCHDB_USER'):
                auth_string = '{user}:{password}'.format(
                    user=pod.get('COUCHDB_USER'),
                    password=pod.get('COUCHDB_PASSWORD')
                )

            sharded_url = '{prefix}{auth_string}@{host}:{port}'.format(
                prefix=pod.get('URI_PREFIX'),
                auth_string=auth_string,
                host=pod.get('IP'),
                port=pod.get('SHARDED_PORT')
            )
            local_url = '{prefix}{auth_string}@{host}:{port}'.format(
                prefix=pod.get('URI_PREFIX'),
                auth_string=auth_string,
                host=pod.get('IP'),
                port=pod.get('LOCAL_PORT')
            )

            common_dimensions = {
                'instance': 'couchdb',
                'hostname': pod.get('HOSTNAME'),
                'node': pod.get('NODE_NAME')
            }

            # Main stats are not filtered by the metric lists in-code to leave room for future expansion using the
            # histograms and other nifty goodies. Some of keys may not 100% match, due to percentiles and stuff, and
            # maybe some metric name components can be moved to something more descriptive rather than a unique
            # metric.
            flat_stats = self._get_stats(sharded_url=sharded_url, local_url=local_url)
            #print('flattened /_stats: {}'.format(pretty_json(flat_stats)))

            # Main stats are neat as they have metric types in the descriptions so replace ".value" with ".type".
            # The problem with some metrics is that the "value" portion may be in the middle of the metric name so
            # we will have to use string splitting, list slicing, and list concatenation but that is an expensive
            # operation so only do it when it is absolutely necessary.
            #
            # An example of a problematic metric name:
            #   couchdb.query_server.vdu_process_time.desc
            #   couchdb.query_server.vdu_process_time.type
            #   couchdb.query_server.vdu_process_time.value.max
            #   couchdb.query_server.vdu_process_time.value.median
            #   couchdb.query_server.vdu_process_time.value.min
            #   couchdb.query_server.vdu_process_time.value.n
            #   couchdb.query_server.vdu_process_time.value.percentile.50
            for metric_name in METRICS:
                metric_val = flat_stats.get(metric_name)
                if metric_val is None:
                    continue

                # Start by doing a simple string replace.
                metric_type_name = metric_name.replace('.value', '.type')

                # If the metric name now doesn't end with ".type" then we need to split it and re-assemble it.
                # Regular expressions would make this easier but the `re` module can be costly to run if expressions
                # are not pre-compiled or efficiently designed. Trying to keep it as simple and pythonic as possible.
                if not metric_type_name.endswith('.type'):
                    # Reduce the list iterations by splitting using a word rather than a single character. Speeeeeeedy!
                    # >>> n = 'couchdb.query_server.vdu_process_time.value.median'
                    # >>> n.replace('.value', '.type')
                    # 'couchdb.query_server.vdu_process_time.type.median'
                    # >>> nn = n.replace('.value', '.type')
                    # >>> nnn = nn.split('.type')
                    # >>> nnn
                    # ['couchdb.query_server.vdu_process_time', '.median']
                    # >>> '{}.type'.format(nnn[0])
                    # 'couchdb.query_server.vdu_process_time.type'
                    metric_type_name = '{}.type'.format(metric_type_name.split('.type')[0])

                else:
                    metric_type_name = flat_stats.get(metric_name.replace('.value', '.type'))

                if not metric_type_name:
                    self.logger.warning('Unable to find a metric type for metric "{}".'.format(metric_name))
                    continue

                # This can be made even more dynamic by using `getattr()` from the instance (`self`) to a generic
                # variable and then calling that generic variable as a function with the appropriate arguments.
                if metric_type_name == 'counter':
                    self.counter(metric_name, common_dimensions).set(metric_val)
                elif metric_type_name == 'gauge':
                    self.gauge(metric_name, common_dimensions).set(metric_val)

            flat_db_stats = self._get_db_stats(sharded_url=sharded_url, local_url=local_url)
            #print('flattened /<DB>: {}'.format(pretty_json(flat_db_stats)))

            # All of this data should be a gauge as far as I can tell. If it's wrong, oops.
            for db in flat_db_stats:
                db_data = flat_db_stats.get(db)

                db_dimensions = {
                    'db': db
                }
                db_dimensions.update(common_dimensions)

                for metric_name in db_data:
                    metric_val = db_data.get(metric_name)
                    if metric_val is None:
                        continue

                    self.gauge(metric_name, db_dimensions).set(metric_val)


if __name__ == '__main__':
    sys.exit(CouchDBPlugin().run())
